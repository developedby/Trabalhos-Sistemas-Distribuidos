import datetime
import json
import os
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Sequence, Mapping

import Pyro5.api as pyro
from Pyro5.errors import TimeoutError as PyroTimeoutError
from Pyro5.errors import excepthook as pyro_excepthook

from .database import Database
from ..consts import DATETIME_FORMAT
from ..enums import OrderType, TransactionState, VotingState
from ..order import Order, Transaction


class ParticipantTransaction:
    """
    Representa uma transação de um participante

    :param id: Identificação da transação, não único
    :param order: Ordem a ser executada
    :param amount: Quantidade a ser negociada
    :param price: Preço a ser negociado
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
            'state': transaction.state
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
    :param buy_order_id: Id da ordem de compra.
    :param sell_order_id: Id da ordem de venda.
    :param participants: Lista de participantes dessa transação.
    """
    def __init__(self,
                 id: int,
                 buy_order_id: Optional[int],
                 sell_order_id: Optional[int],
                 amount: float,
                 price: float,
                 participants: Sequence[str],
                 state: Optional[TransactionState] = TransactionState.ACTIVE,
                 **kwargs):
        self.id = id
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.amount = amount
        self.price = price
        self.participants = participants
        self.state = state
        self.finished_participants = 0

    @staticmethod
    def to_dict(transaction: 'CoordinatorTransaction') -> Dict[str, Any]:
        """Serialização para enviar pelo Pyro."""
        return {
            '__class__': 'CoordinatorTransaction',
            'id': transaction.id,
            'buy_order_id': transaction.buy_order_id,
            'sell_order_id': transaction.sell_order_id,
            'buy_order': Order.to_dict(transaction.buy_order),
            'sell_order': Order.to_dict(transaction.sell_order),
            'amount': transaction.amount,
            'price': transaction.price,
            'participants': transaction.participants,
            'state': transaction.state
        }

    @staticmethod
    def from_dict(class_name: str, dict_: Dict[str, Any]) -> 'CoordinatorTransaction':
        """Desserialização para receber pelo Pyro."""
        return CoordinatorTransaction(
            dict_['id'],
            dict_['buy_order_id'],
            dict_['sell_order_id'],
            Order.from_dict('', dict_['buy_order']),
            Order.from_dict('', dict_['sell_order']),
            dict_['amount'],
            dict_['price'],
            dict_['participants'],
            dict_['state'],
        )


