import threading
import time

import Pyro5.api as pyro


@pyro.expose
class HelloWorldServer:
    def __init__(self):
        self._clients = []
        self._clients_lock = threading.Lock()
        self._clients_message = {}

        self._notification_thread = threading.Thread(target=self._notify_clients, daemon=True)
        self._notification_thread.start()


    def register_interest(self, text: str, client_uri: str):
        print(f"Registrando o cliente {client_uri} com texto {text}")
        new_client = pyro.Proxy(client_uri)
        self._clients_message[new_client] = text
        self._clients_lock.acquire()
        self._clients.append(new_client)
        self._clients_lock.release()


    def _notify_clients(self):
        while True:
            time.sleep(1)
            self._clients_lock.acquire()
            clients = self._clients.copy()
            self._clients_lock.release()

            print(f"Enviando notificação para {len(self._clients)} clientes")
            for client in clients:
                client._pyroClaimOwnership()
                client.notify(self._clients_message[client])


class Server:
    def __init__(self):
        # Register the object as a Pyro object
        self._daemon = pyro.Daemon()
        self.uri = self._daemon.register(HelloWorldServer)

        # Register a name in the name server
        self._name_server = pyro.locate_ns()
        self._name_server.register("server", self.uri)

        self._daemon.requestLoop()


if __name__ == "__main__":
    print("Starting server")
    Server()
