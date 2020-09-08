from contextlib import contextmanager
import datetime
import sys
import threading
import time
from typing import Dict, Callable

import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook

from .client import Client
from ..enums import OrderType, MarketErrorCode, HomebrokerErrorCode
from ..order import Order


class Homebroker:
    def __init__(self, update_period: float):
        self.update_period = update_period
        sys.excepthook = pyro_excepthook

        # Conecta com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com a bolsa
        market_uri = nameserver.lookup('stockmarket')
        print(market_uri)
        self.market = pyro.Proxy(market_uri)
        self.market_lock = threading.Lock()

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
            pass
        finally:
            self.close()

    def close(self):
        for client in self.clients.values():
            client.proxy._pyroClaimOwnership()
            client.proxy._pyroRelease()

    @contextmanager
    def get_market(self):
        """Context manager pra pegar exclusividade no market."""
        self.market_lock.acquire()
        self.market._pyroClaimOwnership()
        try:
            yield
        finally:
            self.market_lock.release()

    def update_quotes(self):
        """Atualiza as cotações de todas as ações que o homebroker observa."""
        self.quotes_lock.acquire()
        # Não pega o proxy pra si porque é sempre uma funcao interna, quem pega é quem chamou
        self.quotes = self.market.get_quotes(self.quotes.keys())
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

    def update_orders(self):
        """Atualiza as ordens de todos os clientes do homebroker."""
        client_names = (client.name for client in self.clients)
        
        self.orders_lock.acquire()
        # Não pega o proxy pra si porque é sempre uma funcao interna, quem pega é quem chamou
        orders_per_clients = self.market.get_orders(client_names)
        transactions_per_client = self.market.get_transactions(client_names, self.last_updated)
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
            with self.get_market():
                self.update_quotes()
            with self.get_market():
                self.update_orders()

    @pyro.expose
    def add_stock_to_quotes(self, ticker: str, client_name: str) -> HomebrokerErrorCode:
        """Adiciona uma ação à lista de cotações."""
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return HomebrokerErrorCode.UNKNOWN_TICKER

        self.clients[client_name].quotes.append(ticker)
        self.quotes[ticker] = None
        with self.get_market():
            self.update_quotes()
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
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return HomebrokerErrorCode.UNKNOWN_TICKER

        self.alerts_lock.acquire()
        self.alert_limits[ticker].append((client_name, lower_limit, upper_limit))
        self.alerts_lock.release()
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def create_order(self, order: Order) -> HomebrokerErrorCode:
        """Cria uma ordem de compra ou de venda."""
        self.orders_lock.acquire()
        with self.get_market():
            error = self.market.create_order(order)
        error = MarketErrorCode(error)
        if (error is not MarketErrorCode.SUCCESS):
            self.orders_lock.release()
            return HomebrokerErrorCode[error.name]

        self.clients[order.client_name].orders.append(order)
        self.orders_lock.release()
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def add_client(self, client_uri: str, client_name: str) -> HomebrokerErrorCode:
        if client_name in ('Market', ''):
            return HomebrokerErrorCode.FORBIDDEN_NAME
        self.clients_lock.acquire()
        if (client_name in self.clients):
            self.clients[client_name].proxy._pyroClaimOwnership()
            self.clients[client_name].proxy._pyroRelease()
            self.clients[client_name].proxy = pyro.Proxy(client_uri)
            self.clients_lock.release()
        else:
            self.clients[client_name] = Client(client_uri, client_name)
            self.clients_lock.release()
            with self.get_market():
                self.market.add_client(client_name)
            print(f"New client: {client_name}")
        return HomebrokerErrorCode.SUCCESS