class Coordinator:
    """
    Representa uma coordenador, responsável por iniciar uma transação
    """

    def __init__(self, db: Database):
        self.transaction_operations: Dict[int, CoordinatorTransaction] = {}
        self.participants: Dict[str, str] = {}
        
        sys.excepthook = pyro_excepthook
        self.daemon = pyro.Daemon()
        self.uri = self.daemon.register(self)

        self.path = Path(f'./app/stock_market/coordinator')
        
        self.db = db

        self.get_initial_state()

    def save_temporary_state(self):
        file_path = self.path / 'temporary_log.json'
        transactions = []
        for t in self.transaction_operations.values():
            if t.state != TransactionState.COMPLETED:
                transactions.append([CoordinatorTransaction.to_dict(t)])
        with open(file_path, 'w') as fp:
            fp.write(json.dumps(
                {'transaction_operations': transactions}
            ))

    def save_state(self):
        file_path = self.path / 'log.json'
        transactions = [CoordinatorTransaction.to_dict(t) for t in self.transaction_operations.values()]
        with open(file_path, 'a') as fp:
            fp.write(json.dumps({
                'transaction_operations': self.transaction_operations,
                'participants': self.participants
            }))

    def add_participants(self, participants: Mapping[str, str]):
        self.participants.update(participants)

    def get_id(self):
        """
        Retorna o próximo id de transação disponível
        """
        tid = 0
        file_path = self.path / './transaction_id'
        if os.path.isfile(file_path):
            with open(file_path, 'r+') as fp:
                tid = int(fp.read()) + 1
                fp.write(str(tid))
        else:
            with open(file_path, 'w') as fp:
                tid = 0
                fp.write(str(tid))
        
        return tid

    # TODO: Precisa dos order_id?
    @pyro.expose
    def open_transaction(self,
                         buy_order_id: int,
                         sell_order_id: int,
                         amount: float,
                         price: float,
                         tid: Optional[int]) -> int:
        """
        Cria uma operação de transação

        :param buy_order: Ordem de compra com id
        :param sell_order: Ordem de venda com id
        :param amount: Quantidade a ser negociada
        :param price: Preço a ser negociado
        """
        if tid is None:
            transaction_id = self.get_id()
        else:
            transaction_id = tid

        buy_order = self.db.get_order_from_id(buy_order_id, OrderType.BUY)
        sell_order = self.db.get_order_from_id(sell_order_id, OrderType.SELL)

        buyer_participant = self.participants[buy_order.client_name]
        seller_participant = self.participants[sell_order.client_name]

        buy_transaction = ParticipantTransaction(
            transaction_id, buy_order, amount, price, buy_order_id)
        sell_transaction = ParticipantTransaction(
            transaction_id, sell_order, amount, price, sell_order_id)

        self.transaction_operations[transaction_id] = CoordinatorTransaction(
            transaction_id,
            None,
            None,
            amount,
            price,
            [buyer_participant, seller_participant])
        
        self.save_temporary_state()

        buyer_participant_proxy = pyro.Proxy(buyer_participant)
        seller_participant_proxy = pyro.Proxy(seller_participant)

        buyer_participant_proxy.prepare_transaction(buy_transaction)
        seller_participant_proxy.prepare_transaction(sell_transaction)

        buyer_participant_proxy._pyroRelease()
        seller_participant_proxy._pyroRelease()
        
        #TODO: pegar as travas

        threading.Thread(target=self.voting_phase,
                         args=(transaction_id,),
                         daemon=True).start()

        return transaction_id

    @pyro.expose
    def get_transaction_state(self, transaction_id):
        return self.transaction_operations[transaction_id].state

    def voting_phase(self, transaction_id):
        #TODO: Colocar try etc para nao morrer
        positives_votes = 0
        participants = self.transaction_operations[transaction_id].participants
        for participant in participants:
            #Coloca um timeout para o participante votar. Se ele responder sim, incrementa o contador
            #Se não responder, assumi que a resposta é não
            participant_proxy = pyro.Proxy(participant)
            participant_proxy._pyroTimeout = 5
            try:
                vote = participant_proxy.vote_for_transaction(transaction_id)
            except PyroTimeoutError:
                vote = False
            participant_proxy._pyroRelease()
            if vote:
                positives_votes += 1
            else:
                break
            

        self.decision_phase(transaction_id, positives_votes)

    def decision_phase(self, transaction_id: int, positives_votes: int):
        participants = self.transaction_operations[transaction_id].participants
        if positives_votes == len(participants):
            self.transaction_operations[transaction_id].state = TransactionState.ACTIVE
            for participant in participants:
                participant_proxy = pyro.Proxy(participant)
                participant_proxy.make_transaction(transaction_id)
                participant_proxy._pyroRelease()
        else:
            self.transaction_operations[transaction_id].state = TransactionState.ABORTED
            for participant in participants:
                participant_proxy = pyro.Proxy(participant)
                participant_proxy.cancel_transaction(transaction_id)
                participant_proxy._pyroRelease()

    def signalize_transaction_completed(self, transaction_id, order_id, order_type):
        transaction = self.transaction_operations[transaction_id]
        transaction.finished_participants += 1
        if order_type == OrderType.BUY:
            transaction.buy_order_id = order_id
        else:
            transaction.sell_order_id = order_id
        if (transaction.finished_participants == len(transaction.participants)):
            self.create_transaction_log(transaction.sell_order_id,
                                        transaction.buy_order_id,
                                        transaction.amount,
                                        transaction.price)

    def create_transaction_log(self,
                               sell_order_id: Optional[int],
                               buy_order_id: Optional[int],
                               transaction_amount: float,
                               trade_price: float):
        """Cria uma entrada no log de transações."""
        command = (
            f"""insert into StockTransaction (sell_id, buy_id, amount, price, datetime)
            values (
                {sell_order_id},
                {buy_order_id},
                {transaction_amount},
                {trade_price},
                '{datetime.datetime.now().strftime(DATETIME_FORMAT)}'
            )""")
        #print(command)
        # TODO: Essa funcao é so no StockMarket
        self.db.execute(command)
        self.save_state()

    def get_initial_state(self):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        else:
            file_path = self.path / 'temporary_log.json'
            with open(file_path, 'r+') as fp:
                data = json.loads(fp.read())
            transactions = {t['id']: CoordinatorTransaction.from_dict('', t)
                            for t in data['transaction_operations']}
            self.transaction_operations = transactions
            
            for tid, transaction in self.transaction_operations.items():
                if transaction.state != TransactionState.COMPLETED:
                    self.open_transaction(
                        transaction.buy_order,
                        transaction.sell_order,
                        transaction.amount,
                        transaction.price,
                        tid)

