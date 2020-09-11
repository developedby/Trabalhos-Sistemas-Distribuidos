from Pyro5.api import Proxy


class Client:
    """Representação de um cliente dentro do servidor."""
    def __init__(self, uri: str, name: str):
        self.uri = uri
        self.proxy = Proxy(self.uri)
        self.name = name
        self.quotes = []  # Tickers
        self.owned_stocks = {}  # Ticker, quantidade
        self.orders = []  # Ticker, quantidade, preço
