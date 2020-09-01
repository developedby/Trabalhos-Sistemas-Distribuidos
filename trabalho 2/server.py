import threading
import time

import Pyro5.api as pyro


@pyro.expose
class HelloWorldServer:
    def __init__(self):
        # Register the object as a Pyro object
        self._daemon = pyro.Daemon()
        self.uri = self._daemon.register(HelloWorldServer)
        # Register a name in the name server
        self._name_server = pyro.locate_ns()
        self._name_server.register("server", self.uri)

        self._interested_clients = []
        self._interested_clients_lock = threading.Lock()

        self._notification_thread = threading.Thread(target=self._notify_clients, daemon=True)
        self._notification_thread.start()

        self._daemon.requestLoop()


    def register_interest(self, text: str, client_uri: str):
        new_client = pyro.Proxy(client_uri)
        new_client.text = text
        self._interested_clients_lock.acquire()
        self._interested_clients.append(new_client)
        self._interested_clients_lock.release()


    def _notify_clients(self):
        while True:
            time.sleep(1)
            self._interested_clients_lock.acquire()
            interested_clients = self._interested_clients.copy()
            self._interested_clients_lock.release()

            for client in interested_clients:
                client.notify(client.text)


if __name__ == "__main__":
    print("Starting server")
    HelloWorldServer()
