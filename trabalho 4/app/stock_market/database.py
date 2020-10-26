import sqlite3
import threading
from typing import Dict

from ..order import Order, OrderType

class Database:
    """Wrapper para o banco de dados do stock market."""
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db_cursor = self.db.cursor()
        self.db_lock = threading.Lock()

    def execute(self, command: str, *args, **kwargs) -> sqlite3.Cursor:
        """Executa uma operação no DB."""
        with self.db_lock:
            cursor =  self.db_cursor.execute(command, *args, **kwargs)
            self.db.commit()
            return cursor

    def close(self):
        self.db.close()

    def get_order_from_id(self, order_id: int, order_type: OrderType) -> Order:
        data = self.execute(
            f'''select c.name, o.ticker, o.amount, o.price, o.expiry_date, o.active 
                from {order_type.value} as o inner join client as c on o.client_id = c.id 
                    where o.id = {order_id}''').fetchone()
        return Order(data[0], order_type, data[1], data[2], data[3], data[4], data[5])

    def get_stock_owned_by_client(self, client_name: str) -> Dict[str, float]:
        """Retorna a carteira de ações de um cliente."""
        command = f"""
            select ticker, amount from OwnedStock
            where client_id = (select id from Client where name = '{client_name}')
        """
        data = self.execute(command)
        return {entry[0]: entry[1] for entry in data}
