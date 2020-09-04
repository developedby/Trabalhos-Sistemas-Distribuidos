import datetime
import threading
import time

import Pyro5.api as pyro

from .client import Client
from ..enums import OrderType, MarketErrorCode
from ..order import Order


class Homebroker:
    def __init__(self, update_period: int):
        self.update_period = update_period

        # Conecta com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com a bolsa
        market_uri = nameserver.lookup('stockmarket')
        print(market_uri)
        self.market = pyro.Proxy(market_uri)
        # Proxy duplicado, pra thread que fica pegando atualizações
        self.market_updates = pyro.Proxy(market_uri)

        self.clients = {}  # Mapping[str, Client]
        self.quotes = {}  # Mapping[str, float]
        self.quotes_lock = threading.Lock()
        self.alert_limits = {}  # Mapping[str, Tuple[float, float]]

        self.thread_updates = threading.Thread(target=self.update_data, daemon=True)

        # Registra no Pyro
        daemon = pyro.Daemon()
        my_uri = daemon.register(self)
        nameserver.register('homebroker', my_uri)

        # Fica respondendo os requests
        print("Rodando Homebroker")
        daemon.requestLoop()

    def update_quotes(self, market_proxy: pyro.Proxy):
        """Atualiza as cotações de todas as ações que o homebroker observa."""
        self.quotes_lock.acquire()
        self.quotes = market_proxy.get_quotes(self.quotes.keys())
        self.quotes_lock.release()
        # Processa os valores

    def update_orders(self, market_proxy: pyro.Proxy):
        """Atualiza as ordens de todos os clientes do homebroker."""
        client_names = (client.uri for client in self.clients)
        orders = market_proxy.get_orders(client_names)
        transactions = market_proxy.get_transactions(client_names, self.last_updated)
        # Pode perder alguma transação por race condition
        self.last_updated = datetime.datetime.now()
        # Processa as ordens
        # TODO: Pensar em como o homebroker vai determinar quando as transações foram completas

    def update_data(self):
        """Fica atualizando os dados do homebroker periodicamente."""
        while(True):
            self.sleep(self.update_period)
            self.update_quotes(self.market_updates)
            self.update_orders(self.market_updates)

    @pyro.expose
    def add_stock_to_quotes(self, ticker: str, client_uri: str):
        """Adiciona uma ação à lista de cotações."""
        self.quotes[ticker] = None
        self.update_quotes

    @pyro.expose
    def remove_stock_from_quotes(self, ticker: str, client_uri: str):
        pass

    @pyro.expose
    def get_current_quotes(self, client_uri: str):
        self.update_quotes()
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
