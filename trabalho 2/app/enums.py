from enum import Enum, auto

class OrderType(Enum):
    BUY = "BuyOrder"
    SELL = "SellOrder"

    def get_matching(self):
        if self is OrderType.BUY:
            return OrderType.SELL
        else:
            return OrderType.BUY

class MarketErrorCode(Enum):
    SUCCESS = auto()
    CLIENT_ALREADY_EXISTS = auto()
    UNKNOWN_CLIENT = auto()
    EXPIRED_ORDER = auto()
    NOT_ENOUGH_STOCK = auto()
    UNKNOWN_TICKER = auto()
