import datetime
from typing import Optional

from .enums import OrderType


class Order:
    """
    Representa uma ordem de compra ou venda.

    :param client_name: Nome do cliente que criou a ordem.
    :param type: Tipo da ordem (compra ou venda).
    :param ticker: Nome da ação.
    :param amount: Quantidade de ações que deseja transacionar.
    :param price: Preço máximo de compra ou preço mínimo de venda.
    :param expiry_date: Data em que a ordem expira.
    """
    def __init__(
        self,
        client_name: str,
        type_: OrderType,
        ticker: str,
        amount:float,
        price: float,
        expiry_date: datetime.datetime,
        active: Optional[bool] = None,
    ):
        self.client_name = client_name
        self.type = type_
        self.ticker = ticker
        self.amount = amount
        self.price = price
        self.expiry_date = expiry_date
        self.active = active if active is not None else not self.is_expired()

    def is_expired(self) -> bool:
        return datetime.datetime.now() >= self.expiry_date


class Transaction:
    def __init__(self,
                 ticker: str,
                 seller_name: str,
                 buyer_name: str,
                 amount: float,
                 price: float,
                 datetime: datetime.datetime):
        self.ticker = ticker
        self.seller_name = seller_name
        self.buyer_name = buyer_name
        self.amount = amount
        self.price = price
        self.datetime = datetime
