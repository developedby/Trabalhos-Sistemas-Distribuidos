"""Enums usados pelos 3 módulos."""
from enum import Enum, auto

class OrderType(Enum):
    """Representa os tipos de ordem que existem (comrpa e venda)."""
    BUY = "BuyOrder"
    SELL = "SellOrder"

    def get_matching(self) -> 'OrderType':
        """Retorna o tipo contrario de si."""
        if self is OrderType.BUY:
            return OrderType.SELL
        else:
            return OrderType.BUY

class MarketErrorCode(Enum):
    """Códigos de erro que o mercado retorna."""
    SUCCESS = auto()
    CLIENT_ALREADY_EXISTS = auto()
    UNKNOWN_CLIENT = auto()
    EXPIRED_ORDER = auto()
    NOT_ENOUGH_STOCK = auto()
    UNKNOWN_TICKER = auto()

class HomebrokerErrorCode(Enum):
    """Códigos de erro que o homebroker retorna."""
    SUCCESS = auto()
    CLIENT_ALREADY_EXISTS = auto()
    UNKNOWN_CLIENT = auto()
    EXPIRED_ORDER = auto()
    NOT_ENOUGH_STOCK = auto()
    UNKNOWN_TICKER = auto()
    INVALID_MESSAGE = auto()
    FORBIDDEN_NAME = auto()

    def __str__(self):
        return str(self.value)

class TransactionState(Enum):
    """Possíveis estados de uma transação"""
    ACTIVETED = auto()
    DESACTIVETED = auto()
    PENDING = auto()
