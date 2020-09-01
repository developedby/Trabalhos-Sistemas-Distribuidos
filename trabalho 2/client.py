import threading
import time

import Pyro5.api as pyro


@pyro.expose
class HelloWorldClient:
    def __init__(self, text: str, server_name: str):
        self._daemon = pyro.Daemon()
        self.uri = self._daemon.register(HelloWorldClient)

        self._name_server = pyro.locate_ns()
        self._server_uri = self._name_server.lookup(server_name)
        self._server = pyro.Proxy(self._server_uri)

        self._server.register_interest(text, self.uri)

        self._daemon.requestLoop()

    def notify(self, text: str):
        print(text)


if __name__ == "__main__":
    print("Starting client")
    HelloWorldClient("Hello world", 'server')
