import enum
import json
import queue
from typing import Mapping, Sequence, List, Dict, Tuple

from ..order import Order, Transaction

class ClientStatus(enum.Enum):
    """Estados possíveis do cliente."""
    DISCONNECTED = enum.auto()
    CONNECTED = enum.auto()
    CLOSING = enum.auto()

class Client:
    """Representação de um cliente dentro do servidor."""
    def __init__(self, name: str):
        self.notification_queue = queue.Queue(maxsize=10)
        self.name = name
        self.quotes: List[str] = []  # Tickers
        self.owned_stock: Dict[str, float] = {}  # Ticker, quantidade
        self.orders: List[Order] = []
        self.status = ClientStatus.DISCONNECTED

    def notify_limit(self, ticker, current_quote):
        """
        Notifica que um limite foi alcançado.

        :param ticker: Nome da ação que alcançou o limite.
        :param current_quote: Preço atual da ação.
        """
        # TODO: Colocar em outra thread pra nao esperar ou trocar para put_nowait?
        self.notification_queue.put(
            json.dumps({'ticker': ticker, 'current_quote': current_quote}, indent=2))

    def notify_order(self,
                     transactions: Sequence[Transaction],
                     active_orders: Sequence[Order],
                     expired_orders: Sequence[str],
                     owned_stock: Mapping[str, float]):
        """
        Notifica que ocorreu uma transação ou alguma ordem expirou.
        Também envia as ordens ativas atuais e a carteira do cliente.

        :param transactions: Transações que ocorreram com o cliente.
        :param active_orders: Ordens atualmente ativas do cliente.
        :param expired_orders: Ordens do que expiraram sem serem compledas.
        :param owned_stock: Carteira do cliente.
        """
        transactions = [Transaction.to_dict(t) for t in transactions]
        active_orders = [Order.to_dict(o) for o in active_orders]
        self.notification_queue.put(
            json.dumps({'transactions': transactions,
                        'active_orders': active_orders,
                        'expired_orders': expired_orders,
                        'owned_stock': owned_stock}, indent=2))