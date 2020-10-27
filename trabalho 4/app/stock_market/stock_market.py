"""
Simulador de bolsa de valores.
"""
import datetime
import math
import os
import sqlite3
import sys
import threading
from threading import Lock
import time
from typing import Dict, List, Mapping, Sequence, Optional, Iterable
from Pyro5 import client

#os.environ["PYRO_LOGFILE"] = "stockmarket.log"
#os.environ["PYRO_LOGLEVEL"] = "DEBUG"

import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook
import yfinance as yf

from .database import Database
from .transaction_operations import Coordinator, Participant, MarketParticipant
from ..consts import DATETIME_FORMAT
from ..enums import OrderType, MarketErrorCode
from ..order import Order, Transaction


class StockMarket:
    """
    Simulador de bolsa de valores.
    Usa a API yfinance para obter dados do mercado de ações real.
    Usa um banco de dados sqlite para armazenar os dados de clientes, ordens e transações.
    """
    def __init__(self, db_path: str, use_pyro=True):
        # Checa se o banco de dados existe
        if not os.path.exists(db_path):
            raise ValueError(f"The database file \"{db_path}\" doesn't exist.")

        # Para mostrar exceções remotas em um ofrmato melhor
        sys.excepthook = pyro_excepthook

        # Tenta se conectar com o nameserver
        nameserver = pyro.locate_ns()

        # Registra as serializações
        pyro.register_class_to_dict(Order, Order.to_dict)
        pyro.register_dict_to_class('Order', Order.from_dict)
        pyro.register_class_to_dict(Transaction, Transaction.to_dict)
        pyro.register_dict_to_class('Transaction', Transaction.from_dict)

        # Conecta com o banco de dados e inicializa
        self.db = Database(db_path)

        # Comentar pra db persistente
        # self.db.execute('delete from BuyOrder')
        # self.db.execute('delete from Client')
        # self.db.execute('delete from OwnedStock')
        # self.db.execute('delete from SellOrder')
        # self.db.execute('delete from StockTransaction')
        self.add_client("Market")

        # Registra a aplicação no Pyro
        self.daemon = pyro.Daemon()
        uri = self.daemon.register(self)

        # Carrega o Coordenador e os participantes pra cada cliente
        self.coordinator = Coordinator(self.db)
        client_names = self.db.execute_with_fetch('select name from Client', True)
        orders = {}
        for client in client_names:
            orders[client[0]] = self.get_client_orders_by_name(client[0], True)

        self.stock_locks: Dict[str, Dict[str, threading.Lock]] = {}
        self.participants = []
        for client_name in client_names:
            self.stock_locks[client_name[0]] = {}
            for order in orders[client_name[0]]:
                if order.ticker not in self.stock_locks[client_name[0]]:
                    self.stock_locks[client_name[0]][order.ticker] = threading.Lock()
            if client_name[0] != 'Market':
                self.participants.append(Participant(client_name[0], self.coordinator.uri, self.db, self.daemon))
        
        self.market_participant = MarketParticipant(self.coordinator.uri, self.db, self.daemon)
        self.coordinator.add_participants({
            participant.name: participant.uri
            for participant in self.participants
        })

        self.coordinator.participants['Market'] = self.market_participant.uri

        self.coordinator.get_initial_state()
        self.market_participant.get_initial_state()
        for participant in self.participants:
            participant.get_initial_state()

        # Registra no nameserver
        nameserver.register('stockmarket', uri)
        nameserver._pyroRelease()

        # Começa a rodar
        self.running = True
        print("Rodando Stock Market")
        try:
            self.daemon.requestLoop()
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self):
        """Termina o aplicativo. Chamado após fechar a GUI e o Pyro."""
        self.db.close()

    def mark_expired_orders_as_inactive(self):
        '''Marca as ordens ativas que já expiraram como inativas.'''
        self.db.execute(
            f"""update BuyOrder set active = 0 
                where active = 1 and 
                datetime(expiry_date)
                    < datetime('{datetime.datetime.now().strftime(DATETIME_FORMAT)}')""")

        self.db.execute(
            f"""update SellOrder set active = 0 
                where active = 1 and 
                datetime(expiry_date)
                    < datetime('{datetime.datetime.now().strftime(DATETIME_FORMAT)}')""")
    
    def try_execute_active_orders(self, order_type: OrderType):
        '''
        Tenta executar todas as ordens ativas do tipo order_type.
        Como transações entre clientes internos sempre ocorrem no momento de criação das ordens,
        troca só com o mercado real.
        '''

        all_client_names = set(self.stock_locks.keys())
        
        # Verifica se tem alguma ordem expirada
        # pra não executar uma transação que não deveria ocorrer
        self.mark_expired_orders_as_inactive()

        #Pega todas as travas de todas as ordens
        for client_name in self.stock_locks.keys():
            for ticker in self.stock_locks[client_name].keys():
                self.stock_locks[client_name][ticker].acquire()
        
        active_orders = self.db.execute_with_fetch(
            f''' select o.*, c.name 
                    from {order_type.value} as o inner join Client as c on o.client_id = c.id
                        where o.active = 1 ''', True)

        #Faz um dicionário de ordens ativas por cliente, subtrai os conjuntos para descobrir quem não tem ordem ativa
        orders_by_client = {}
        # if len(active_orders) > 0:
        #     print(active_orders[0])

        for data in active_orders:
            if data[7] not in orders_by_client:
                orders_by_client[data[7]] = set()    
            orders_by_client[data[7]].add(data[2])

        client_names_with_orders = set(orders_by_client.keys())
        # print(client_names_with_orders)

        #Libera todas as travas dos clientes sem ordens ativas
        for client_name in (all_client_names.difference(client_names_with_orders)):
            for ticker in self.stock_locks[client_name].keys():
                self.stock_locks[client_name][ticker].release()

        #Libera as travas das ações sem ordem ativa
        for client_name in client_names_with_orders:
            for ticker in self.stock_locks[client_name].keys():
                if ticker not in orders_by_client[client_name]:
                    self.stock_locks[client_name][ticker].release()

        # Tenta executar
        self.try_trade_with_market(order_type, active_orders)
    
    def try_trade_with_market(self,
                              order_type: OrderType,
                              order_data: Sequence[Sequence]):
        """
        Tenta transacionar um conjunto de ordens com o mercado real.
        Realiza as transações se o mercado está com um preço adequado.

        :param order_type: Tipo da ordem (compra ou venda).
        :param order_data: Conjunto de ordens para transacionar, no formato dado pelo sqlite.
        """
        for order_entry in order_data:
            ticker = order_entry[2]
            real_price = self.get_quotes([ticker])[ticker]  # Pega o preço no mercado real
            order_id = order_entry[0]
            # Se a ação existe no mercado (tem um preço), tenta realizar
            if real_price is not None:
                order_price = order_entry[4]
                client_id = order_entry[1]
                order = Order(
                    client_name='',  # Pro db não importa o nome do cliente
                    type_=order_type,
                    ticker=ticker,
                    amount=order_entry[3],
                    price=order_price,
                    expiry_date=datetime.datetime.strptime(order_entry[5], DATETIME_FORMAT),
                    active=True
                )
                # Se tiver um preço adequado, executa a transação
                if ((order_type == OrderType.BUY) and (real_price < order_price)
                        or ((order_type == OrderType.SELL) and (real_price > order_price))):
                    self.trade_with_market(order, client_id, real_price, order_id)
                
                #Libera a trava dessa ação
                self.stock_locks[order_entry[7]][ticker].release()
            # Se a ação não existe mais no mercado, marca como inativa
            else:
                self.db.execute(
                    f''' update {order_type.value} set active = 0 
                        where id = {order_id}''')
                #Libera as travas das ação que não existe mais
                self.stock_locks[order_entry[7]][ticker].release()

    def trade_with_internal_clients(self,
                                    order: Order,
                                    client_id: int,
                                    matching_data: Sequence[Sequence]):
        '''
        Executa uma ordem de um cliente, trocando com clientes internos.

        Sempre realiza a transação, então deve ser chamada apenas depois de verificar
        se as transações vão ser válidas.

        :param order: A ordem que vai realizar.
        :param client_id: Id no DB do cliente que criou a ordem.
        :param matching_data: Ordens com as quais vai realizar as transações.
        '''

        # Coloca a ordem que quer realizar no DB
        order_id = self.db.execute(
            f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                values (
                    '{order.ticker}', {order.amount}, {order.price}, '{order.expiry_date}', 
                    {client_id}, 1
                )''')

        # Pega a quantidade de ações para serem transacionadas
        amount = 0
        matching_ids = []  # Ids dos clientes com quem pode transacionar
        matching_names = {} #Nome dos clientes com quem pode transacionar
        order_amount = order.amount
        for matching_order in matching_data:
            amount += matching_order[3]
            matching_ids.append(matching_order[0])
            matching_names[matching_order[0]] = matching_order[7]
            if (amount >= order_amount):
                break
        
        #Libera a trava dos clientes que não vão fazer transação
        for client_name in self.stock_locks.keys():
            if order.ticker in self.stock_locks[client_name].keys():
                if client_name not in matching_names.values() and client_name != order.client_name:
                    self.stock_locks[client_name][order.ticker].release()

        # Executa transações com os clientes dados
        for i, matching_id in enumerate(matching_ids):
            # Calcula quantidade e preço da transação

            transaction_amount = min(matching_data[i][3], order_amount)
            price = matching_data[i][4]
            if order.type == OrderType.BUY:
                buy_order_id = order_id
                sell_order_id = matching_id
            else:
                sell_order_id = order_id
                buy_order_id = matching_id
            self.coordinator.open_transaction(buy_order_id, sell_order_id, transaction_amount, price)

            #Libera a trava do cliente que transacionou
            self.stock_locks[matching_names[matching_id]][order.ticker].release()
            order_amount -= transaction_amount

        return order_amount

    def trade_with_market(self,
                          order: Order,
                          client_id: int,
                          real_price: float,
                          order_id: int = None):
        '''
        Executa uma transação com o mercado real.
        Executa uma ordem inteira.
        Só é executada quando tem certeza que vai trocar com o mercado.

        :param order: Ordem que vai realizar com o mercado.
        :param client_id: Id no DB do cliente que criou a ordem.
        :param real_price: Preço da ação no mercado real.
        :param order_id: Id no DB da ordem. Se None, cria uma ordem nova no DB.
        '''
        # Se a ordem não existe no DB, cria uma nova com os valroes de `order`

        if order_id is None:
            command = (
                f'''insert into {order.type.value}
                    (ticker, amount, price, expiry_date, client_id, active)
                    values (
                        '{order.ticker}',
                        {order.amount},
                        {order.price},
                        '{order.expiry_date}',
                        {client_id},
                        1
                    )''')
            own_order_id = self.db.execute(command)
        else:
            own_order_id = order_id

        matching_type = order.type.get_matching()
        # Cria a ordem correspondente no nome do mercado, com qual vai fazer a transação
        command = (
            f'''insert into {matching_type.value}
            (ticker, amount, price, expiry_date, client_id, active)
            values (
                '{order.ticker}',
                {order.amount},
                {real_price},
                '{order.expiry_date}',
                (select id from Client where name = 'Market'),
                1
            )''')
        new_matching_id = self.db.execute(command)

        if order.type == OrderType.BUY:
                buy_order_id = own_order_id
                sell_order_id = new_matching_id
        else:
            sell_order_id = own_order_id
            buy_order_id = new_matching_id

        self.coordinator.open_transaction(buy_order_id, sell_order_id, order.amount, real_price)

    def client_has_stock(self,
                         client_id: int,
                         ticker: str,
                         amount: Optional[float] = None) -> bool:
        """
        Retorna se o cliente tem ou não uma ação.
        Se `amount` foi dado, verifica se tem pelo menos a quantidade dada.
        """
        # Pega os dados do DB
        data = self.db.execute_with_fetch(
            f'''select os.* from Client as c 
                inner join OwnedStock as os on c.id = os.client_id 
                    where os.ticker = '{ticker}' and 
                    c.id = {client_id} ''', False
        )

        # Se não tem a ação
        if not data:
            return False

        # Verifica a quantidade, se precisa
        if amount is not None:
            owned_stock = data[2]
            if owned_stock >= amount:
                return True
            else:
                return False
        else:
            return True

    def get_client_ids_by_names(self,
                                client_names: Sequence[str]) -> Mapping[str, Optional[int]]:
        """
        Retorna um dicionario com os ids de cada nome dado.
        Se o nome não existe, tem valor None.
        """
        data = self.db.execute_with_fetch(
            f'''select id, name from Client 
                where name in {f"('{client_names[0]}')" if (len(client_names) == 1) else tuple(client_names)} ''', True
        )

        id_map = {name: None for name in client_names}
        for entry in data:
            if entry[1] in id_map:
                id_map[entry[1]] = entry[0]
        return id_map

    def get_client_orders_by_name(self,
                                  client_name: str,
                                  active_only: bool) -> List[Order]:
        """
        Retorna todas as ordens de um cliente.

        :param client_name: Nome do cliente.
        :param active_only: Se retorna só as ordens ativas, ou se retorna todas.
        """
        orders = []
        buy_data = self.db.execute_with_fetch(
            f'''select * from BuyOrder
                where 
                    client_id = (
                        select id from Client where name = '{client_name}'
                    )
                    {'and active = 1' if active_only else ""} ''', True
        )
        for order in buy_data:
            orders.append(Order(
                    client_name=client_name,
                    type_=OrderType.BUY,
                    ticker=order[2],
                    amount=order[3],
                    price=order[4],
                    expiry_date=datetime.datetime.strptime(order[5], DATETIME_FORMAT),
                    active=bool(order[6])
            ))

        sell_data = self.db.execute_with_fetch(
            f'''select * from SellOrder
                where 
                    client_id = (
                        select id from Client where name = '{client_name}'
                    )
                    {'and active = 1' if active_only else ""} ''', True
        )
        for order in sell_data:
            orders.append(Order(
                    client_name=client_name,
                    type_=OrderType.SELL,
                    ticker=order[2],
                    amount=order[3],
                    price=order[4],
                    expiry_date=datetime.datetime.strptime(order[5], DATETIME_FORMAT),
                    active=bool(order[6])
            ))

        return orders

    @pyro.expose
    def add_client(self, client_name: str) -> MarketErrorCode:
        '''Insere um novo cliente no sistema.'''

        # Verifica se cliente já existe
        client_id = self.get_client_ids_by_names((client_name,))[client_name]
        if client_id is not None:
            return MarketErrorCode.CLIENT_ALREADY_EXISTS
        
        # Adiciona cliente no DB
        self.db.execute(f"insert into Client(name) values ('{client_name}')")

        # Cria um novo participante e manda pro coordenador
        if (client_name != 'Market'):
            new_participant = Participant(
                client_name, self.coordinator.uri, self.db, self.daemon)
            self.participants.append(new_participant)
            self.coordinator.add_participants({new_participant.name: new_participant.uri})
            new_participant.get_initial_state()

        print(f"Created client {client_name}")
        return MarketErrorCode.SUCCESS

    @pyro.expose
    def check_ticker_exists(self, ticker: str) -> bool:
        """retorna se uma ação existe na api."""
        data = yf.download(ticker, period="1d")
        return len(data) > 0

    @pyro.expose
    def create_order(self, order: Order) -> MarketErrorCode:
        '''Cria ordem de compra ou venda e, se possível, realiza transações com ela.'''
        # Verifica se a ordem expirou
        if (datetime.datetime.now() >= order.expiry_date):
            print("Order is expired")
            return MarketErrorCode.EXPIRED_ORDER

        # Verifica se o cliente existe
        client_id = self.get_client_ids_by_names((order.client_name,))[order.client_name]
        if client_id is None:
            print("Client not found")
            return MarketErrorCode.UNKNOWN_CLIENT

        # Atualiza o estado de expiração das ordens
        self.mark_expired_orders_as_inactive()

        if not order.ticker in self.stock_locks[order.client_name].keys():
            self.stock_locks[order.client_name][order.ticker] = threading.Lock()

        #Pega a trava para a ordem desse cliente
        self.stock_locks[order.client_name][order.ticker].acquire()
        # Se quer vender, checa se tem ações o suficiente
        if order.type == OrderType.SELL:
            if not self.client_has_stock(client_id, order.ticker, amount=order.amount):
                print("Client doesn't have enough stock to sell")
                return MarketErrorCode.NOT_ENOUGH_STOCK

        # Pega o valor do mercado
        real_price = self.get_quotes([order.ticker])[order.ticker]
        if real_price is None:
            print("Ticker not found in the market")
            return MarketErrorCode.UNKNOWN_TICKER

        # Calcula o preço com que quer realizar a transação
        # É sempre o máximo entre a ordem criada e o preço do mercado real
        # O maximo foi escolhido para permitir transações tanto com internos quanto com o mercado
        target_price = max(order.price, real_price)

        # Pega a trava de todas os clientes que possuem a ação
        for client_name in self.stock_locks.keys():
            if order.ticker in self.stock_locks[client_name].keys() and client_name != order.client_name:
                self.stock_locks[client_name][order.ticker].acquire()
        
        # Pega as ordens que conseguem realizar a ordem sendo criada
        matching_type = order.type.get_matching()
        command = (
            f'''select o.*, c.name 
                from {matching_type.value} as o inner join Client as c on o.client_id = c.id
                    where o.ticker = '{order.ticker}' 
                        and o.price {'>=' if order.type == OrderType.SELL else '<='} {target_price} 
                        and o.active = 1
                order by o.price {'desc' if order.type == OrderType.SELL else 'asc'}''')
        matching_data = self.db.execute_with_fetch(command, True)


        # Se os clientes internos tem um preço melhor que o do mercado transaciona o máximo possível
        if len(matching_data) > 0:
            print("Doing transaction with internal client")
            order.amount = self.trade_with_internal_clients(
                order, client_id, matching_data)
        else:
            # Libera a trava de todas os clientes que possuem a ação
            for client_name in self.stock_locks.keys():
                if order.ticker in self.stock_locks[client_name].keys() and client_name != order.client_name:
                    self.stock_locks[client_name][order.ticker].release()
        # Se sobrou ações na ordem
        if order.amount > 0:
            # Troca com o mercado caso tenha um preço que realize a ordem
            if ((order.type == OrderType.SELL and order.price <= real_price)
                    or (order.type == OrderType.BUY and order.price > real_price)):
                print("Doing transaction with market")
                self.trade_with_market(order, client_id, real_price)
            # Caso contrario, guarda o que sobrou da ordem no DB
            else:
                print("Creating order")
                self.db.execute(
                    f'''insert into {order.type.value}
                        (ticker, amount, price, expiry_date, client_id, active) 
                        values (
                            '{order.ticker}',
                            {order.amount},
                            {order.price},
                            '{order.expiry_date}', 
                            {client_id},
                            1)''')

        #Libera a trava do cliente principal
        self.stock_locks[order.client_name][order.ticker].release()
        return MarketErrorCode.SUCCESS

    @pyro.expose
    def get_quotes(self, tickers: Sequence[str]) -> Dict[str, Optional[float]]:
        """Retorna a cotação atual de um conjunto de ações."""
        # A cotação atual é sempre a do mercado
        # Os clientes internos tem ordem de compra ativa maior que o preço do mercado
        # Porque eles já teriam vendido para o mercado

        # Dependendo do numero de ações para pegar cotação faz algo diferente
        # por causa da estrutura de dados que o yfinance usa
        print(f"get_quotes: {len(tickers)} tickers - {tickers}")
        if len(tickers) == 0:
            return {}
        data = yf.download(tickers, period="1d")["Adj Close"]
        if len(tickers) == 1:
            quotes = {tickers[0]: round(float(data.values[0]), 2) if len(data.values) > 0 else None}
        else:
            quotes: Dict[str, Optional[float]] = {ticker: None for ticker in tickers}
            for ticker in quotes:
                quote = data.loc[:, ticker.upper()].values[0]
                if not math.isnan(quote):
                    quotes[ticker] = round(float(quote), 2)
        return quotes

    @pyro.expose
    def get_orders(self,
                   client_names: Sequence[str],
                   active_only: bool) -> Dict[str, List[Order]]:
        """
        Retorna as ordens de compra e venda de um conjunto de clientes.
        
        :param client_names: Nome dos clientes.
        :param active_only: Se retorna só as ordens ativas, ou todas.
        """
        self.try_execute_active_orders(OrderType.BUY)
        self.try_execute_active_orders(OrderType.SELL)
        orders = {}
        for client in client_names:
            orders[client] = self.get_client_orders_by_name(client, active_only)
        return orders

    @pyro.expose
    def get_transactions(
        self,
        client_names: Sequence[str],
        from_date: Optional[str] = None) -> Dict[str, List[Transaction]]:
        """
        Retorna as transações executadas por um conjunto de clientes.

        :param client_names: Nome dos clientes.
        :param from_date: Se não for None, retorna só as transações a partir de uma data-hora.
        """
        if not client_names:
            return {}

        client_name_to_id = self.get_client_ids_by_names(client_names)
        ids = tuple(client_name_to_id.values())
        client_id_to_name = {client_name_to_id[name]: name for name in client_name_to_id}
        ids_str = str(ids) if len(ids) > 1 else f'({ids[0]})'

        # Pega as informações do DB
        command = (
            f"""select bo.ticker, so.client_id, bo.client_id, t.amount, t.price, t.datetime, t.id from
                StockTransaction as t
                inner join SellOrder as so on t.sell_id = so.id
                inner join BuyOrder as bo on t.buy_id = bo.id
                where (bo.client_id in {ids_str} or so.client_id in {ids_str})""" +
            (f"and datetime(t.datetime) >= datetime('{from_date}')"
                if from_date is not None else '')
        )
        data = self.db.execute_with_fetch(command, True)

        # Transforma em um formato mais amigavel, separando por cliente
        transactions = {client: [] for client in client_names}
        for entry in data:
            if entry[1] in ids:
                transactions[client_id_to_name[entry[1]]].append(Transaction(
                    ticker=entry[0],
                    seller_name=client_id_to_name[entry[1]],
                    buyer_name=client_id_to_name[entry[2]] if entry[2] in client_id_to_name else "Market",
                    amount=entry[3],
                    price=entry[4],
                    datetime=datetime.datetime.strptime(entry[5], DATETIME_FORMAT),
                    id_=entry[6]
                ))
            if entry[2] in ids:
                transactions[client_id_to_name[entry[2]]].append(Transaction(
                    ticker=entry[0],
                    seller_name=client_id_to_name[entry[1]] if entry[1] in client_id_to_name else "Market",
                    buyer_name=client_id_to_name[entry[2]],
                    amount=entry[3],
                    price=entry[4],
                    datetime=datetime.datetime.strptime(entry[5], DATETIME_FORMAT),
                    id_=entry[6]
                ))
        return transactions

    @pyro.expose
    def get_stock_owned_by_client(self, client_name: str) -> Dict[str, float]:
        """Retorna a carteira de ações de um cliente."""
        return self.db.get_stock_owned_by_client(client_name)
