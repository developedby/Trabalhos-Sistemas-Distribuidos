"""Classes auxiliares."""
import datetime
from typing import Optional, Dict, Any

from .enums import OrderType

datetime_format = '%Y-%m-%d %H:%M:%S'

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
    def __init__(self,
                 client_name: str,
                 type_: OrderType,
                 ticker: str,
                 amount: float,
                 price: float,
                 expiry_date: datetime.datetime,
                 active: Optional[bool] = None,
                 **kwargs):
        self.client_name = client_name
        self.type = type_
        self.ticker = ticker
        self.amount = amount
        self.price = price
        self.expiry_date = expiry_date
        self.active = (
            active if active is not None
            else not self.is_expired()
        )

    def is_expired(self):
        """Retorna se a ordem expirou ou não."""
        return datetime.datetime.now() >= self.expiry_date

    @staticmethod
    def to_dict(order: 'Order') -> Dict[str, Any]:
        """Serialização para mandar pelo Pyro."""
        global datetime_format
        return {
            '__class__': 'Order',
            'client_name': order.client_name,
            'type': order.type,
            'ticker': order.ticker,
            'amount': order.amount,
            'price': order.price,
            'expiry_date': order.expiry_date.strftime(datetime_format),
            'active': order.active
        }

    @staticmethod
    def from_dict(class_name: str, dict_: Dict[str, Any]) -> 'Order':
        """Desserialização para receber pelo Pyro."""
        global datetime_format
        return Order(
            dict_['client_name'],
            OrderType(dict_['type']),
            dict_['ticker'],
            dict_['amount'],
            dict_['price'],
            datetime.datetime.strptime(dict_['expiry_date'], datetime_format),
            dict_['active']
        )

    def __repr__(self):
        return(
            f"Order("
            f"client_name={self.client_name}, "
            f"type_={self.type}, "
            f"ticker={self.ticker}, "
            f"amount={self.amount}, "
            f"price={self.price}, "
            f"expiry_date={self.expiry_date}, "
            f"active={self.active}"
            ")"
        )

class Transaction:
    """
    Representa uma transação entre dois clientes.
    
    :param ticker: Nome da ação
    :param seller_name: Nome do usuário que vendeu.
    :param buyer_name: Nome do usuário que comprou.
    :param amount: Quantidade que foi transacionada.
    :param price: Preço por unidade com que a ação foi transacionada.
    :param datetime: Data-hora em que ocorreu a transação.
    """
    def __init__(self,
                 ticker: str,
                 seller_name: str,
                 buyer_name: str,
                 amount: float,
                 price: float,
                 datetime: datetime.datetime,
                 **kwargs):
        self.ticker = ticker
        self.seller_name = seller_name
        self.buyer_name = buyer_name
        self.amount = amount
        self.price = price
        self.datetime = datetime

    @staticmethod
    def to_dict(transaction: 'Transaction') -> Dict[str, Any]:
        """Serialização para enviar pelo Pyro."""
        return {
            '__class__': 'Transaction',
            'ticker': transaction.ticker,
            'seller_name': transaction.seller_name,
            'buyer_name': transaction.buyer_name,
            'amount': transaction.amount,
            'price': transaction.price,
            'datetime': transaction.datetime.strftime(datetime_format)
        }

    @staticmethod
    def from_dict(class_name: str, dict_: Dict[str, Any]) -> 'Transaction':
        """Desserialização para receber pelo Pyro."""
        global datetime_format
        return Transaction(
            dict_['ticker'],
            dict_['seller_name'],
            dict_['buyer_name'],
            dict_['amount'],
            dict_['price'],
            datetime.datetime.strptime(dict_['datetime'], datetime_format)
        )