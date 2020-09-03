import threading

import Pyro5.api as pyro

from ..enums import OrderType
from .gui import ClientGui
from ..order import Order

the_client = None

@pyro.expose
class ClientCallback:
    def notify_limit(self):
        global the_client
        pass

    def notify_quote(self):
        global the_client
        pass


class Client:
    def __init__(self):
        self.gui = ClientGui(self)
        self._init_pyro()

    def _init_pyro(self):
        global the_client
        the_client = self
        self.daemon = pyro.Daemon()
        self.uri = self.daemon.register(ClientCallback)

        name_server = pyro.locate_ns()
        homebroker_uri = name_server.lookup('homebroker')
        self.homebroker = pyro.Proxy(homebroker_uri)

    def start(self):
        self.gui.start()
        self.daemon.requestLoop()

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


if __name__ == "__main__":
    print("Starting client")
    the_client = Client()
    the_client.start()
