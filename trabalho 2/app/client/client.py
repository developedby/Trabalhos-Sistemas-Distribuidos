import threading

import Pyro5.api as pyro

from ..enums import OrderType
from .gui import ClientGui
from ..order import Order


class Client:
    def __init__(self):
        name_server = pyro.locate_ns()
        homebroker_uri = name_server.lookup('homebroker')
        self.homebroker = pyro.Proxy(homebroker_uri)

        self.daemon = pyro.Daemon()
        self.uri = self.daemon.register(self)

        self.running = True
        self.gui = ClientGui(self)
        self.daemon.requestLoop(loopCondition=lambda: self.running)

    def create_order(self, order: Order):
        """Cria uma ordem de compra ou venda para uma ação."""
        self.homebroker.create_order(order)

    def add_quote_alert(self, ticker: str, lower_limit: float, upper_limit: float):
        """
        Pede pro servidor avisar caso uma ação passe dos valores limites.

        :param ticker: Nome da ação.
        :param lower_limit: Limite inferior do valor da ação.
        :param upper_limit: Limite superior do valor da ação.
        """
        pass

    def add_stock_to_quotes(self, ticker: str):
        """
        Adiciona uma ação à lista de ações de interesse.
        As ações de interesse são aquelas
        que o usuário quer saber seu valor ao longo do tempo.

        :param ticker: Nome da ação.
        """
        # Pergunta preco pro servidor
        # Adiciono na GUI
        pass

    def remove_stock_from_quotes(self, ticker: str):
        """
        Remove uma ação da lista de ações de interesse.
        As ações de interesse são aquelas
        que o usuário quer saber seu valor ao longo do tempo.

        :param ticker: Nome da ação.
        """
        pass

    def get_current_quotes(self):
        """Atualiza o valor de todas as ações na lista de interesse."""
        pass

    @pyro.expose
    def notify_limit(self):
        pass

    @pyro.expose
    def notify_quote(self):
        pass

    @pyro.expose
    def notify_order(self):
        pass
