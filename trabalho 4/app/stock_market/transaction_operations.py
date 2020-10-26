import datetime
import json
import os
from os.path import isfile
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Sequence, Mapping

import Pyro5.api
import Pyro5.core
import Pyro5.errors

from .database import Database
from ..consts import DATETIME_FORMAT
from ..enums import OrderType, TransactionState, VotingState
from ..order import Order, Transaction

PARTICIPANT_VOTING_TIMEOUT = 5

class ParticipantTransaction:
    """
    Representa uma transação de um participante

    :param id: Identificação da transação, não único
    :param order: Ordem a ser executada
    :param amount: Quantidade a ser negociada
    :param price: Preço a ser negociado
    :param order_id: Id da ordem a ser executada
    :param state: Estado atual da transação
    """

    def __init__(self,
                 id: int,
                 order: Order,
                 amount: float,
                 price: float,
                 order_id: int,
                 state: Optional[TransactionState] = TransactionState.ACTIVE,
                 **kwargs):
        self.id = id
        self.order = order
        self.amount = amount
        self.price = price
        self.order_id = order_id
        self.state = state

    @staticmethod
    def to_dict(transaction: 'ParticipantTransaction') -> Dict[str, Any]:
        """Serialização para enviar pelo Pyro."""
        return {
            '__class__': 'ParticipantTransaction',
            'id': transaction.id,
            'order': Order.to_dict(transaction.order),
            'amount': transaction.amount,
            'price': transaction.price,
            'order_id': transaction.order_id,
            'state': transaction.state.value
        }

    @staticmethod
    def from_dict(class_name: str, dict_: Dict[str, Any]) -> 'ParticipantTransaction':
        """Desserialização para receber pelo Pyro."""
        return ParticipantTransaction(
            dict_['id'],
            Order.from_dict('', dict_['order']),
            dict_['amount'],
            dict_['price'],
            dict_['order_id'],
            TransactionState(dict_['state'])
        )


class CoordinatorTransaction:
    """
    Representa uma transação do coordenador.

    :param id: Identificação da transação, único.
    :param initial_buy_order_id: Id da ordem de compra.
    :param initial_sell_order_id: Id da ordem de venda.
    :amount: Quantidade a ser negociada
    :price: Preço a ser negociado
    :param participants: Lista de participantes dessa transação.
    :state: Estado atual dessa transação
    :final_buy_order_id: Id da ordem final de compra após realização da transação
    :final_sell_order_id: Id da ordem final de venda após realização da transação
    """
    def __init__(self,
                 id_: int,
                 initial_buy_order_id: int,
                 initial_sell_order_id: int,
                 amount: float,
                 price: float,
                 participants: Sequence[str],
                 state: Optional[TransactionState] = TransactionState.ACTIVE,
                 final_buy_order_id: Optional[int] = None,
                 final_sell_order_id: Optional[int] = None,
                 **kwargs):
        self.id = id_
        self.initial_buy_order_id = initial_buy_order_id
        self.initial_sell_order_id = initial_sell_order_id
        self.amount = amount
        self.price = price
        self.participants = participants
        self.state = state
        self.final_buy_order_id = final_buy_order_id
        self.final_sell_order_id = final_sell_order_id
        self.finished_participants = 0

    @staticmethod
    def to_dict(transaction: 'CoordinatorTransaction') -> Dict[str, Any]:
        """Serialização para enviar pelo Pyro."""
        return {
            '__class__': 'CoordinatorTransaction',
            'id': transaction.id,
            'initial_buy_order_id': transaction.initial_buy_order_id,
            'initial_sell_order_id': transaction.initial_sell_order_id,
            'amount': transaction.amount,
            'price': transaction.price,
            'participants': transaction.participants,
            'state': transaction.state.value,
            'final_buy_order_id': transaction.final_buy_order_id,
            'final_sell_order_id': transaction.final_sell_order_id
        }

    @staticmethod
    def from_dict(class_name: str, dict_: Dict[str, Any]) -> 'CoordinatorTransaction':
        """Desserialização para receber pelo Pyro."""
        return CoordinatorTransaction(
            id_=dict_['id'],
            initial_buy_order_id=dict_['initial_buy_order_id'],
            initial_sell_order_id=dict_['initial_sell_order_id'],
            amount=dict_['amount'],
            price=dict_['price'],
            participants=dict_['participants'],
            state=TransactionState(dict_['state']),
            final_buy_order_id=dict_['final_buy_order_id'],
            final_sell_order_id=dict_['final_sell_order_id'],
        )

