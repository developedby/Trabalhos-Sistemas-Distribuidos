"""
Simulador de bolsa de valores.
"""

import datetime
import math
import os
import sqlite3
import sys
import threading
import time
from typing import Dict, List, Mapping, Sequence, Optional, Iterable

#os.environ["PYRO_LOGFILE"] = "stockmarket.log"
#os.environ["PYRO_LOGLEVEL"] = "DEBUG"

import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook
import yfinance as yf

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
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db_cursor = self.db.cursor()
        self.db_lock = threading.Lock()

        # Comentar pra db persistente
        # self.db_execute('delete from BuyOrder')
        # self.db_execute('delete from Client')
        # self.db_execute('delete from OwnedStock')
        # self.db_execute('delete from SellOrder')
        # self.db_execute('delete from StockTransaction')
        self.add_client("Market")

        # Começa a servir a aplicação pelo Pyro
        if use_pyro:
            daemon = pyro.Daemon()
            uri = daemon.register(self)
            nameserver.register('stockmarket', uri)
            nameserver._pyroRelease()
            self.running = True
            print("Rodando Stock Market")
            try:
                daemon.requestLoop()
            except KeyboardInterrupt:
                pass
            finally:
                self.close()

    def close(self):
        """Termina o aplicativo. Chamado após fechar a GUI e o Pyro."""
        self.db.close()

    def db_execute(self, command, *args, **kwargs):
        """Executa uma operação no DB."""
        with self.db_lock:
            return self.db_cursor.execute(command, *args, **kwargs)

    def update_owned_stock(self,
                           ticker: str,
                           change_amount: float,
                           client_id: int):
        '''
        Atualiza ou insere uma quantidade de ações para um cliente.
        
        :param ticker: Nome da ação.
        :param change_amount: Quantidade de ações para ser adicionada/removida.
        :param client_id: Id do cliente no DB.
        '''
        # Pega o id da entrada no db, para a quantidade que o cliente tem daquela ação
        id_owned_stock = self.db_execute(
            f'''select id from OwnedStock 
                    where ticker = '{ticker}' and
                    client_id = {client_id}''').fetchone()

        # Se tem a ação, atualiza a quantidade
        if id_owned_stock:
            id_owned_stock = id_owned_stock[0]
            self.db_execute(
                f'''update OwnedStock set amount=amount + {change_amount}
                        where id = {id_owned_stock}''')
        #Se não tem, adiciona a ação
        else:
            self.db_execute(
                f'''insert into OwnedStock (ticker, amount, client_id)
                        values ('{ticker}', {change_amount}, {client_id})''')
        
        self.db.commit()

    def create_transaction_log(self,
                               sell_order_id: int,
                               buy_order_id: int,
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
        self.db_execute(command)

    def mark_expired_orders_as_inactive(self):
        '''Marca as ordens ativas que já expiraram como inativas.'''
        self.db_execute(
            f"""update BuyOrder set active = 0 
                where active = 1 and 
                datetime(expiry_date)
                    < datetime('{datetime.datetime.now().strftime(DATETIME_FORMAT)}')""")

        self.db_execute(
            f"""update SellOrder set active = 0 
                where active = 1 and 
                datetime(expiry_date)
                    < datetime('{datetime.datetime.now().strftime(DATETIME_FORMAT)}')""")
        self.db.commit()

    def try_execute_active_orders(self):
        '''
        Tenta executar todas as ordens ativas.
        Como transações entre clientes internos sempre ocorrem no momento de criação das ordens,
        troca só com o mercado real.
        '''
        # Verifica se tem alguma ordem expirada
        # pra não executar uma transação que não deveria ocorrer
        self.mark_expired_orders_as_inactive()
        active_buy_orders = self.db_execute(
            ''' select * from BuyOrder 
                    where active = 1 ''').fetchall()

        active_sell_orders = self.db_execute(
            ''' select * from SellOrder 
                    where active = 1 ''').fetchall()
        # Tenta executa
        self.try_trade_with_market(OrderType.BUY, active_buy_orders)
        self.try_trade_with_market(OrderType.SELL, active_sell_orders)
    
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
            # Se a ação não existe mais no mercado, marca como inativa
            else:
                self.db_execute(
                    f''' update {order_type.value} set active = 0 
                        where id = {order_id}''')

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

        matching_type = order.type.get_matching()
        # Pega a quantidade de ações para serem transacionadas
        amount = 0
        matching_ids = []  # Ids dos clientes com quem pode transacionar
        order_amount = order.amount
        for matching_order in matching_data:
            amount += matching_order[3]
            matching_ids.append(matching_order[0])
            if (amount >= order_amount):
                break

        # Executa transações com os clientes dados
        for i, matching_id in enumerate(matching_ids):
            # Calcula quantidade e preço da transação
            transaction_amount = min(matching_data[i][3], order_amount)
            price = matching_data[i][4]

            # Para cada transação, cria uma ordem com o tamanho da transação
            self.db_execute(
                f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {transaction_amount}, {order.price}, '{order.expiry_date}', 
                        {client_id}, 0)''')

            new_id = self.db_cursor.lastrowid  # Id da ordem que foi criada

            # Atualiza no db a ordem correspondente com a qual a transação está sendo feita
            # Se a transação esgota a ordem correspondente, marca como inativa
            if (transaction_amount == matching_data[i][3]):
                self.db_execute(
                    f'''update {matching_type.value}
                        set active = 0 
                        where id = {matching_id}''')
            # Se não, atualiza para ter a quantidade que sobrou da ordem
            else:
                self.db_execute(
                    f'''update {matching_type.value}
                        set amount = {matching_data[i][3] - transaction_amount} 
                        where id = {matching_id}''')

            # Salva a transação e atualiza a quantidade de ações possuidas
            if (order.type == OrderType.SELL):
                self.create_transaction_log(
                    new_id, matching_id, transaction_amount, price)

                self.update_owned_stock(
                    order.ticker, -transaction_amount, client_id)
                self.update_owned_stock(
                    order.ticker, transaction_amount, matching_data[i][1])

            else:
                self.create_transaction_log(
                    matching_id, new_id, transaction_amount, price)

                self.update_owned_stock(
                    order.ticker, transaction_amount, client_id)
                self.update_owned_stock(
                    order.ticker, -transaction_amount, matching_data[i][1])

            order_amount -= transaction_amount
        
        self.db.commit()

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
                        0
                    )''')
            self.db_execute(command).fetchone()
            own_order_id = self.db_cursor.lastrowid
        # Se existe, marca como inativa
        else:
            command = f'update {order.type.value} set active = 0 where id = {order_id}'
            self.db_execute(command)
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
                0
            )''')
        self.db_execute(command)
        new_matching_id = self.db_cursor.lastrowid

        if (order.type == OrderType.SELL):
            sell_order_id = own_order_id
            buy_order_id = new_matching_id
            change_amount = -order.amount
        else:
            sell_order_id = new_matching_id
            buy_order_id = own_order_id
            change_amount = order.amount

        # Salva a transação no DB
        self.create_transaction_log(sell_order_id, buy_order_id, abs(change_amount), real_price)

        # Atualiza quantidade de ações do cliente
        self.update_owned_stock(order.ticker, change_amount, client_id)

        self.db.commit()

    def client_has_stock(self,
                         client_id: int,
                         ticker: str,
                         amount: Optional[float] = None) -> bool:
        """
        Retorna se o cliente tem ou não uma ação.
        Se `amount` foi dado, verifica se tem pelo menos a quantidade dada.
        """
        # Pega os dados do DB
        data = self.db_execute(
            f'''select os.* from Client as c 
                inner join OwnedStock as os on c.id = os.client_id 
                    where os.ticker = '{ticker}' and 
                    c.id = {client_id} '''
        ).fetchone()

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
        data = self.db_execute(
            f'''select id, name from Client 
                where name in {f"('{client_names[0]}')" if (len(client_names) == 1) else tuple(client_names)} '''
        ).fetchall()

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
        buy_data = self.db_execute(
            f'''select * from BuyOrder
                where 
                    client_id = (
                        select id from Client where name = '{client_name}'
                    )
                    {'and active = 1' if active_only else ""} '''
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

        sell_data = self.db_execute(
            f'''select * from SellOrder
                where 
                    client_id = (
                        select id from Client where name = '{client_name}'
                    )
                    {'and active = 1' if active_only else ""} '''
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
        self.db_execute(f"insert into Client(name) values ('{client_name}')")
        self.db.commit()
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

        # Pega as ordens que conseguem realizar a ordem sendo criada
        matching_type = order.type.get_matching()
        command = (
            f'''select * from {matching_type.value} 
            where ticker = '{order.ticker}' 
                and price {'>=' if order.type == OrderType.SELL else '<='} {target_price} 
                and active = 1
            order by price {'desc' if order.type == OrderType.SELL else 'asc'}''')
        matching_data = self.db_execute(command).fetchall()
        
        # Se os clientes internos tem um preço melhor que o do mercado transaciona o máximo possível
        if len(matching_data) > 0:
            print("Doing transaction with internal client")
            order.amount = self.trade_with_internal_clients(
                order, client_id, matching_data)
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
                self.db_execute(
                    f'''insert into {order.type.value}
                        (ticker, amount, price, expiry_date, client_id, active) 
                        values (
                            '{order.ticker}',
                            {order.amount},
                            {order.price},
                            '{order.expiry_date}', 
                            {client_id},
                            1)''')
        self.db.commit()
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
            print(1, data)
            quotes: Dict[str, Optional[float]] = {ticker: None for ticker in tickers}
            for ticker in quotes:
                quote = data.loc[:, ticker.upper()].values[0]
                print(2, quote)
                if not math.isnan(quote):
                    quotes[ticker] = round(float(quote), 2)
                    print(3, quotes)
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
        self.try_execute_active_orders()
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

        name_to_id = self.get_client_ids_by_names(client_names)
        ids = tuple(name_to_id.values())
        id_to_name = {name_to_id[name]: name for name in name_to_id}
        ids_str = str(ids) if len(ids) > 1 else f'({ids[0]})'

        # Pega as informações do DB
        command = (
            f"""select bo.ticker, so.client_id, bo.client_id, t.amount, t.price, t.datetime from
                StockTransaction as t
                inner join SellOrder as so on t.sell_id = so.id
                inner join BuyOrder as bo on t.buy_id = bo.id
                where (bo.client_id in {ids_str} or so.client_id in {ids_str})""" +
            (f"and datetime(t.datetime) >= datetime('{from_date}')"
                if from_date is not None else '')
        )
        data = self.db_execute(command)

        # Transforma em um formato mais amigavel, separando por cliente
        transactions = {client: [] for client in client_names}
        for entry in data:
            print(entry[5], from_date)
            if entry[1] in ids:
                transactions[id_to_name[entry[1]]].append(Transaction(
                    ticker=entry[0],
                    seller_name=id_to_name[entry[1]],
                    buyer_name=id_to_name[entry[2]] if entry[2] in id_to_name else "Market",
                    amount=entry[3],
                    price=entry[4],
                    datetime=datetime.datetime.strptime(entry[5], DATETIME_FORMAT)
                ))
            if entry[2] in ids:
                transactions[id_to_name[entry[2]]].append(Transaction(
                    ticker=entry[0],
                    seller_name=id_to_name[entry[1]] if entry[1] in id_to_name else "Market",
                    buyer_name=id_to_name[entry[2]],
                    amount=entry[3],
                    price=entry[4],
                    datetime=datetime.datetime.strptime(entry[5], DATETIME_FORMAT)
                ))
        return transactions

    @pyro.expose
    def get_stock_owned_by_client(self, client_name: str) -> Dict[str, float]:
        """Retorna a carteira de ações de um cliente."""
        command = f"""
            select ticker, amount from OwnedStock
            where client_id = (select id from Client where name = '{client_name}')
        """
        data = self.db_execute(command)
        return {entry[0]: entry[1] for entry in data}
