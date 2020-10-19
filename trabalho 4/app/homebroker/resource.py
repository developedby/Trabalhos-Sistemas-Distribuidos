import threading
from contextlib import contextmanager
from typing import Any

# TODO: Descobrir como fazer a sintaxe de typing Resource[TipoDoRecurso]

class Resource:
    def __init__(self, resource: Any):
        self._resource = resource
        self._lock = threading.Lock()

    @contextmanager
    def __call__(self) -> Any:
        resource = self.acquire()
        try:
            yield resource
        finally:
            self.release()

    def acquire(self):
        self._lock.acquire()
        return self.get()

    def release(self):
        self._lock.release()

    def get(self):
        return self._resource

    def set(self, value):
        self._resource = value
