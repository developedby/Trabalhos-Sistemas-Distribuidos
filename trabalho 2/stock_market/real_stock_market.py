import time
import datetime
import json
import collections

import Pyro5.api as pyro

import sys
sys.path.append('..')
from gui import StockMarketGui

from enums import OrderType
from order import Order

import yfinance as yf
import sqlite3

the_stock_market = None

@pyro.expose
class StockMarketPyro:
    def create_order(self, order: Order):
        global the_stock_market
        the_stock_market.create_order(order)

    # def get_quotes(self, tickers: collections.Collection[str]):
    def get_quotes(self, tickers: []):
        global the_stock_market
        quotes = {ticker: float('inf') for ticker in tickers}
        for order in the_stock_market.sell_orders:
            if order.ticker in tickers:
                quotes[order.ticker] = min(order.price, quotes[order.ticker])
        return quotes

    # def get_orders(self, client_ids: Collection[str]):
    def get_orders(self, client_ids:[]):
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

        self.gui = StockMarketGui()

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
        self.db_cursor.execute('delete from BuyOrder')
        self.db_cursor.execute('delete from Client  ')
        self.db_cursor.execute('delete from OwnedStock')
        self.db_cursor.execute('delete from SellOrder')
        self.db_cursor.execute('delete from StockTransaction')
        self.add_client("Market")
        # self.gui.start()
        # self.daemon.requestLoop()

    def check_ticker(self, ticker: str):
        """Verifica se ação existe na api"""
        dumb_data = yf.download(ticker, period="1d")
        return len(dumb_data) > 0

    def get_quotes(self, stocks):
        data = yf.download(stocks, period="1d")["Adj Close"]
        return data.values
        #Mostrar para o usuário

    def create_order(self, order: Order):
        '''Cria ordem de compra ou venda, se possível executa a transação'''

        #Verifica se a ordem é valida
        if (order.is_expired()):
            print("Order is expired")
            #TODO: Return code
            return 

        #Verifica se cliente existe
        client_id = self.db_cursor.execute(
            f'''select id from Client 
                    where name = '{order.client_id}' ''').fetchone()
        if not client_id:
            print("Client not found")
            #Avisa usuário?
            #TODO: Return code
            return 
        client_id = client_id[0]
        
        #Verifica o estado das ordens
        self.check_orders_are_expired()

        #Checa se o cliente tem as ações que ele quer vender
        data = self.db_cursor.execute(
            f'''select os.* from Client as c 
                inner join OwnedStock as os on c.id = os.client_id 
                    where os.ticker = '{order.ticker}' and 
                    c.id = {client_id} ''').fetchone()
        current_ticker_amount = data[2] if (data) else 0
        if ((order.type == OrderType.SELL) and ((data is None) or current_ticker_amount < order.amount)):
            print("Client doesn't have enough tickers to sell")
            #Avisa usuário?
            #TODO: Return code
            return

        #Pega o valor do mercado
        real_price = self.get_quotes([order.ticker])
        if (len(real_price) == 0):
            print("Ticker not found in the market")
            #Avisa usuário?
            #TODO: Return code
            return
        real_price = real_price[0]
        
        #Checa por possíveis combinações
        matching_type = "BuyOrder" if order.type == OrderType.SELL else "SellOrder"

        #Se eu quero vender, verifico se os clientes internos querem comprar por um preço maior que o do mercado (prioriza quem está vendendo)
        target_price = max(order.price, real_price)

        matching_data = self.db_cursor.execute(
            f'''select * from {matching_type} 
                where ticker = '{order.ticker}' and 
                price {'>=' if order.type == OrderType.SELL else '<='} {target_price} and 
                active = 1 order by price {'desc' if order.type == OrderType.SELL else 'asc'}''').fetchall()
        
        #Se os clientes internos tem um preço melhor que o do mercado transaciona o máximo possível
        if (len(matching_data) > 0):
            print("Doing transaction with internal client")
            order.amount = self.trade_with_internal_clients(matching_data, order, client_id, matching_type)
        if (order.amount > 0):
            #Se o mercado tem um preço melhor que o dos clientes internos restantes
            if ((order.type == OrderType.SELL and order.price <= real_price) or (order.type == OrderType.BUY and order.price > real_price)):
                print("Doing transaction with market")
                self.trade_with_market(order, client_id, real_price, matching_type)
            else:
                print("Creating order")
                self.db_cursor.execute(
                    f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active) 
                            values ('{order.ticker}', {order.amount}, {order.price}, '{order.expiry_date}', 
                            {client_id}, 1)''')
        self.db.commit()

    def trade_with_internal_clients(self, matching_data: [], order: Order, client_id: int, matching_type: str):
        '''Executa uma ou mais transações com clientes internos'''        
        
        #Pega a quantidade de ações para serem transicionadas
        amount = 0
        matching_ids = []
        order_amount = order.amount
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

            #Salva a ordem no banco
            self.db_cursor.execute(
                f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {transaction_amount}, {order.price}, '{order.expiry_date}', 
                        {client_id}, 0)''')

            new_id = self.db_cursor.lastrowid
            
            #Atualiza no banco a ordem correspondente
            if (transaction_amount == matching_data[i][3]):
                self.db_cursor.execute(
                    f'''update {matching_type} set active = 0 
                            where id = {matching_id}''')
            else:
                self.db_cursor.execute(
                    f'''update {matching_type} set amount = {matching_data[i][3] - transaction_amount} 
                            where id = {matching_id}''')
        
            #Salva a transação, atualiza a quantidade de ações possuidas
            if (order.type == OrderType.SELL):
                #Salva o log        
                self.db_cursor.execute(
                    f'''insert into StockTransaction (sell_id, buy_id, amount, price)
                            values ({new_id}, {matching_id}, {transaction_amount}, {price})''')
                
                #atualiza quantidade de ações
                self.update_or_insert_owned_stocks(order.ticker, -transaction_amount, client_id)
                self.update_or_insert_owned_stocks(order.ticker, transaction_amount, matching_data[i][1])
                
            else:
                self.db_cursor.execute(
                    f'''insert into StockTransaction (sell_id, buy_id, amount, price)
                            values ({matching_id}, {new_id}, {transaction_amount}, {price})''')

                #atualiza quantidade de ações
                self.update_or_insert_owned_stocks(order.ticker, transaction_amount, client_id)
                self.update_or_insert_owned_stocks(order.ticker, -transaction_amount, matching_data[i][1])
            
            order_amount -= transaction_amount
        
        self.db.commit()

        return order_amount

    def trade_with_market(self, order: Order, client_id: int, real_price: float, matching_type: str, order_id: int = None):
        '''Executa uma transação com o mercado, toda a ordem será executada'''
        #Salva a ordem no banco
        if order_id is None:    
            self.db_cursor.execute(
                f'''insert into {order.type.value} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {order.amount}, {order.price}, '{order.expiry_date}',
                        {client_id}, 0)''').fetchone()
            own_order_id = self.db_cursor.lastrowid
        #Atualiza a ordem no banco
        else:
            self.db_cursor.execute(
                    f'''update {order.type.value} set active = 0 
                            where id = {order_id}''')
            own_order_id = order_id

        self.db_cursor.execute(
            f'''insert into {matching_type} (ticker, amount, price, expiry_date, client_id, active)
                        values ('{order.ticker}', {order.amount}, {real_price}, '{order.expiry_date}',
                        (select id from Client where name = 'Market'), 0)''').fetchone()
        new_matching_id = self.db_cursor.lastrowid

        if (order.type == OrderType.SELL):
            #Salva o log        
            self.db_cursor.execute(
                f'''insert into StockTransaction (sell_id, buy_id, amount, price)
                        values ({own_order_id}, {new_matching_id}, {order.amount}, {real_price})''')
            
            #atualiza quantidade de ações
            self.update_or_insert_owned_stocks(order.ticker, -order.amount, client_id)            
        else:
            self.db_cursor.execute(
                f'''insert into StockTransaction (sell_id, buy_id, amount, price)
                    values ({new_matching_id}, {own_order_id}, {order.amount}, {real_price})''')

            #atualiza quantidade de ações
            self.update_or_insert_owned_stocks(order.ticker, order.amount, client_id)

        self.db.commit()

    def update_or_insert_owned_stocks(self, ticker: str, amount: float, client_id: int):
        '''Atualizar ou insere uma quantidade de ações para um cliente'''

        #Tenta atualizar
        id_owned_stock = self.db_cursor.execute(
            f'''select id from OwnedStock 
                    where ticker = '{ticker}' and
                    client_id = {client_id}''').fetchone()
        if id_owned_stock:
            id_owned_stock = id_owned_stock[0]
            self.db_cursor.execute(
                f'''update OwnedStock set amount=amount + {amount}
                        where id = {id_owned_stock}''')
        
        #Se não tiver, adiciona a ação
        if not id_owned_stock:
            self.db_cursor.execute(
                f'''insert into OwnedStock (ticker, amount, client_id)
                        values ('{ticker}', {amount}, {client_id})''')
        
        self.db.commit()
    
    def check_orders_are_expired(self):
        '''Verifica se as ordens de compra e venda estão expiradas, se sim atualiza o estado'''

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
        '''Tenta executar todas as transações que estão em espera com o merdado'''

        active_buy_orders = self.db_cursor.execute(
            ''' select * from BuyOrder 
                    where active = 1 ''').fetchall()
        
        active_sell_orders = self.db_cursor.execute(
            ''' select * from SellOrder 
                    where active = 1 ''').fetchall()
        
        self.try_trade_with_market(OrderType.BUY, active_buy_orders)
        self.try_trade_with_market(OrderType.SELL, active_sell_orders)
    
    def try_trade_with_market(self, order_type: OrderType, data: []):
        for order_data in data:
            ticker = order_data[2]
            real_price = self.get_quotes([ticker])
            order_id = order_data[0]
            if (len(real_price) > 0):
                real_price = real_price[0]
                order_price = order_data[4]
                client_id = order_data[1]
                order = Order("dumb_name", order_type, ticker, order_data[3], order_price, datetime.datetime.strptime(order_data[5], "%Y-%m-%d %H:%M:%S"))

                #Se tiver um preço adequado, executa a transação
                if ((order_type == OrderType.BUY) and (real_price < order_price)):
                    self.trade_with_market(order, client_id, real_price, "SellOrder", order_id)
                elif ((order_type == OrderType.SELL) and (real_price > order_price)):
                    self.trade_with_market(order, client_id, real_price, "BuyOrder", order_id)
            #A ação não existe mais no mercado
            else:
                self.db_cursor.execute(
                    f''' update {order_type.value} set active = 0 
                        where id = {order_id}''')


    def add_client(self, client_name: str):
        '''Insere um novo cliente no sistema'''

        #Verifica se cliente já existe
        data = self.db_cursor.execute(
            f'''select * from Client 
                    where name = '{client_name}' ''').fetchone()
        if data:
            #Avisa usuário?
            #TODO: Return code
            return
        
        #Adiciona cliente
        self.db_cursor.execute(
            f'''insert into Client(name) 
                    values ('{client_name}')''')
        self.db.commit()

    def close(self):
        self.db.close()


