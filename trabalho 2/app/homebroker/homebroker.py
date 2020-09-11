"""Servidor do homebroker."""
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
    """
    Servidor do homebroker.

    Recebe pedidos de Client, passando as informações para StockMarket.

    Guarda o que o cliente está interessado,
    como limites de ganho e perda e uma lista de ações de interesse.

    Periodicamente pega atualizações de StockMarket,
    avisando os clientes caso tenha ocorrido algum evento de interesse.
    """
    def __init__(self, update_period: float):
        self.update_period = update_period

        # Para as exceções remotas aparecerem em um formato melhor
        sys.excepthook = pyro_excepthook

        # Conecta com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com a bolsa
        market_uri = nameserver.lookup('stockmarket')
        print(market_uri)
        self.market = pyro.Proxy(market_uri)
        self.market_lock = threading.Lock()

        # Registra as serializações dos objetos para o Pyro
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

        # Registra o objeto no daemon do Pyro e no nameserver
        daemon = pyro.Daemon()
        my_uri = daemon.register(self)
        nameserver.register('homebroker', my_uri)

        # Cria a thread que fica pegando atualizações da bolsa
        self.thread_updates = threading.Thread(target=self.update_data, daemon=True)
        self.thread_updates.start()

        # Fica respondendo os requests dos clientes
        print("Rodando Homebroker")
        try:
            daemon.requestLoop()
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self):
        """Termina o programa. Fecha as conexões."""
        with self.clients_lock:
            for client in self.clients.values():
                client.proxy._pyroClaimOwnership()
                client.proxy._pyroRelease()
        with self.get_market():
            self.market._pyroRelease()

    @contextmanager
    def get_market(self):
        """Context manager pra pegar exclusividade no proxy."""
        self.market_lock.acquire()
        self.market._pyroClaimOwnership()
        try:
            yield
        finally:
            self.market_lock.release()

    def update_data(self):
        """
        Fica atualizando os dados do homebroker periodicamente.
        Envia notificações para os clientes caso ocorra algum evento.
        """
        while(True):
            time.sleep(self.update_period)
            self.update_quotes()
            self.update_orders()

    def update_quotes(self):
        """Atualiza as cotações de todas as ações que o homebroker observa."""

        # Atualiza as cotações
        with self.quotes_lock:
            with self.get_market():
                self.quotes = self.market.get_quotes(self.quotes.keys())
            quotes_copy = self.quotes.copy()

        # Envia os alertas de limite de preço para os clientes, caso haja
        alerts_to_remove = []
        for ticker in quotes_copy:
            # Se tem alerta para a ação
            if ticker in self.alert_limits:
                with self.alerts_lock:
                    for client, limits in self.alert_limits[ticker].items():
                        # Se tem limite minimo e o valor da ação ta mais baixo que o limite
                        # Ou se tem maximo e o valor da ação ta maior
                        if ((limits[0] is not None) and (quotes_copy[ticker] <= limits[0])
                                or ((limits[1] is not None) and (quotes_copy[ticker] >= limits[1]))):
                            # Chama a callback do cliente
                            self.clients[client].proxy._pyroClaimOwnership()
                            self.clients[client].proxy.notify_limit(ticker, quotes_copy[ticker])
                            alerts_to_remove.append((ticker, client))
        for ticker_client in alerts_to_remove:
            self.alert_limits[ticker_client[0]].pop(ticker_client[1])

    def update_orders(self):
        """Atualiza as ordens de todos os clientes do homebroker."""
        # Pega uma copia dos clientes, pra evitar problemas de concorrencia
        with self.clients_lock:
            client_names = self.clients.keys()
            with self.orders_lock:
                with self.get_market():
                    orders_per_client = self.market.get_orders(client_names, active_only=True)
                
                # Notificações que tem que enviar aos clientes
                # {nome do cliente: (transacoes, orderns ativas, ordens expiradas, acoes possuidas)}
                notifications_per_client = {client: [[], [] ,[], {}] for client in self.clients}

                # Pega as ordens que expiraram
                # Separa as ordens novas
                new_orders = set()
                for orders_of_a_client in orders_per_client.values():
                    for order in orders_of_a_client:
                        new_orders.add((order.client_name, order.ticker))
                # Separa as ordens antigas
                old_orders = set()
                for client in self.clients.values():
                    for order in client.orders:
                        old_orders.add((order.client_name, order.ticker))
                # Pega somente as ordens que ficaram inativas
                inactive_orders = old_orders.difference(new_orders)
                # Das recem inativas, pega somente as que expiraram para enviar pro cliente
                for client_name in self.clients.keys():
                    for order in self.clients[client_name].orders:
                        if ((client_name, order.ticker) in inactive_orders
                                and order.is_expired()):
                            notifications_per_client[client_name][2].append(order.ticker)

                # Atualiza as ordens ativas
                for client_name, client_orders in orders_per_client.items():
                    notifications_per_client[client_name][1] = client_orders
                    self.clients[client_name].orders = client_orders

            # Pega as transações realizadas no último intervalo e atualiza as carteira
            with self.get_market():
                transactions_per_client = self.market.get_transactions(
                    client_names, self.last_updated.strftime(self.datetime_format))
            # Warning: Pode perder alguma transação por race condition
            # Caso perca, não vai notificar o cliente, mas o resto ainda funciona
            self.last_updated = datetime.datetime.now()
            for client_name, transactions in transactions_per_client.items():
                if transactions:
                    notifications_per_client[client_name][0] = transactions
                    with self.get_market():
                        self.clients[client_name].owned_stocks = \
                            self.market.get_stock_owned_by_client(client_name)
                notifications_per_client[client_name][3] = self.clients[client_name].owned_stocks

            # Envia as notificações aos clientes
            for client, notification in notifications_per_client.items():
                # Só envia se mudou alguma coisa (transação ou ordem exirou)
                if notification[0] or notification[2]:
                    self.clients[client].proxy._pyroClaimOwnership()
                    self.clients[client].proxy.notify_order(*notification)

    @pyro.expose
    def add_stock_to_quotes(self, ticker: str, client_name: str) -> HomebrokerErrorCode:
        """Adiciona uma ação à lista de cotações de um cliente."""
        print("add_stock_to_quotes", ticker, client_name)
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return HomebrokerErrorCode.UNKNOWN_TICKER

        self.clients[client_name].quotes.append(ticker)
        with self.quotes_lock:
            self.quotes[ticker] = None
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
            with self.quotes_lock:
                self.quotes.pop(ticker)
        return HomebrokerErrorCode.SUCCESS

    @pyro.expose
    def get_current_quotes(self, client_name: str) -> Dict[str, float]:
        """Retorna as cotações atuais das ações que o cliente está interessado."""
        print("get_current_quotes", client_name)
        self.update_quotes()
        with self.quotes_lock:
            client_quotes = {
                ticker: quote for ticker, quote in self.quotes.items()
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
        # Verifica se a ação existe
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return HomebrokerErrorCode.UNKNOWN_TICKER

        # Adiciona o limite
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
        """
        Adiciona um cliente ou atualiza sua conexão com o homebroker.
        
        :param client_uri: URI Pyro do cliente.
        :param client_name: Nome de usuário do cliente.
        """
        # Verifica se o nome é válido
        if client_name in ('Market', ''):
            return HomebrokerErrorCode.FORBIDDEN_NAME

        self.clients_lock.acquire()
        # Se o cliente já existe atualiza o proxy para a nova conexão
        if (client_name in self.clients):
            self.clients[client_name].proxy._pyroClaimOwnership()
            self.clients[client_name].proxy._pyroRelease()
            self.clients[client_name].proxy = pyro.Proxy(client_uri)
            self.clients_lock.release()
        # Caso não exista cria um novo e manda pro mercado
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