Pyro5.api.SerializerBase.register_class_to_dict(ParticipantTransaction, ParticipantTransaction.to_dict)
Pyro5.api.SerializerBase.register_dict_to_class('ParticipantTransaction', ParticipantTransaction.from_dict)

class Coordinator:
    """
    Representa uma coordenador, responsável por iniciar uma transação.

    :param db: banco de dados usado para salvar os dados finais
    """

    def __init__(self, db: Database):
        self.transaction_operations: Dict[int, CoordinatorTransaction] = {}
        self.participants: Dict[str, Pyro5.core.URI] = {}
        
        sys.excepthook = Pyro5.errors.excepthook
        self.daemon = Pyro5.api.Daemon()
        self.uri = self.daemon.register(self)

        self.path = Path(f'./app/stock_market/coordinator')
        
        self.db = db

    def save_temporary_state(self):
        """Salva o estado temporário do coordenador, no caso todas as transações que não foram completadas"""

        file_path = self.path / 'temporary_log.json'
        transactions = [CoordinatorTransaction.to_dict(t) for t in self.transaction_operations.values() if t.state != TransactionState.COMPLETED]
        
        with open(file_path, 'w') as fp:
            fp.write(json.dumps(
                {'transaction_operations': transactions}
            ))

    def save_state(self):
        """Salva o estado atual do coordenador"""

        file_path = self.path / 'log.json'
        transactions = [CoordinatorTransaction.to_dict(t) for t in self.transaction_operations.values()]
        with open(file_path, 'a') as fp:
            fp.write(json.dumps({
                'transaction_operations': transactions
            }))

        self.save_temporary_state()

    @Pyro5.api.expose
    def add_participants(self, participants: Mapping[str, Pyro5.core.URI]):
        """Adiciona participantes no coordenador"""

        self.participants.update(participants)

    def get_next_transaction_id(self):
        """Retorna o próximo id de transação disponível."""

        tid = 0
        file_path = self.path / './transaction_id'
        if os.path.isfile(file_path):
            with open(file_path, 'r+') as fp:
                tid = int(fp.read()) + 1
                fp.seek(0, 0)
                fp.write(str(tid))
        else:
            with open(file_path, 'w') as fp:
                tid = 0
                fp.write(str(tid))
        
        return tid

    @Pyro5.api.expose
    def open_transaction(self,
                         buy_order_id: int,
                         sell_order_id: int,
                         amount: float,
                         price: float,
                         tid: Optional[int] = None) -> int:
        """
        Cria uma operação de transação.

        :param buy_order: Id da ordem de compra.
        :param sell_order: Id da ordem de venda.
        :param amount: Quantidade a ser negociada.
        :param price: Preço a ser negociado.
        :param tid: Id a ser definido para a transação
        """
        if tid is None:
            transaction_id = self.get_next_transaction_id()
        else:
            transaction_id = tid

        buy_order = self.db.get_order_from_id(buy_order_id, OrderType.BUY)
        sell_order = self.db.get_order_from_id(sell_order_id, OrderType.SELL)
        
        buyer_uri = self.participants[buy_order.client_name]
        seller_uri = self.participants[sell_order.client_name]

        buy_transaction = ParticipantTransaction(
            transaction_id, buy_order, amount, price, buy_order_id)
        sell_transaction = ParticipantTransaction(
            transaction_id, sell_order, amount, price, sell_order_id)

        self.transaction_operations[transaction_id] = CoordinatorTransaction(
            transaction_id,
            buy_order_id,
            sell_order_id,
            amount,
            price,
            [buy_order.client_name, sell_order.client_name])
        
        self.save_temporary_state()

        with Pyro5.api.Proxy(buyer_uri) as buyer_proxy :
            buyer_proxy.prepare_transaction(buy_transaction)
        with Pyro5.api.Proxy(seller_uri) as seller_proxy :
            seller_proxy.prepare_transaction(sell_transaction)
        
        #TODO: pegar as travas

        threading.Thread(target=self.voting_phase,
                         args=(transaction_id,),
                         daemon=True).start()

        return transaction_id

    @Pyro5.api.expose
    def get_transaction_state(self, transaction_id: int):
        """
        Retorna o estado atual de uma transação

        :param transaction_id: id da transação a ser procurada
        """

        if transaction_id in self.transaction_operations:
            return self.transaction_operations[transaction_id].state
        return TransactionState.ABORTED

    def voting_phase(self, transaction_id: int):
        """
        Executa a fase de votação do efetivação da transação.

        :param transaction_id: id da transação a ser votada
        """
        #TODO: Fazer o programa funcionar mesmo se os participantes cairem
        positives_votes = 0
        participants = self.transaction_operations[transaction_id].participants
        for participant_name in participants:
            # Coloca um timeout para o participante votar.
            # Se ele responder sim, incrementa o contador.
            # Se não responder, assume que a resposta é não.
            with Pyro5.api.Proxy(self.participants[participant_name]) as participant_proxy:
                participant_proxy._pyroTimeout = PARTICIPANT_VOTING_TIMEOUT
                try:
                    vote = participant_proxy.vote_for_transaction(transaction_id)
                except Pyro5.errors.TimeoutError:
                    vote = False
            if vote:
                positives_votes += 1
            else:
                break

        self.decision_phase(transaction_id, positives_votes)

    def decision_phase(self, transaction_id: int, positives_votes: int):
        """
        Executa a fase de decisão do efetivação da transação.

        :param transaction_id: Id da transação a ser decidida
        :param positives_votos: Quantidade de votos positivos para a transação
        """

        participants = self.transaction_operations[transaction_id].participants
        # Se todo mundo votou pra efetivar
        if positives_votes == len(participants):
            self.transaction_operations[transaction_id].state = TransactionState.COMPLETED
            for participant_name in participants:
                with Pyro5.api.Proxy(self.participants[participant_name]) as participant_proxy:
                    # def f(transaction_id):
                    #     participant_proxy._pyroClaimOwnership()
                    #     participant_proxy.commit_transaction(transaction_id)  
                    # threading.Thread(target=f,
                    #      args=(transaction_id,),
                    #      daemon=True).start()

                    order_id, order_type = participant_proxy.commit_transaction(transaction_id)

                    self.signal_transaction_completed(transaction_id, order_id, OrderType(order_type))
        # Se alguém desistiu ou deu erro
        else:
            self.transaction_operations[transaction_id].state = TransactionState.ABORTED
            for participant_name in participants:
                with Pyro5.api.Proxy(self.participants[participant_name]) as participant_proxy:
                    participant_proxy.cancel_transaction(transaction_id)

    @Pyro5.api.expose
    def signal_transaction_completed(self, transaction_id: int, order_id: int, order_type: OrderType):
        """
        Avisa que um dos participantes da transação finalizou a tarefa

        :param transacion_id: Id da transação finalizada
        :param order_id: Id da ordem executada
        :param order_type: Tipo da ordem executada
        """

        if transaction_id in self.transaction_operations:
            transaction = self.transaction_operations[transaction_id]
            transaction.finished_participants += 1
            if order_type == OrderType.BUY:
                transaction.final_buy_order_id = order_id
            else:
                transaction.final_sell_order_id = order_id
            if (transaction.finished_participants == len(transaction.participants)):
                self.create_transaction_log(transaction.final_sell_order_id,
                                            transaction.final_buy_order_id,
                                            transaction.amount,
                                            transaction.price)
        else:
            print("Coordinator.signal_transaction_completed: Invalid transaction id")

    def create_transaction_log(self,
                               sell_order_id: Optional[int],
                               buy_order_id: Optional[int],
                               transaction_amount: float,
                               trade_price: float):
        """
        Cria uma entrada no log de transações (banco de dados e arquivo).

        :param sell_order_id: Id da ordem final de venda
        :param buy_order_id: Id da ordem final de compra
        :param transacion_amount: Quantidade negociada
        :param trade_price: Preço negociado
        """

        command = (
            f"""insert into StockTransaction (sell_id, buy_id, amount, price, datetime)
            values (
                {sell_order_id},
                {buy_order_id},
                {transaction_amount},
                {trade_price},
                '{datetime.datetime.now().strftime(DATETIME_FORMAT)}'
            )""")
        self.db.execute(command)

        self.save_state()

    def get_initial_state(self):
        """Lê e executda o estado inicial do coordenador (transações não finalizadas)"""

        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        else:
            file_path = self.path / 'temporary_log.json'
            if (os.path.isfile(file_path)):
                with open(file_path, 'r+') as fp:
                    data = json.loads(fp.read())
                self.transaction_operations = {
                    t['id']: CoordinatorTransaction.from_dict('', t)
                    for t in data['transaction_operations']}
                
                for tid, transaction in self.transaction_operations.items():
                    if transaction.state not in (TransactionState.COMPLETED, TransactionState.ABORTED):
                        self.open_transaction(
                            transaction.initial_buy_order_id,
                            transaction.initial_sell_order_id,
                            transaction.amount,
                            transaction.price,
                            tid)

                self.save_state()