if __name__ == "__main__":
    the_stock_market = StockMarket()
    the_stock_market.start()
    print("\n\nteste adicionar cliente")
    the_stock_market.add_client("Teste")
    the_stock_market.add_client("Teste")
    the_stock_market.add_client("Teste2")

    print("\n\nverificar ação que não existe")
    print(the_stock_market.check_ticker("blablabla"))
    print(the_stock_market.get_quotes(["blablabla"]))
    
    print("\n\nverificar ação que existe")
    print(the_stock_market.check_ticker("ABEV3.SA"))
    print(the_stock_market.get_quotes(["ABEV3.SA"]))
    
    print("\n\nTestando criar uma ordem velha")
    order = Order("blalblaaksd", OrderType.SELL, 'blablabla', 1000, 10.0, datetime.datetime.strptime("21/11/06 16:30", "%d/%m/%y %H:%M"))
    the_stock_market.create_order(order)
    
    print("\n\nTestando criar uma ordem com um cliente invalido")
    order.expiry_date = datetime.datetime.strptime("2021-11-21 16:30:00", "%Y-%m-%d %H:%M:%S")
    the_stock_market.create_order(order)
    
    print("\n\nTestando criar uma ordem com uma ação incorreta")
    order.type = OrderType.BUY
    order.client_id = "Teste"
    the_stock_market.create_order(order)
    
    print("\n\nTestando criar uma ordem de venda com uma ação que o cliente não tem")
    order.type = OrderType.SELL
    order.ticker = "ITSA4.SA"
    the_stock_market.create_order(order)

    print("\n\nTestando criar uma ordem de compra do mercado")
    order.ticker = "ABEV3.SA"
    order.type = OrderType.BUY
    order.price = 100.0
    the_stock_market.create_order(order)

    print("\n\nTestando colocar uma ordem de venda na espera para vencer em pouco tempo")
    order.expiry_date = datetime.datetime.now() + datetime.timedelta(seconds=2)
    order.expiry_date = datetime.datetime.strptime(order.expiry_date.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
    print(order.expiry_date)
    order.type = OrderType.SELL
    order.price = 20.0
    order.client_id = "Teste"
    order.amount = 900
    the_stock_market.create_order(order)

    time.sleep(3)
    print("\n\nTestando criar uma ordem de compra com cliente interno mas vai ser com mercado pq está expirado")
    order.expiry_date = datetime.datetime.strptime("21/11/21 16:30", "%d/%m/%y %H:%M")
    order.type = OrderType.BUY
    order.price = 20.0
    order.client_id = "Teste2"
    the_stock_market.create_order(order)

    print("\n\nRecriando ordem de venda")
    order.type = OrderType.SELL
    order.price = 20.0
    order.client_id = "Teste"
    order.amount = 900
    the_stock_market.create_order(order)

    print("\n\nTestando criar uma ordem de compra com cliente interno")
    order.type = OrderType.BUY
    order.price = 20.0
    order.amount = 800
    order.client_id = "Teste2"
    the_stock_market.create_order(order)

    print("\n\nTestando verificar se o restante da venda vai ser executado pelo banco")
    the_stock_market.try_execute_active_orders()

    print("\n\nTestando criar uma ordem de compra com cliente interno para ser terminada com o mercado")
    order.type = OrderType.BUY
    order.price = 20.0
    order.amount = 800
    order.client_id = "Teste2"
    the_stock_market.create_order(order)



    # the_stock_market.start()