class Participant:
    """
    Representa um participante de uma transação
    """

    def __init__(self, name: str, coordinator_uri: str, db: Database):
        sys.excepthook = pyro_excepthook
        
        self.name = name
        self.coordinator = pyro.Proxy(coordinator_uri)
        self.daemon = pyro.Daemon()
        self.uri = self.daemon.register(self)

        self.transactions: Dict[int, ParticipantTransaction] = {}
        self.temporary_own_stock: Dict[str, float] = {}

        self.path = Path(f'./app/stock_market/participants/{self.name}')

        self.db = db

        self.get_initial_state()

    def save_state(self):
        file_path = self.path / 'log.json'
        transactions = [ParticipantTransaction.to_dict(t) for t in self.transactions.values()]
        with open(file_path, 'a') as fp:
            fp.write(json.dumps({
                'transactions': transactions,
                'temporary_own_stock': self.temporary_own_stock
            }))

    def save_temporary_state(self):
        file_path = self.path / 'temporary_log.json'
        transactions = []
        for t in self.transactions.values():
            if t.state != TransactionState.COMPLETED:
                transactions.append([ParticipantTransaction.to_dict(t)])
        with open(file_path, 'w') as fp:
            fp.write(json.dumps({
                'transactions': transactions,
                'temporary_own_stock': self.temporary_own_stock
            }))

    def prepare_transaction(self, transaction):
        # Se ultrapassa, da ValueError
        self.transactions[transaction.id] = transaction
        transaction.state = TransactionState.PENDING
        if transaction.amount > transaction.order.amount:
            transaction.state = TransactionState.FAILED
        # Se esgota a ordem, marca como inativa
        elif transaction.amount == transaction.order.amount:
            transaction.order.active = False
        # Se não, atualiza para ter a quantidade que sobrou da ordem
        else:
            transaction.order.amount -= transaction.amount

        owned_stock = self.market.get_stock_owned_by_client(self.name)
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

    def vote_for_transaction(self, transaction_id):
        self.save_temporary_state()
        if transaction_id in self.transactions:
            if self.transactions[transaction_id].state == TransactionState.PENDING:
                return True
        return False
        
    def make_transaction(self, transaction_id):
        transaction = self.transactions[transaction_id]
        # Se esgota a ordem, marca como inativa
        # TODO: Puxar a order type de algum lugar
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
                # TODO: Corrigit o amount pra diminuir pro valor certo
                f'''update {transaction.order.type.value}
                    set amount = {transaction.order.amount}
                    where id = {transaction.order_id}''')
            cursor = self.db.execute(
                f'''insert into {transaction.order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                    values (
                        '{transaction.order.ticker}',
                        {transaction.amount},
                        {transaction.order.price},
                        '{transaction.order.expiry_date}', 
                        (select id from Client where name = {transaction.order.client_name}),
                        0
                    )''')
            new_id = cursor.lastrowid

        self.update_owned_stock(transaction.order.ticker,
                                transaction.amount,
                                transaction.order.client_name)
        
        transaction.state = TransactionState.COMPLETED

        self.coordinator.signalize_transaction_completed(
            transaction_id, new_id, transaction.order.type)
        self.save_state()

    def update_owned_stock(self,
                           ticker: str,
                           amount: float,
                           client_name: str):
        '''
        Atualiza ou insere uma quantidade de ações para um cliente.
        
        :param ticker: Nome da ação.
        :param amount: Quantidade de ações para ser adicionada/removida.
        :param client_id: Id do cliente no DB.
        '''
        # Pega o id da entrada no db, para a quantidade que o cliente tem daquela ação
        id_owned_stock = self.db.execute(
            f'''select id from OwnedStock 
                    where ticker = '{ticker}' and
                    client_id = (select id from Client where name = {client_name})''').fetchone()

        # Se tem a ação, atualiza a quantidade
        if id_owned_stock:
            id_owned_stock = id_owned_stock[0]
            self.db.execute(
                f'''update OwnedStock set amount={amount}
                        where id = {id_owned_stock}''')
        #Se não tem, adiciona a ação
        else:
            self.db.execute(
                f'''insert into OwnedStock (ticker, amount, client_id)
                        values ('{ticker}', {amount}, (select id from Client where name = {client_name}))''')
        
        self.db.commit()

    def cancel_transaction(self, transaction_id):
        if transaction_id in self.transactions:
            self.temporary_own_stock.pop(self.transactions[transaction_id].order.ticker)
            self.transactions[transaction_id].state = TransactionState.ABORTED
            self.save_state()

    def get_initial_state(self):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        else:
            file_path = self.path / 'temporary_log.json'
            with open(file_path, 'r+') as fp:
                data = json.loads(fp.read())
            self.temporary_own_stock = data['temporary_own_stock']
            transactions = {t['id']: ParticipantTransaction.from_dict('', t)
                            for t in data['transactions']}
            self.transactions = transactions
            
            for tid, transaction in self.transactions.items():
                if transaction.state != TransactionState.COMPLETED:
                    state = self.coordinator.get_transaction_state()
                    if state != TransactionState.ABORTED:
                        self.make_transaction(tid)
                    else:
                        self.transactions[tid].state = TransactionState.ABORTED
            
            self.save_state()
