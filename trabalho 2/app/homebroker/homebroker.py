from contextlib import contextmanager
import datetime
import sys
import threading
import time
from typing import Dict, Callable, List, Tuple

import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook

from .client import Client
from ..enums import OrderType, MarketErrorCode, HomebrokerErrorCode
from ..order import Order, Transaction


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

        # Registra as serializações
        pyro.register_class_to_dict(Order, Order.to_dict)
        pyro.register_dict_to_class('Order', Order.from_dict)
        pyro.register_class_to_dict(Transaction, Transaction.to_dict)
        pyro.register_dict_to_class('Transaction', Transaction.from_dict)

        self.datetime_format = "%Y-%m-%d %H:%M:%S"
        self.clients = {}  # Dict[str, Client]
        self.quotes = {}  # Dict[str, float]
        self.quotes_lock = threading.Lock()
        self.orders_lock = threading.Lock()
        self.clients_lock = threading.Lock()
        self.alerts_lock = threading.Lock()
        self.alert_limits = {}  # Dict[str, Dict[str, Tuple[float, float]]]
        self.last_updated = datetime.datetime.now()

        # Registra no Pyro
        daemon = pyro.Daemon()
        my_uri = daemon.register(self)
        nameserver.register('homebroker', my_uri)

        self.thread_updates = threading.Thread(target=self.update_data, daemon=True)
        self.thread_updates.start()

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

        with self.quotes_lock:
            # Não pega o proxy pra si porque é sempre uma funcao interna, quem pega é quem chamou
            self.quotes = self.market.get_quotes(self.quotes.keys())
            quotes_copy = self.quotes.copy()

        for ticker in quotes_copy:
            # Se tem alerta para a ação e os valores foram atingidos
            if ticker in self.alert_limits:
                with self.alerts_lock:
                    for client, limits in self.alert_limits[ticker].items():
                        # Se tem limite minimo e o valor da acao ta mais baixo que o limite
                        # Ou se tem maximo e o valor da acao ta maior
                        if ((limits[0] is not None) and (quotes_copy[ticker] <= limits[0])
                                or ((limits[1] is not None) and (quotes_copy[ticker] >= limits[1]))):
                            # Chama a callback do cliente
                            self.clients[client].proxy._pyroClaimOwnership()
                            self.clients[client].proxy.notify_limit(ticker, quotes_copy[ticker])
                            self.alert_limits[ticker].pop(client)

    def update_orders(self):
        """Atualiza as ordens de todos os clientes do homebroker."""
        client_names = self.clients.keys()
        #print(client_names)
        with self.orders_lock:
            # Não pega o proxy pra si porque é sempre uma funcao interna, quem pega é quem chamou
            orders_per_clients = self.market.get_orders(client_names, active_only=True)
            transactions_per_client = self.market.get_transactions(
                client_names, self.last_updated.strftime(self.datetime_format))
            # Pode perder alguma transação por race condition
            self.last_updated = datetime.datetime.now()
            
            #Mudanças nas ordens para o cliente
            # {nome do cliente: (transacoes, orderns ativas, ordens expiradas, acoes possuidas)}
            client_notifications = {client: [[], [] ,[], {}] for client in self.clients}

            # Descobre ordens que expiraram
            new_orders_set = set()
            new_orders_client = {}
            for client, orders_client in orders_per_clients.items():
                for order in orders_client:
                    if order.client_name not in new_orders_client:
                        new_orders_client[order.client_name] = [order]
                    else:
                        new_orders_client[order.client_name].append(order)
                    new_orders_set.add((order.client_name, order.ticker))
            
            clients_orders_set = set()
            with self.clients_lock:
                for client in self.clients:
                    for order in self.clients[client].orders:
                        clients_orders_set.add((order.client_name, order.ticker))
            
            inactive_orders = clients_orders_set.difference(new_orders_set)
            for client in self.clients:
                for order in self.clients[client].orders:
                    if (client, order.ticker) in inactive_orders and order.is_expired():
                        client_notifications[client][2].append(order.ticker)

            # Atualiza as ordens ativas
            for client, client_orders in orders_per_clients.items():
                client_notifications[client][1] = client_orders
                self.clients[client].orders = client_orders

        # Pega as transações realizadas no último intervalo
        for client, transactions in transactions_per_client.items():
            for transaction in transactions:
                if transaction.seller_name != 'Market':
                    client_notifications[client][0].append(transaction)
                elif transaction.buyer_name != 'Market':
                    client_notifications[client][0].append(transaction)
            if transactions:
                self.clients[client].owned_stocks = self.market.get_stock_owned_by_client(client)
            client_notifications[client][3] = self.clients[client].owned_stocks

        # Notifica os clientes
        for client, notification in client_notifications.items():
            # Se realizou alguma transação ou expirou alguma ordem (se mudou algo)
            if notification[0] or notification[2]:
                self.clients[client].proxy._pyroClaimOwnership()
                self.clients[client].proxy.notify_order(*notification)

    def update_data(self):
        """Fica atualizando os dados do homebroker periodicamente."""
        while(True):
            time.sleep(self.update_period)
            print('Atualizando infos')
            with self.get_market():
                self.update_quotes()
            with self.get_market():
                self.update_orders()

    @pyro.expose
    def add_stock_to_quotes(self, ticker: str, client_name: str) -> HomebrokerErrorCode:
        """Adiciona uma ação à lista de cotações."""
        print("add_stock_to_quotes", ticker, client_name)
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return HomebrokerErrorCode.UNKNOWN_TICKER

        self.clients[client_name].quotes.add(ticker)
        self.quotes[ticker] = None
        with self.get_market():
            self.update_quotes()
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def remove_stock_from_quotes(self, ticker: str, client_name: str) -> HomebrokerErrorCode:
        """Remove uma ação da lista de cotações de um cliente."""
        print("remove_stock_from_quotes", ticker, client_name)
        try:
            self.clients[client_name].quotes.remove(ticker)
        except ValueError:
            return HomebrokerErrorCode.UNKNOWN_TICKER
        has_interest = False
        for client in self.clients:
            if ticker in self.clients[client].quotes:
                has_interest = True
                break
        if not has_interest:
            self.quotes.pop(ticker)
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def get_current_quotes(self, client_name: str) -> Dict[str, float]:
        """Retorna as cotações atuais das ações que o cliente está interessado."""
        print("get_current_quotes", client_name)
        with self.get_market():
            self.update_quotes()
        client_quotes = {
            ticker: self.quotes[ticker] for ticker in self.quotes
            if ticker in self.clients[client_name].quotes
        }
        return client_quotes

    @pyro.expose
    def add_quote_alert(self, ticker: str,
                        lower_limit: float, upper_limit: float,
                        client_name: str) -> HomebrokerErrorCode:
        """
        Adiciona limites de valor pra alertar um cliente sobre uma ação.
        Alerta quando a ação passa do mínimo ou do máximo.
        """
        print('add_quote_alert', ticker, lower_limit, upper_limit, client_name)
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return HomebrokerErrorCode.UNKNOWN_TICKER

        with self.alerts_lock:
            if ticker not in self.alert_limits:
                self.alert_limits[ticker] = {client_name: (lower_limit, upper_limit)}
            else:
                self.alert_limits[ticker][client_name] = (lower_limit, upper_limit)
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def create_order(self, order: Order) -> HomebrokerErrorCode:
        """Cria uma ordem de compra ou de venda."""
        print('Create order', order)
        with self.orders_lock:
            with self.get_market():
                error = self.market.create_order(order)
            error = MarketErrorCode(error)
            if error is not MarketErrorCode.SUCCESS:
                return HomebrokerErrorCode[error.name]

            self.clients[order.client_name].orders.append(order)

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
            print(f"Novo cliente: {client_name}")
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def get_client_status(
        self, client_name: str) -> Tuple[Dict[str, float],
                                         List[Order],
                                         Dict[str, float],
                                         Dict[str, Tuple[float, float]]]:
        """Retorna o estado atual do cliente. Cotações, Ordens, carteira e alertas."""
        with self.get_market():
            quotes = self.market.get_quotes(self.clients[client_name].quotes)
            orders = self.market.get_orders([client_name], active_only=True)[client_name]
            owned_stock = self.market.get_stock_owned_by_client(client_name)
        alerts = {}
        for ticker in self.alert_limits:
            if client_name in self.alert_limits[ticker]:
                alerts[ticker] = self.alert_limits[ticker][client_name]
        return quotes, orders, owned_stock, alerts
