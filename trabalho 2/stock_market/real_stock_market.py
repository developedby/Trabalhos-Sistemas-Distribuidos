classimport datetime
import json

import Pyro5.api as pyro

from .gui import StockMarketGui
from ..enums import OrderType
from ..order import Order
import yfinance as yf
import sqlite3

the_stock_market = None

@pyro.expose
class StockMarketPyro:
    def create_order(self, order: Order):
        global the_stock_market
        the_stock_market.create_order(order)

    def get_quotes(self, tickers: Collection[str]):
        global the_stock_market
        quotes = {ticker: float('inf') for ticker in tickers}
        for order in the_stock_market.sell_orders:
            if order.ticker in tickers:
                quotes[order.ticker] = min(order.price, quotes[order.ticker])
        return quotes

    def get_orders(self, client_ids: Collection[str]):
        global the_stock_market
        pass

    def get_stock_list(self):
        global the_stock_market
        return the_stock_market.stocks


class StockMarket:
    def __init__(self):
        stocks = set()
        buy_orders = []
        sell_orders = []
        if init_from_file:
            self._init_from_file()

        self.gui = StockMarketGui()
        self.db = sqlite3.connect('stock_market.db')
        self.db_cursor = self.db.cursor()

    def _init_pyro(self):
        global the_stock_market
        the_stock_market = self
        # Registra como objeto Pyro
        self.daemon = pyro.Daemon()
        uri = self.daemon.register(StockMarketPyro)

        # Registra o nome no nameserver
        name_server = pyro.locate_ns()
        name_server.register('stockmarket', uri)

    def start(self):
        self.db = sqlite3.connect('stock_market.db')
        self.db_cursor = self.db.cursor()
        # self.gui.start()
        # self.daemon.requestLoop()

    def check_ticker(self, ticker: str):
        """Verifica se ação existe na api"""
        dumb_data = yf.download(ticker, period="1d")
        return len(dumb_data) > 0

    def get_quotes(self, stocks):
        data = yf.download(stocks, period="1d")
        return data.values
        #Mostrar para o usuário

    def create_order(self, order: Order):
        '''Cria ordem de compra ou venda, se possível executa a transação'''
        
        self.check_orders_are_expired()

        
        data = self.db_cursor.execute(f'select os.* from Client as c inner join OwnedStock as os on c.id = os.client_id where os.ticker = {order.ticker}').fetchall()
        current_ticker_amount = data[2] if (len(data) > 0) else 0
        #Checa se o cliente tem as ações que ele quer vender
        if ((order.type_ == OrderType.SELL) and ((len(data) == 0) or current_amount < order.amount)):
            #Avisa usuário?
            #TODO: Return code
            return
        else:
            real_price = self.get_quotes([order.ticker]):
            #Se a ação não existe
            if not real_price:
                #Avisa usuário?
                #TODO: Return code
                return
            real_price = real_price[0]
        
        #Checa por possíveis combinações
        matching_type = "BuyOrder" if order.type_ == OrderType.SELL else "SellOrder"

        #Se eu quero vender, verifico se os clientes internos querem comprar por um preço maior que o do mercado
        target_price = max(order.price, real_price) if OrderType.SELL else min(order.price, real_price)

        matching_data = self.db_cursor.execute(
            f'''select * from {matching_type} 
                where ticker = {order.ticker} and 
                price {'>=' if order.type == OrderType.SELL else '<='} {target_price} and 
                active = 1 order by price desc''').fetchall()
        
        #Os clientes internos tem um preço melhor que o do mercado transaciona o máximo possível
        if (len(matching_data) > 0):
            order.amount = self.trade_with_internal_clients(matching_data, order, matching_type, current_ticker_amount)
    
        if (order.amount > 0):
            #Se o mercado tem um preço melhor que o dos clientes internos restantes
            if ():
                
            else:
                self.db_cursor.execute(f''' insert into {order.type_.value} (ticker, amount, price, expiry_date, client_id) 
                                        values ({order.ticker}, {order.amount}, {order.price}, {order.expiry_date},
                                        (select id from Client where name = {order.client_id}))''')
        self.db.commit()

    def trade_with_internal_clients(self, matching_data: [], order: Order, matching_type: str, current_ticker_amount_: float, owned_stock_id: int):
        amount = 0
        matching_ids = []
        order_amount = order.amount
        current_ticker_amount = current_ticker_amount_
        
        #Pega a quantidade de ações para serem transicionadas
        for matching_order in matching_data:
            amount += matching_order[3]
            matching_ids.append(matching_order[0])
            if (amount >= order_amount):
                break

        #Executa transações
        for i, matching_id in enumerate(matching_ids):
            #Calcula quatidade e preço da transação
            transaction_amount = min(matching_data[i][3], order_amount)
            price = matching_data[i][4]

            #Salva no banco operação da order
            new_id = self.db_cursor.execute(f''' insert into {order.type_.value} (ticker, amount, price, expiry_date, client_id, active)
                                            values ({order.ticker}, {transaction_amount}, {order.price}, {order.expiry_date},
                                            (select id from Client where name = {order.client_id}), 0) returning id''').fetchone()
            
            #Atualiza no banco operação da order correspondente
            if (transaction_amount == matching_data[i][3]):
                self.db_cursor.execute(f'update {matching_type} set active = 0 where id = {matching_id}')
            else:
                self.db_cursor.execute(f'update {matching_type} set amount = {matching_data[i][3] - transaction_amount} where id = {matching_id}')
        
            #Salva a transação, atualiza a quantidade de ações possuidas
            if (order.type_ == OrderType.SELL):
                #Salva o log        
                self.db_cursor.execute(f''' insert into StockTransaction (sell_id, buy_id, amount, price)
                                        values ({new_id}, {matching_id}, {transaction_amount}, {price}''')
                
                #atualiza quantidade de ações
                current_ticker_amount -= transaction_amount
                if (current_ticker_amount_ > 0):
                    self.db_cursor.execute(f''' update OwnedStock set amount={current_ticker_amount}
                                            where id = {owned_stock_id}''')
                
            else:
                self.db_cursor.execute(f''' insert into StockTransaction (sell_id, buy_id, amount, price)
                                        values ({matching_id}, {new_id}, {transaction_amount}, {price}''')

                current_ticker_amount += transaction_amount
                if (current_ticker_amount_ > 0):
                    self.db_cursor.execute(f''' update OwnedStock set amount={current_ticker_amount}
                                            where id = {owned_stock_id}''')
                else:
                    self.db_cursor.execute(f''' insert into OwnedStock (ticker, amount, client_id)
                                            values ({order.ticker}, {current_ticker_amount},
                                            (select id from Client where name = {order.client_id})''')
                    current_ticker_amount_ = current_ticker_amount
            
            order_amount -= transaction_amount
        
        self.db.commit()

        return order_amount

    def update_or_insert_owned_stocks(self, ticker: str, amount: float, client_name: str, update: bool):
        #try update
        self.db_cursor.execute(f''' update OwnedStock set amount={current_ticker_amount}
                                    where id = ()''')
        else:
            self.db_cursor.execute(f''' insert into OwnedStock (ticker, amount, client_id)
                                    values ({order.ticker}, {current_ticker_amount},
                                    (select id from Client where name = {order.client_id})''')
    
    def check_orders_are_expired(self):
        self.db_cursor.execute('update BuyOrder set active = 0 where active = 1 and datetime(expiry_data) < datetime(now())')
        self.db_cursor.execute('update SellOrder set active = 0 where active = 1 and datetime(expiry_data) < datetime(now())')


    def add_client(self, client_id: str):
        self.db_cursor.execute(f'insert into Client(name) values ({client_id})')
        self.db.commit()

    def close(self):
        self.db.close()


if __name__ == "__main__":
    the_stock_market = StockMarket(init_from_file=False)
    # the_stock_market.start()
    the_stock_market.add_stock("")
