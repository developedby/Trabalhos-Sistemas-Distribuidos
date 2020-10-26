import sqlite3
import threading

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
            return self.db_cursor.execute(command, *args, **kwargs)

    def close(self):
        self.db.close()

    def get_order_from_id(self, order_id: int, order_type: OrderType) -> Order:
        data = self.execute(
            f'''select * from {order_type.value} where id = {order_id}''').fetchone()
        return Order(data[1], order_type, data[2], data[3], data[4], data[5], data[6])
