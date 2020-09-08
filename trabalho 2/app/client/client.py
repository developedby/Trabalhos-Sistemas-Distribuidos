import datetime
import sys
import threading
from typing import Sequence, Mapping

import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook

from ..enums import OrderType, HomebrokerErrorCode
from .gui import ClientGui
from ..order import Order, Transaction


class Client:
    def __init__(self):
        sys.excepthook = pyro_excepthook
        with pyro.locate_ns() as name_server:
            homebroker_uri = name_server.lookup('homebroker')
        self.homebroker = pyro.Proxy(homebroker_uri)

        self.daemon = pyro.Daemon()
        self.uri = self.daemon.register(self)

        # Registra as serializações
        pyro.register_class_to_dict(Order, Order.to_dict)
        pyro.register_dict_to_class('Order', Order.from_dict)
        pyro.register_class_to_dict(Transaction, Transaction.to_dict)
        pyro.register_dict_to_class('Transaction', Transaction.from_dict)

        self.name = None

        self.running = True
        self.gui = ClientGui(self)
        print("Rodando cliente")
        try:
            self.daemon.requestLoop(loopCondition=lambda: self.running)
        finally:
            self.homebroker._pyroClaimOwnership()
            self.homebroker._pyroRelease()

    def create_order(self,
                     order_type: OrderType,
                     ticker: str,
                     amount: float,
                     price: float,
                     expiration_datetime: datetime.datetime) -> HomebrokerErrorCode:
        """Cria uma ordem de compra ou venda para uma ação."""
        order = Order(self.name, order_type, ticker, amount, price, expiration_datetime)
        error_code = self.homebroker.create_order(order)
        error_code = HomebrokerErrorCode(error_code)
        return error_code, order

    def add_quote_alert(self, ticker: str, lower_limit: float, upper_limit: float) -> HomebrokerErrorCode:
        """
        Pede pro servidor avisar caso uma ação passe dos valores limites.

        :param ticker: Nome da ação.
        :param lower_limit: Limite inferior do valor da ação.
        :param upper_limit: Limite superior do valor da ação.
        """
        error_code = self.homebroker.add_quote_alert(
            ticker, lower_limit, upper_limit, self.name)
        error_code = HomebrokerErrorCode(error_code)
        return error_code

    def add_stock_to_quotes(self, ticker: str) -> HomebrokerErrorCode:
        """
        Adiciona uma ação à lista de ações de interesse.
        As ações de interesse são aquelas
        que o usuário quer saber seu valor ao longo do tempo.

        :param ticker: Nome da ação.
        """
        error_code = self.homebroker.add_stock_to_quotes(ticker, self.name)
        error_code = HomebrokerErrorCode(error_code)
        return error_code

    def remove_stock_from_quotes(self, ticker: str) -> HomebrokerErrorCode:
        """
        Remove uma ação da lista de ações de interesse.
        As ações de interesse são aquelas
        que o usuário quer saber seu valor ao longo do tempo.

        :param ticker: Nome da ação.
        """
        error_code = self.homebroker.remove_stock_from_quotes(ticker, self.name)
        error_code = HomebrokerErrorCode(error_code)
        return error_code

    def get_current_quotes(self):
        """Atualiza o valor de todas as ações na lista de interesse."""
        return self.homebroker.get_current_quotes(self.name)

    @pyro.expose
    def notify_limit(self, ticker: str, current_quote: float):
        print(f"Limite: {ticker}, {current_quote}")
        self.gui.notify_limit(ticker, current_quote)

    @pyro.expose
    def notify_order(self,
                     transactions: Sequence[Transaction],
                     active_orders: Sequence[Order],
                     expired_orders: Sequence[str],
                     owned_stock: Mapping[str, float]):
        print("Order:", transactions, active_orders, expired_orders, owned_stock)
        self.gui.notify_order(transactions, active_orders, expired_orders, owned_stock)
