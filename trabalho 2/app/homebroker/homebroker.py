import threading
import time

import Pyro5.api as pyro

from .client import Client
from ..enums import OrderType


the_homebroker = None


@pyro.expose
class ClientConnector:
    def add_stock_to_quotes(self, ticker: str, client_uri: str):
        global the_homebroker
        pass

    def remove_stock_from_quotes(self, ticker: str, client_uri: str):
        global the_homebroker
        pass

    def get_current_quotes(self, client_uri: str):
        global the_homebroker
        pass

    def add_quote_alert(self, ticker: str,
                        lower_limit: float, upper_limit: float,
                        client_uri: str):
        global the_homebroker
        pass

    def create_order(self, order: Order):
        global the_homebroker
        the_homebroker.create_order(order)

    def add_client(self, client_uri: str):
        global the_homebroker
        the_homebroker.clients[client_uri] = Client(client_uri)


class Homebroker:
    def __init__(self):
        self.clients = {}
        self.stocks = {}  # ticker: preço
        self.limits_for_alert = {}  # ticker: lista de limites de alerta

        self._init_pyro()
        pass

    def _init_pyro(self):
        global the_homebroker
        the_homebroker = self
        # Registra como objeto Pyro
        self.daemon = pyro.Daemon()
        uri_client_connector = self.daemon.register(ClientConnector)

        # Registra o nome no nameserver
        name_server = pyro.locate_ns()
        name_server.register('homebroker', uri_client_connector)

        # Cria o proxy da bolsa
        market_uri = name_server.lookup('stockmarket')
        self.market = pyro.Proxy(market_uri)

    def start(self):
        self.daemon.requestLoop()

    def create_order(self, order: Order):
        self.market.create_order(order)

    def get_quotes_from_market(self):
        quotes = self.market.get_quotes(self.stocks.keys())
        # Processa os valores

    def check_orders(self):
        client_ids = [client.uri for client in self.clients]
        orders = self.market.get_orders(client_ids)
        # Processa as ordens

    def get_stock_list(self):
        stocks = self.market.get_stock_list()


if __name__ == "__main__":
    print("Starting server")
    the_homebroker = Homebroker()
    the_homebroker.start()