class Participant:
    """
    Representa um participante de uma transação.

    :param name: Nome do participante
    :param coordinator_uri: Endereço pyro do participante
    :param db: Banco de dados a ser usado
    :param daemon: Thread onde o participante será registrado
    """

    def __init__(self,
                 name: str,
                 coordinator_uri: Pyro5.core.URI,
                 db: Database,
                 daemon: Pyro5.api.Daemon):
        sys.excepthook = Pyro5.errors.excepthook
        
        self.name = name
        self.coordinator_uri = coordinator_uri
        self.uri = daemon.register(self)
        self.db = db

        self.transactions: Dict[int, ParticipantTransaction] = {}
        self.temporary_own_stock: Dict[str, float] = {}

        self.path = Path(f'./app/stock_market/participants/{self.name}')

    def save_state(self):
        """Salva o estado atual do participante"""

        file_path = self.path / 'log.json'
        transactions = [ParticipantTransaction.to_dict(t) for t in self.transactions.values()]
        with open(file_path, 'a') as fp:
            fp.write(json.dumps({
                'transactions': transactions,
                'temporary_own_stock': self.temporary_own_stock
            }))

        self.save_temporary_state()

    def save_temporary_state(self):
        """Salva o estado temporário do participante, no caso todas as transações que não foram completadas e a carteira momentânea"""

        file_path = self.path / 'temporary_log.json'
        transactions = [ParticipantTransaction.to_dict(t) for t in self.transactions.values() if t.state != TransactionState.COMPLETED]
        
        with open(file_path, 'w') as fp:
            fp.write(json.dumps({
                'transactions': transactions,
                'temporary_own_stock': self.temporary_own_stock
            }))

    @Pyro5.api.expose
    def prepare_transaction(self, transaction: ParticipantTransaction):
        """
        Executa as operações da transação e aguarda o coordenador.

        :param transacition: Transação a ser executada
        """

        # Ve se já não esta executando essa transação
        if transaction.id in self.transactions:
            return

        self.transactions[transaction.id] = transaction
        transaction.state = TransactionState.ACTIVE
        self.save_temporary_state()

        # Se ultrapassa, da ValueError
        if transaction.amount > transaction.order.amount:
            transaction.state = TransactionState.FAILED
        # Se esgota a ordem, marca como inativa
        elif transaction.amount == transaction.order.amount:
            transaction.order.active = False
        # Se não, atualiza para ter a quantidade que sobrou da ordem
        else:
            transaction.order.amount -= transaction.amount

        owned_stock = self.db.get_stock_owned_by_client(self.name)
        if (transaction.order.ticker in owned_stock):
            if (transaction.order.type == OrderType.BUY):
                self.temporary_own_stock[transaction.order.ticker] += transaction.amount
            else:
                if owned_stock[transaction.order.ticker] >= transaction.amount:
                    self.temporary_own_stock[transaction.order.ticker] -= transaction.amount
                else:
                    transaction.state = TransactionState.FAILED
        else:
            if (transaction.order.type == OrderType.BUY):
                self.temporary_own_stock[transaction.order.ticker] = transaction.amount
            else:
                transaction.state = TransactionState.FAILED
        
        if transaction.state == TransactionState.ACTIVE:
            self.transactions[transaction.id].state = TransactionState.PENDING
        self.save_temporary_state()

    @Pyro5.api.expose
    def vote_for_transaction(self, transaction_id: int):
        """
        Vota se pode ou não executar uma transação

        :param transacion_id: Id da votação a ser votada
        """
        if transaction_id not in self.transactions:
            return False

        while self.transactions[transaction_id].state == TransactionState.ACTIVE:
            time.sleep(0.01)

        if self.transactions[transaction_id].state == TransactionState.PENDING:
            return True
        else:
            return False

    @Pyro5.api.expose
    def commit_transaction(self, transaction_id: int):
        """
        Executa uma transação

        :param transacion_id: Id da transação a ser executada
        """

        transaction = self.transactions[transaction_id]
        # Se esgota a ordem, marca como inativa
        if not transaction.order.active:
            self.db.execute(
                f'''update {transaction.order.type.value}
                    set active = 0 
                    where id = {transaction.order_id}''')
            new_id = transaction.order_id
        # Se não, atualiza para ter a quantidade que sobrou da ordem
        # E cria a ordem parcial que foi executada
        else:
            self.db.execute(
                f'''update {transaction.order.type.value}
                    set amount = {transaction.order.amount - transaction.amount}
                    where id = {transaction.order_id}''')
            cursor = self.db.execute(
                f'''insert into {transaction.order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                    values (
                        '{transaction.order.ticker}',
                        {transaction.amount},
                        {transaction.order.price},
                        '{transaction.order.expiry_date}', 
                        (select id from Client where name = '{transaction.order.client_name}'),
                        0
                    )''')
            new_id = cursor.lastrowid

        self.update_owned_stock(transaction.order.ticker)
        self.temporary_own_stock.pop(transaction.order.ticker)
        
        transaction.state = TransactionState.COMPLETED

        self.save_state()

        return new_id, transaction.order.type
        # with Pyro5.api.Proxy(self.coordinator_uri) as coord_proxy:
        #     print("Participante dizendo que acabou a transacao")
        #     coord_proxy.signal_transaction_completed(
        #         transaction_id, new_id, transaction.order.type)


    def update_owned_stock(self, ticker: str):
        """
        Atualiza ou insere uma quantidade de ações para um cliente.
        
        :param ticker: Nome da ação.
        """
        # Pega o id da entrada no db, para a quantidade que o cliente tem daquela ação
        current_stock_amount = self.temporary_own_stock[ticker]
        id_owned_stock = self.db.execute(
            f'''select id from OwnedStock 
                    where ticker = '{ticker}' and
                    client_id = (select id from Client where name = '{self.name}')''').fetchone()

        # Se tem a ação, atualiza a quantidade
        if id_owned_stock:
            id_owned_stock = id_owned_stock[0]
            self.db.execute(
                f'''update OwnedStock set amount={current_stock_amount}
                        where id = {id_owned_stock}''')
        #Se não tem, adiciona a ação
        else:
            self.db.execute(
                f'''insert into OwnedStock (ticker, amount, client_id)
                        values ('{ticker}', {current_stock_amount}, (select id from Client where name = '{self.name}'))''')

    @Pyro5.api.expose
    def cancel_transaction(self, transaction_id: int):
        """
        Cancela uma transação

        :param transacion_id: Id da transação a ser executada
        """

        if transaction_id in self.transactions:
            self.temporary_own_stock.pop(self.transactions[transaction_id].order.ticker)
            self.transactions[transaction_id].state = TransactionState.ABORTED
            self.save_state()

    def get_initial_state(self):
        """Lê e executda o estado inicial do participante (transações não finalizadas)"""

        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        else:
            file_path = self.path / 'temporary_log.json'
            if (os.path.isfile(file_path)):
                with open(file_path, 'r+') as fp:
                    data = json.loads(fp.read())
                self.temporary_own_stock = data['temporary_own_stock']
                self.transactions = {
                    t['id']: ParticipantTransaction.from_dict('', t)
                    for t in data['transactions']}
                
                with Pyro5.api.Proxy(self.coordinator_uri) as coord_proxy:
                    # Pra cada transação no log
                    for tid, transaction in self.transactions.items():
                        # Se é uma transação que tinha que executar
                        # Ve se precisa começar de novo ou pode desistir
                        if transaction.state == TransactionState.ACTIVE:
                            coord_state = coord_proxy.get_transaction_state()
                            if coord_state == TransactionState.ACTIVE:
                                self.prepare_transaction(transaction)
                            elif coord_state == TransactionState.ABORTED:
                                transaction.state = TransactionState.ABORTED
                            else:
                                print("Participant.get_initial_state: Ue, coord_state tem valor que não bate")
                        # Se é uma transação que terminou e tava esperando
                        # Ve se pode commitar ou se joga fora
                        elif transaction.state == TransactionState.PENDING:
                            coord_state = coord_proxy.get_transaction_state()
                            if coord_state == TransactionState.ACTIVE:
                                pass
                            elif coord_state == TransactionState.COMPLETED:
                                self.commit_transaction(tid)
                            elif coord_state == TransactionState.ABORTED:
                                transaction.state = TransactionState.ABORTED
                            else:
                                print("Participant.get_initial_state: Ue, coord_state tem valor que não bate")
                
                self.save_state()


