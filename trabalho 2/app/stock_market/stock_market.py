import datetime
import math
import os
import sqlite3
import sys
import time
from typing import List, Mapping, Sequence, Optional, Iterable

os.environ["PYRO_LOGFILE"] = "stockmarket.log"
os.environ["PYRO_LOGLEVEL"] = "DEBUG"

import Pyro5.api as pyro
import yfinance as yf

from ..enums import OrderType, MarketErrorCode
from ..order import Order, Transaction
from .gui import StockMarketGui


class StockMarket:
    def __init__(self, db_path: str, use_pyro=True):
        # Checa se o banco de dados existe
        if not os.path.exists(db_path):
            raise ValueError(f"The database file \"{db_path}\" doesn't exist.")
        # Tenta se conectar com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com o banco de dados e inicializa
        self.db = sqlite3.connect(db_path)
        self.db_cursor = self.db.cursor()
        self.db_cursor.execute('delete from BuyOrder')
        self.db_cursor.execute('delete from Client  ')
        self.db_cursor.execute('delete from OwnedStock')
        self.db_cursor.execute('delete from SellOrder')
        self.db_cursor.execute('delete from StockTransaction')
        self.add_client("Market")

        # Cria a GUI
        self.gui = StockMarketGui(self, daemon=True)

        # Começa a servir a aplicação pelo Pyro
        if use_pyro:
            self.daemon = pyro.Daemon()
            uri = self.daemon.register(self)
            nameserver.register('stockmarket', uri)
            self.running = True
            print("Rodando Stock Market")
            self.daemon.requestLoop(loopCondition=lambda: self.running)
            self.close()

    def close(self):
        """Termina o aplicativo. Chamado após fechar a GUI e o Pyro."""
        self.db.close()

    def check_ticker_exists(self, ticker: str) -> bool:
        """Verifica se a ação existe na api."""
        dumb_data = yf.download(ticker, period="1d")
        return len(dumb_data) > 0

    def update_owned_stock(self, ticker: str, change_amount: float, client_id: int):
        '''Atualiza ou insere uma quantidade de ações para um cliente.'''
        # Pega o id da entrada no db, para a quantidade que o cliente tem daquela ação
        id_owned_stock = self.db_cursor.execute(
            f'''select id from OwnedStock 
                    where ticker = '{ticker}' and
                    client_id = {client_id}''').fetchone()
        # Se tem a ação, atualiza a quantidade
        if id_owned_stock:
            id_owned_stock = id_owned_stock[0]
            self.db_cursor.execute(
                f'''update OwnedStock set amount=amount + {change_amount}
                        where id = {id_owned_stock}''')
        #Se não tem, adiciona a ação
        else:
            self.db_cursor.execute(
                f'''insert into OwnedStock (ticker, amount, client_id)
                        values ('{ticker}', {change_amount}, {client_id})''')
        
        self.db.commit()

    def create_transaction_log(self,
                               sell_order_id: int,
                               buy_order_id: int,
                               transaction_amount: float,
                               trade_price: float):
        """Cria uma entrada no log de transações."""
        self.db_cursor.execute(
            f'''insert into StockTransaction (sell_id, buy_id, amount, price, datetime)
            values (
                {sell_order_id},
                {buy_order_id},
                {transaction_amount},
                {trade_price},
                datetime('now')
            )''')

    def mark_expired_orders_as_inactive(self):
        '''Marca as ordens ativas que já expiraram como inativas.'''

        self.db_cursor.execute(
            ''' update BuyOrder set active = 0 
                    where active = 1 and 
                    datetime(expiry_date) < datetime('now')''')

        self.db_cursor.execute(
            ''' update SellOrder set active = 0 
                    where active = 1 and 
                    datetime(expiry_date) < datetime('now')''')
        self.db.commit()

    def try_execute_active_orders(self):
        '''Tenta executar todas as transações que estão em espera com o mercado.'''
        self.mark_expired_orders_as_inactive()
        active_buy_orders = self.db_cursor.execute(
            ''' select * from BuyOrder 
                    where active = 1 ''').fetchall()
        
        active_sell_orders = self.db_cursor.execute(
            ''' select * from SellOrder 
                    where active = 1 ''').fetchall()
        
        self.try_trade_with_market(OrderType.BUY, active_buy_orders)
        self.try_trade_with_market(OrderType.SELL, active_sell_orders)
    
    def try_trade_with_market(self, order_type: OrderType, order_data: Sequence[Sequence]):
        for order_entry in order_data:
            ticker = order_entry[2]
            real_price = self.get_quotes([ticker])[ticker]
            order_id = order_entry[0]
            if real_price is not None:
                order_price = order_entry[4]
                client_id = order_entry[1]
                order = Order(
                    client_name='',  # Pro db não importa o nome do cliente
                    type_=order_type,
                    ticker=ticker,
                    amount=order_entry[3],
                    price=order_price,
                    expiry_date=datetime.datetime.strptime(order_entry[5], "%Y-%m-%d %H:%M:%S"),
                    active=True
                )

                # Se tiver um preço adequado, executa a transação
                if ((order_type == OrderType.BUY) and (real_price < order_price)
                        or ((order_type == OrderType.SELL) and (real_price > order_price))):
                    self.trade_with_market(order, client_id, real_price, order_type.get_matching(), order_id)
            # A ação não existe mais no mercado
            else:
                self.db_cursor.execute(
                    f''' update {order_type.value} set active = 0 
                        where id = {order_id}''')

    def trade_with_internal_clients(self,
                                    matching_data: Sequence[Sequence],
                                    order: Order,
                                    client_id: int,
                                    matching_type: OrderType):
        '''Executa uma ou mais transações com clientes internos.'''

        # Pega a quantidade de ações para serem transacionadas
        amount = 0
        matching_ids = []
        order_amount = order.amount
        for matching_order in matching_data:
            amount += matching_order[3]
            matching_ids.append(matching_order[0])
            if (amount >= order_amount):
                break

        # Executa transações
        for i, matching_id in enumerate(matching_ids):
            # Calcula quantidade e preço da transação
            transaction_amount = min(matching_data[i][3], order_amount)
            price = matching_data[i][4]

            # Salva a ordem no db
            self.db_cursor.execute(
                f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {transaction_amount}, {order.price}, '{order.expiry_date}', 
                        {client_id}, 0)''')

            new_id = self.db_cursor.lastrowid
            
            # Atualiza no db a ordem correspondente
            if (transaction_amount == matching_data[i][3]):
                self.db_cursor.execute(
                    f'''update {matching_type.value} set active = 0 
                            where id = {matching_id}''')
            else:
                self.db_cursor.execute(
                    f'''update {matching_type.value} set amount = {matching_data[i][3] - transaction_amount} 
                            where id = {matching_id}''')
        
            # Salva a transação e atualiza a quantidade de ações possuidas
            if (order.type == OrderType.SELL):
                self.create_transaction_log(new_id, matching_id, transaction_amount, price)

                self.update_owned_stock(order.ticker, -transaction_amount, client_id)
                self.update_owned_stock(order.ticker, transaction_amount, matching_data[i][1])
                
            else:
                self.create_transaction_log(matching_id, new_id, transaction_amount, price)

                self.update_owned_stock(order.ticker, transaction_amount, client_id)
                self.update_owned_stock(order.ticker, -transaction_amount, matching_data[i][1])
            
            order_amount -= transaction_amount
        
        self.db.commit()

        return order_amount

    def trade_with_market(self,
                          order: Order,
                          client_id: int,
                          real_price: float,
                          matching_type: OrderType,
                          order_id: int = None):
        '''
        Executa uma transação com o mercado.
        Executa uma ordem inteira.
        Só é executada quando tem certeza que vai trocar com o mercado.'''
        # Salva a ordem no banco
        if order_id is None:    
            self.db_cursor.execute(
                f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {order.amount}, {order.price}, '{order.expiry_date}',
                        {client_id}, 0)''').fetchone()
            own_order_id = self.db_cursor.lastrowid

        # Atualiza a ordem no banco
        else:
            self.db_cursor.execute(
                    f'''update {order.type.value} set active = 0 
                            where id = {order_id}''')
            own_order_id = order_id

        self.db_cursor.execute(
            f'''insert into {matching_type.value} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {order.amount}, {real_price}, '{order.expiry_date}',
                        (select id from Client where name = 'Market'), 0)''').fetchone()
        new_matching_id = self.db_cursor.lastrowid

        if (order.type == OrderType.SELL):
            sell_order_id = own_order_id
            buy_order_id = new_matching_id
            change_amount = -order.amount
        else:
            sell_order_id = new_matching_id
            buy_order_id = own_order_id
            change_amount = order.amount

        # Salva o log
        self.create_transaction_log(sell_order_id, buy_order_id, abs(change_amount), real_price)

        # Atualiza quantidade de ações
        self.update_owned_stock(order.ticker, change_amount, client_id)            

        self.db.commit()

    def add_client(self, client_name: str) -> MarketErrorCode:
        '''Insere um novo cliente no sistema.'''

        #Verifica se cliente já existe
        client_id = self.get_client_ids_by_names((client_name,))[client_name]
        if client_id is not None:
            return MarketErrorCode.CLIENT_ALREADY_EXISTS
        
        #Adiciona cliente
        self.db_cursor.execute(
            f'''insert into Client(name) 
                    values ('{client_name}')''')
        self.db.commit()
        return MarketErrorCode.SUCCESS

    def client_has_stock(self,
                         client_id: int,
                         ticker: str,
                         amount: Optional[float] = None) -> bool:
        """Retorna se o cliente tem ou não uma ação, ou uma quantidade dela."""
        data = self.db_cursor.execute(
            f'''select os.* from Client as c 
                inner join OwnedStock as os on c.id = os.client_id 
                    where os.ticker = '{ticker}' and 
                    c.id = {client_id} '''
        ).fetchone()

        if not data:
            return False

        if amount is not None:
            owned_stock = data[2]
            if owned_stock >= amount:
                return True
            else:
                return False
        else:
            return True

    def get_client_ids_by_names(self, client_names: Sequence[str]) -> Mapping[str, Optional[int]]:
        """Retorna um dicionario dos nomes para os ids. Se o nome não existe, tem valor None."""
        data = self.db_cursor.execute(
            f'''select id, name from Client 
                where name in {f"('{client_names[0]}')" if (len(client_names) == 1) else tuple(client_names)} '''
        ).fetchall()

        id_map = {name: None for name in client_names}
        for entry in data:
            if entry[1] in id_map:
                id_map[entry[1]] = entry[0]
        return id_map

    def get_client_orders_by_name(self, client_name: str, active_only: bool) -> Sequence[Order]:
        """
        Pega todas as ordens de um cliente.

        :param client_name: Nome do cliente.
        :param active_only: Se retorna só as ordens ativas, ou se retorna todas.
        """
        orders = []
        buy_data = self.db_cursor.execute(
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
                    expiry_date=datetime.datetime.strptime(order[5], "%Y-%m-%d %H:%M:%S"),
                    active=bool(order[6])
            ))

        sell_data = self.db_cursor.execute(
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
                    expiry_date=datetime.datetime.strptime(order[5], "%Y-%m-%d %H:%M:%S"),
                    active=bool(order[6])
            ))

        return orders

    @pyro.expose
    def create_order(self, order: Order) -> MarketErrorCode:
        '''
        Cria ordem de compra ou venda e,
        se possível, executa a transação.
        '''
        # Verifica se a ordem é valida
        if (order.is_expired()):
            print("Order is expired")
            return MarketErrorCode.EXPIRED_ORDER

        # Verifica se cliente existe
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
        
        #Checa por possíveis combinações
        matching_type = order.type.get_matching()

        #Se eu quero vender, verifico se os clientes internos querem comprar por um preço maior que o do mercado (prioriza quem está vendendo)
        target_price = max(order.price, real_price)

        matching_data = self.db_cursor.execute(
            f'''select * from {matching_type.value} 
                where ticker = '{order.ticker}' and 
                price {'>=' if order.type == OrderType.SELL else '<='} {target_price} and 
                active = 1 order by price {'desc' if order.type == OrderType.SELL else 'asc'}''').fetchall()
        
        #Se os clientes internos tem um preço melhor que o do mercado transaciona o máximo possível
        if (len(matching_data) > 0):
            print("Doing transaction with internal client")
            order.amount = self.trade_with_internal_clients(matching_data, order, client_id, matching_type)
        if (order.amount > 0):
            #Se o mercado tem um preço melhor que o dos clientes internos restantes
            if ((order.type == OrderType.SELL and order.price <= real_price)
                    or (order.type == OrderType.BUY and order.price > real_price)):
                print("Doing transaction with market")
                self.trade_with_market(order, client_id, real_price, matching_type)
            else:
                print("Creating order")
                self.db_cursor.execute(
                    f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active) 
                            values ('{order.ticker}', {order.amount}, {order.price}, '{order.expiry_date}', 
                            {client_id}, 1)''')
        self.db.commit()
        return MarketErrorCode.SUCCESS

    @pyro.expose
    def get_quotes(self, tickers: Sequence[str]) -> Mapping[str, Optional[float]]:
        """Retorna a cotação atual de um conjunto de ações."""
        # A cotação atual é sempre a do mercado
        # Os clientes internos tem ordem de compra ativa maior que o preço do mercado
        # Porque eles já teriam vendido para o mercado
        data = yf.download(tickers, period="1d")["Adj Close"]
        if len(tickers) == 1:
            quotes = {tickers[0]: data.values[0] if data.values else None}
        else:
            quotes = {ticker: None for ticker in tickers}
            for ticker in quotes:
                quote = data.loc[:, ticker].values[0]
                if not math.isnan(quote):
                    quotes[ticker] = float(quote)
        return quotes

    @pyro.expose
    def get_orders(self, client_names: Sequence[str], active_only: bool) -> Mapping[str, Sequence[Order]]:
        """Retorna as ordens de compra e venda de um conjunto de clientes."""
        self.try_execute_active_orders()
        orders = {}
        for client in client_names:
            orders[client] = self.get_client_orders_by_name(client, active_only)
        return orders

    @pyro.expose
    def get_transactions(self,
                         client_names: Sequence[str],
                         from_date: Optional[datetime.datetime] = None) -> Mapping[str, Sequence[Transaction]]:

        name_to_id = self.get_client_ids_by_names(client_names)
        ids = tuple(name_to_id.values())
        id_to_name = {name_to_id[name]: name for name in name_to_id}
        data = self.db_cursor.execute(
            f"""select bo.ticker, so.client_id, bo.client_id, t.amount, t.price, t.datetime from
                StockTransaction as t
                inner join SellOrder as so on t.sell_id = so.id
                inner join BuyOrder as bo on t.buy_id = bo.id
                where (bo.client_id in {ids} or so.client_id in {ids})""" +
            (f"and datetime(t.datetime) >= datetime({from_date.strftime('%Y-%m-%d %H:%M:%S')})"
                if from_date is not None else ''))
        transactions = {client: [] for client in client_names}
        for entry in data:
            if entry[1] in ids:
                transactions[id_to_name[entry[1]]].append(Transaction(
                    ticker=entry[0],
                    seller_name=id_to_name[entry[1]],
                    buyer_name=id_to_name[entry[2]],
                    amount=entry[3],
                    price=entry[4],
                    datetime=datetime.datetime.strptime(entry[5], "%Y-%m-%d %H:%M:%S")
                ))
            if entry[2] in ids:
                transactions[id_to_name[entry[2]]].append(Transaction(
                    ticker=entry[0],
                    seller_name=id_to_name[entry[1]],
                    buyer_name=id_to_name[entry[2]],
                    amount=entry[3],
                    price=entry[4],
                    datetime=datetime.datetime.strptime(entry[5], "%Y-%m-%d %H:%M:%S")
                ))
        return transactions
