import threading

import Pyro5.api as pyro

from ..enums import OrderType, HomebrokerErrorCode
from .gui import ClientGui
from ..order import Order, Transaction


class Client:
    def __init__(self):
        name_server = pyro.locate_ns()
        homebroker_uri = name_server.lookup('homebroker')
        self.homebroker = pyro.Proxy(homebroker_uri)

        self.daemon = pyro.Daemon()
        self.uri = self.daemon.register(self)

        self.name = None

        self.running = True
        self.gui = ClientGui(self)
        print("Rodando cliente")
        self.daemon.requestLoop(loopCondition=lambda: self.running)

    def create_order(self, order: Order):
        """Cria uma ordem de compra ou venda para uma ação."""
        error_code = self.homebroker.create_order(order)
        if error_code is not HomebrokerErrorCode.SUCCESS:
            # TODO: Mostra um erro
            pass
        # TODO: Mostra na GUI

    def add_quote_alert(self, ticker: str, lower_limit: float, upper_limit: float):
        """
        Pede pro servidor avisar caso uma ação passe dos valores limites.

        :param ticker: Nome da ação.
        :param lower_limit: Limite inferior do valor da ação.
        :param upper_limit: Limite superior do valor da ação.
        """
        error_code = self.homebroker.add_quote_alert(
            ticker, lower_limit, upper_limit, self.name)
        if error_code is not HomebrokerErrorCode.SUCCESS:
            # TODO: Mostra um erro
            pass
        # TODO: Mostra na GUI

    def add_stock_to_quotes(self, ticker: str):
        """
        Adiciona uma ação à lista de ações de interesse.
        As ações de interesse são aquelas
        que o usuário quer saber seu valor ao longo do tempo.

        :param ticker: Nome da ação.
        """
        error_code = self.homebroker.add_stock_to_quotes(ticker, self.name)
        if error_code is not HomebrokerErrorCode.SUCCESS:
            # TODO: Mostra um erro
            pass
        # TODO: Mostra na GUI

    def remove_stock_from_quotes(self, ticker: str):
        """
        Remove uma ação da lista de ações de interesse.
        As ações de interesse são aquelas
        que o usuário quer saber seu valor ao longo do tempo.

        :param ticker: Nome da ação.
        """
        error_code = self.homebroker.remove_stock_from_quotes(ticker, self.name)
        if error_code is not HomebrokerErrorCode.SUCCESS:
            # TODO: Mostra um erro
            pass
        # TODO: Mostra na GUI

    def get_current_quotes(self):
        """Atualiza o valor de todas as ações na lista de interesse."""
        quotes = self.homebroker.get_current_quotes(self.name)
        # TODO: Mostra na GUI

    @pyro.expose
    def notify_limit(self, ticker: str, current_quote: float):
        # TODO: Mostra na GUI e tira o alerta da lista de alertas
        pass

    @pyro.expose
    def notify_order(self,
                     transation: Transaction,
                     active_orders: Sequence[Order],
                     expired_orders: Sequence[str]):
        # TODO: Mostra as transações na gui, atualiza as ordens ativa e mostra as ordens expiradas
        pass