class MarketParticipant:
    def __init__(self,
                 coordinator_uri: Pyro5.core.URI,
                 db: Database,
                 daemon: Pyro5.api.Daemon):
        self.coordinator_uri = coordinator_uri
        self.db = db
        self.uri = daemon.register(self)
        self.transactions: Dict[int, ParticipantTransaction] = {}
        self.path = Path(f'./app/stock_market/participants/Market')

    def save_state(self):
        """Salva o estado atual do participante"""

        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        file_path = self.path / 'log.json'
        transactions = [ParticipantTransaction.to_dict(t) for t in self.transactions.values()]
        with open(file_path, 'a') as fp:
            fp.write(json.dumps({
                'transactions': transactions
            }))

        self.save_temporary_state()

    def save_temporary_state(self):
        """Salva o estado temporário do coordenador, no caso todas as transações que não foram completadas"""

        file_path = self.path / 'temporary_log.json'
        transactions = [ParticipantTransaction.to_dict(t) for t in self.transactions.values() if t.state != TransactionState.COMPLETED]

        with open(file_path, 'w') as fp:
            fp.write(json.dumps({
                'transactions': transactions
            }))

    @Pyro5.api.expose
    def prepare_transaction(self, transaction: int):
        """
        Executa as operações da transação e aguarda o coordenador.

        :param transacition: Transação a ser executada
        """

        self.transactions[transaction.id] = transaction
        self.transactions[transaction.id].state = TransactionState.PENDING
        self.save_temporary_state()

    @Pyro5.api.expose
    def vote_for_transaction(self, transaction_id: int):
        """
        Vota se pode ou não executar uma transação

        :param transacion_id: Id da votação a ser votada
        """

        if transaction_id in self.transactions:
            return self.transactions[transaction_id].state == TransactionState.PENDING
        return False

    @Pyro5.api.expose
    def commit_transaction(self, transaction_id: int):
        """
        Executa uma transação

        :param transacion_id: Id da transação a ser executada
        """

        transaction = self.transactions[transaction_id]
        # Cria a ordem no nome do mercado no db

        self.db.execute(
                f'''update {transaction.order.type.value}
                    set active = 0 
                    where id = {transaction.order_id}''')
        self.save_state()

        return transaction.order_id, transaction.order.type

        # with Pyro5.api.Proxy(self.coordinator_uri) as coord_proxy:
        #     print("Mercado Dizendo que terminou a transacao")
        #     coord_proxy.signal_transaction_completed(
        #         transaction_id, transaction.order_id, transaction.order.type)

    @Pyro5.api.expose
    def cancel_transaction(self, transaction_id):
        """
        Cancela uma transação

        :param transacion_id: Id da transação a ser executada
        """

        if transaction_id in self.transactions:
            self.transactions[transaction_id].state = TransactionState.ABORTED
            self.save_state()

    def get_initial_state(self):
        """Lê e executda o estado inicial do participante (transações não finalizadas)"""

        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        else:
            file_path = self.path / 'temporary_log.json'
            if (os.path.isfile(file_path)):
                with open(file_path, 'r+') as fp:
                    data = json.loads(fp.read())
                self.transactions = {
                    t['id']: ParticipantTransaction.from_dict('', t)
                    for t in data['transactions']}
                
                with Pyro5.api.Proxy(self.coordinator_uri) as coord_proxy:
                    # Pra cada transação no log
                    for tid, transaction in self.transactions.items():
                        if transaction.state == TransactionState.PENDING:
                            coord_state = coord_proxy.get_transaction_state()
                            if coord_state == TransactionState.ACTIVE:
                                pass
                            elif coord_state == TransactionState.COMPLETED:
                                self.commit_transaction(tid)
                            elif coord_state == TransactionState.ABORTED:
                                transaction.state = TransactionState.ABORTED
                            else:
                                print("Participant.get_initial_state: Ue, coord_state tem valor que não bate")
                
                self.save_state()