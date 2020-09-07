import datetime
import threading
import time
from typing import Dict

import Pyro5.api as pyro

from .client import Client
from ..enums import OrderType, MarketErrorCode, HomebrokerErrorCode
from ..order import Order


class Homebroker:
    def __init__(self, update_period: int):
        self.update_period = update_period

        # Conecta com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com a bolsa
        market_uri = nameserver.lookup('stockmarket')
        print(market_uri)
        self.market_proxy = pyro.Proxy(market_uri)
        # Proxy duplicado, pra thread que fica pegando atualizações
        self.market_proxy_updates = pyro.Proxy(market_uri)

        self.clients = {}  # Mapping[str, Client]
        self.quotes = {}  # Mapping[str, float]
        self.quotes_lock = threading.Lock()
        self.orders_lock = threading.Lock()
        self.clients_lock = threading.Lock()
        self.alerts_lock = threading.Lock()
        self.alert_limits = {}  # Mapping[str, list[Tuple[str, float, float]]]

        self.thread_updates = threading.Thread(target=self.update_data, daemon=True)

        # Registra no Pyro
        daemon = pyro.Daemon()
        my_uri = daemon.register(self)
        nameserver.register('homebroker', my_uri)

        # Fica respondendo os requests
        print("Rodando Homebroker")
        try:
            daemon.requestLoop()
        except KeyboardInterrupt:
            self.close()

    def update_quotes(self, market_proxy: pyro.Proxy):
        """Atualiza as cotações de todas as ações que o homebroker observa."""
        self.quotes_lock.acquire()
        self.quotes = self.market_proxy.get_quotes(self.quotes.keys())
        quotes_copy = self.quotes.copy()
        self.quotes_lock.release()

        for ticker in quotes_copy:
            #TODO: Atualizar a GUI
            #Se tem alerta para a ação e os valores foram atingidos
            if (ticker in self.alert_limits):
                self.alerts_lock.acquire()
                for alert in self.alert_limits[ticker]:
                    if (alert[1] == quotes_copy[ticker]) or (alert[2] == quotes_copy[ticker]):
                        #Chama a callback do cliente
                        self.clients[alert[0]].proxy.notify_limit(ticker, quotes_copy[ticker])
                        self.alert_limits[ticker].remove(alert)
                self.alerts_lock.release()

    def update_orders(self, market_proxy: pyro.Proxy):
        """Atualiza as ordens de todos os clientes do homebroker."""
        client_names = (client.name for client in self.clients)
        
        self.orders_lock.acquire()
        orders_per_clients = market_proxy.get_orders(client_names)
        transactions_per_client = market_proxy.get_transactions(client_names, self.last_updated)
        #Pode perder alguma transação por race condition
        self.last_updated = datetime.datetime.now()
        
        #Mudanças nas ordens para o cliente
        client_notifications = {client: [[], [] ,[]] for client in self.clients}

        #Descobre ordens que expiraram
        new_orders_set = set()
        new_orders_client = {}
        for client, orders_client in orders_per_clients.items():
            for order in orders_client:
                new_orders_client[order.client_name].append(order)
                new_order = (order.client_name, order.ticker)
                new_orders_set.add(new_order)
        
        clients_orders_set = set()
        self.clients_lock.acquire()
        for client in self.clients:
            for order in client.orders:
                new_order = (order.client_name, order.ticker)
                clients_orders_set.add(new_order)
        self.clients_lock.release()
        
        expired_orders = clients_orders_set.difference(new_orders_set)
        
        for expired_order in expired_orders:
            client_notifications[expired_order[0]][2].append(expired_order[1])

        #Atualiza as ordens ativas
        for client, client_orders in orders_per_clients.items():
            client_notifications[client][1] = client_orders
            self.clients[client].orders = client_orders

        self.orders_lock.release()

        #Pega as transações realizadas no último intervalo
        for client, transactions in transactions_per_client.items():
            for transaction in transactions:
                if transaction.seller_name != 'Market':
                    client_notifications[client][0].append(transaction)
                if transaction.buyer_name != 'Market':
                    client_notifications[client][0].append(transaction)
                    amount = transaction.amount
                    if transaction.ticker in self.clients[client].owned_stocks:
                        amount += self.clients[client].owned_stocks[transaction.ticker]
                    self.clients[client].owned_stocks[transaction.ticker] = amount
            
        #Notifica os clientes
        for client, notification in client_notifications.items():
            self.clients[client].proxy.notify_order(notification[0], notification[1], notification[2])

    def update_data(self):
        """Fica atualizando os dados do homebroker periodicamente."""
        while(True):
            self.sleep(self.update_period)
            self.update_quotes(self.market_proxy_updates)
            self.update_orders(self.market_proxy_updates)

    @pyro.expose
    def add_stock_to_quotes(self, ticker: str, client_name: str) -> HomebrokerErrorCode:
        """Adiciona uma ação à lista de cotações."""
        if (not self.market_proxy.check_ticker_exists(ticker)):
            return HomebrokerErrorCode.UNKNOWN_TICKER
        self.clients[client_name].quotes.append(ticker)
        self.quotes[ticker] = None
        self.update_quotes(self.market_proxy)
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def remove_stock_from_quotes(self, ticker: str, client_name: str) -> HomebrokerErrorCode:
        """Remove uma ação da lista de cotações de um cliente."""
        try:
            self.clients[client_name].quotes.remove(ticker)
        except ValueError:
            return HomebrokerErrorCode.UNKNOWN_TICKER
        has_interest = False
        for client in self.clients:
            if (ticker in client.quotes):
                has_interest = True
                break
        if (not has_interest):
            self.quotes.pop(ticker)
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def get_current_quotes(self, client_name: str) -> Dict[str, float]:
        """Retorna as cotações atuais das ações que o cliente está interessado."""
        self.update_quotes()
        client_quotes = {
            ticker: self.quotes[ticker] for ticker in self.quotes.keys()
            if ticker in self.client[client_name].owned_stocks}
        return client_quotes

    @pyro.expose
    def add_quote_alert(self, ticker: str,
                        lower_limit: float, upper_limit: float,
                        client_name: str) -> HomebrokerErrorCode:
        """
        Adiciona limites de valor pra alertar um cliente sobre uma ação.
        Alerta quando a ação passa do mínimo ou do máximo.
        """
        if not self.market_proxy.check_ticker_exists(ticker):
            return HomebrokerErrorCode.UNKNOWN_TICKER

        self.alerts_lock.acquire()
        self.alert_limits[ticker].append((client_name, lower_limit, upper_limit))
        self.alerts_lock.release()
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def create_order(self, order: Order) -> HomebrokerErrorCode:
        """Cria uma ordem de compra ou de venda."""
        self.orders_lock.acquire()
        error = self.market_proxy.create_order(order)
        if (error != MarketErrorCode.SUCCESS):
            self.orders_lock.release()
            return HomebrokerErrorCode[error.name]

        self.clients[order.client_name].orders.append(order)
        self.orders_lock.release()
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def add_client(self, client_uri: str, client_name: str):
        if client_name == 'Market':
            return HomebrokerErrorCode.FORBIDDEN_NAME
        self.clients_lock.acquire()
        if (client_name in self.clients):
            self.clients[client_name].proxy._proxyRelease()
            self.clients[client_name].proxy = pyro.Proxy(client_uri)
            self.clients_lock.release()
        else:
            self.clients[client_name] = Client(client_uri, client_name)
            self.clients_lock.release()
            self.market_proxy.add_client(client_name)
        return HomebrokerErrorCode.SUCCESS
        

    def close(self):
        for client in self.clients:
            client.proxy._pyroRelease()
