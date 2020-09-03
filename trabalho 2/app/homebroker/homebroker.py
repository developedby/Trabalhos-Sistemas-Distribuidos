import threading
import time

import Pyro5.api as pyro

from .client import Client
from ..enums import OrderType
from ..order import Order


class Homebroker:
    def __init__(self):
        # Conecta com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com a bolsa
        market_uri = nameserver.lookup('stockmarket')
        print(market_uri)
        self.market = pyro.Proxy(market_uri)

        self.clients = {}
        self.stocks = {}  # ticker: preço
        self.alert_limits = {}  # ticker: lista de limites de alerta

        # Registra no Pyro
        daemon = pyro.Daemon()
        my_uri = daemon.register(self)
        nameserver.register('homebroker', my_uri)

        # Fica respondendo os requests
        print("Rodando Homebroker")
        daemon.requestLoop()

    def get_quotes_from_market(self):
        quotes = self.market.get_quotes(self.stocks.keys())
        # Processa os valores

    def check_orders(self):
        client_ids = [client.uri for client in self.clients]
        orders = self.market.get_orders(client_ids)
        # Processa as ordens

    @pyro.expose
    def add_stock_to_quotes(self, ticker: str, client_uri: str):
        pass

    @pyro.expose
    def remove_stock_from_quotes(self, ticker: str, client_uri: str):
        pass

    @pyro.expose
    def get_current_quotes(self, client_uri: str):
        self.get_quotes_from_market()
        # Filtra so as do cliente
        pass

    @pyro.expose
    def add_quote_alert(self, ticker: str,
                        lower_limit: float, upper_limit: float,
                        client_uri: str):
        pass

    @pyro.expose
    def create_order(self, order: Order):
        self.market.create_order(order)

    @pyro.expose
    def add_client(self, client_uri: str):
        self.clients[client_uri] = Client(client_uri)
