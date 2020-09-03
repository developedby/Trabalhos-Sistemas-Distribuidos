import datetime

from enums import OrderType


class Order:
    """
    Representa uma ordem de compra ou venda.

    :param client_id: Id do cliente que criou a ordem.
    :param type: Tipo da ordem (compra ou venda).
    :param ticker: Nome da ação.
    :param amount: Quantidade de ações que deseja transacionar.
    :param price: Preço máximo de compra ou preço mínimo de venda.
    :param expiry_date: Data em que a ordem expira.
    """
    def __init__(
        self,
        client_id: str,
        type_: OrderType,
        ticker: str,
        amount:float,
        price: float,
        expiry_date: datetime.datetime
    ):
        self.client_id = client_id
        self.type = type_
        self.ticker = ticker
        self.amount = amount
        self.price = price
        self.expiry_date = expiry_date

    def is_expired(self):
        return datetime.datetime.now() >= self.expiry_date
