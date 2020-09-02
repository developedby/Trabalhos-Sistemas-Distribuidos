import datetime
import json

import Pyro5.api as pyro

from .gui import StockMarketGui
from ..enums import OrderType
from ..order import Order

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
    def __init__(self, init_from_file=True):
        stocks = set()
        buy_orders = []
        sell_orders = []
        if init_from_file:
            self._init_from_file()

        self.gui = StockMarketGui()

    def _init_from_file(self):
        with open('initial_state.json', 'r') as init_file:
            init_json = json.load(init_file)

        for ticker in init_json['stocks']:
            add_stock(ticker)

        for client in init_json['clients']:
            # TODO: Pensar em como armazenar o cliente
            self.add_client()

        for order in init_json['buy_orders']:
            create_order(Order(
                client_id=init_json['client_id'],
                type_=OrderType.BUY,
                ticker=order['ticker'],
                amount=order['amount'],
                price=order['price'],
                expiry_date=datetime.datetime.now() + datetime.timedelta(days=1)
            ))

        for order in init_json['sell_orders']:
            create_order(Order(
                client_id=init_json['client_id'],
                type_=OrderType.SELL,
                ticker=order['ticker'],
                amount=order['amount'],
                price=order['price'],
                expiry_date=datetime.datetime.now() + datetime.timedelta(days=1)
            ))

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
        self.gui.start()
        self.daemon.requestLoop()

    def add_stock(self, ticker: str):
        """Adiciona uma ação na lista de ações existentes"""
        self.stocks.add(ticker)

    def create_order(self, order: Order):
        pass

    def add_client(self, client_id: str):
        pass


if __name__ == "__main__":
    the_stock_market = StockMarket(init_from_file=True)
    the_stock_market.start()
