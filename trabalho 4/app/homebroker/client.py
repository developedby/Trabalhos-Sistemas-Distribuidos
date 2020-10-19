import enum
import json
import os
import queue
from typing import Mapping, Sequence, List, Dict, Tuple

from .resource import Resource
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
        # TODO: Trocar pra Resource[List] etc, quando tiver funcionando
        self.quotes: List[str] = Resource([])  # Tickers
        self.owned_stock: Dict[str, float] = Resource({})  # Ticker, quantidade
        self.orders: List[Order] = Resource([])

        self.status = ClientStatus.DISCONNECTED

    def notify_limit(self, ticker, current_quote):
        """
        Notifica que um limite foi alcançado.

        :param ticker: Nome da ação que alcançou o limite.
        :param current_quote: Preço atual da ação.
        """
        # TODO: Colocar em outra thread pra nao esperar ou trocar para put_nowait?
        self.notification_queue.put(
            json.dumps({'event': 'limit',
                        'ticker': ticker,
                        'current_quote': current_quote}))

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
            json.dumps({'event': 'order',
                        'transactions': transactions,
                        'active_orders': active_orders,
                        'expired_orders': expired_orders,
                        'owned_stock': owned_stock}))

    def to_json(self) -> str:
        return json.dumps({
            'client_name': self.name,
            'quotes': self.quotes.get(),
            'owned_stock': self.owned_stock.get(),
            'orders': self.orders.get().to_dict()
        })

    @staticmethod
    def from_json(json_data: str) -> 'Client':
        data = json.loads(json_data)
        new_client = Client(data['client_name'])
        new_client.quotes.set(data['quotes'])
        new_client.owned_stock.set(data['owned_stock'])
        new_client.orders.set(Order.from_dict(data['orders']))
        return new_client

    @staticmethod
    def from_file(file_path: str) -> 'Client':
        with open(file_path, 'r') as f:
            return Client.from_json(f.read())

    def to_file(self, clients_dir: str):
        with open(clients_dir/f'{self.name}.json', 'w') as dest_file:
            dest_file.write(self.to_json())