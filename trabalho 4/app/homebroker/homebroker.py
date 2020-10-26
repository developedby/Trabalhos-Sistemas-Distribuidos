"""Servidor do homebroker."""
import datetime
import json
import os
import signal
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Callable, List, Tuple, Optional, Any, Sequence

import flask
import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook

from .client import Client, ClientStatus
from .consts import DATETIME_FORMAT
from .enums import OrderType, MarketErrorCode, HomebrokerErrorCode
from .order import Order, Transaction

class Homebroker:
    """
    Servidor do homebroker.

    Recebe pedidos de Client, passando as informações para StockMarket.

    Guarda o que o cliente está interessado,
    como limites de ganho e perda e uma lista de ações de interesse.

    Periodicamente pega atualizações de StockMarket,
    avisando os clientes caso tenha ocorrido algum evento de interesse.
    """

    def __init__(self, name: str, update_period: float):
        self.name = name
        self.update_period = update_period
        # Carrega as informações internas do homebroker
        self.load_initial_state()

        # Para as exceções remotas do Pyro aparecerem em um formato melhor
        sys.excepthook = pyro_excepthook

        # Conecta com o nameserver
        nameserver = pyro.locate_ns()

        # Conecta com a bolsa
        market_uri = nameserver.lookup('stockmarket')
        print(market_uri)
        self.market = pyro.Proxy(market_uri)
        self.market_lock = threading.Lock()

        # Registra as serializações dos objetos para o Pyro
        pyro.register_class_to_dict(Order, Order.to_dict)
        pyro.register_dict_to_class('Order', Order.from_dict)
        pyro.register_class_to_dict(Transaction, Transaction.to_dict)
        pyro.register_dict_to_class('Transaction', Transaction.from_dict)

        self.clients: Dict[str, Client] = {}
        self.clients_lock = threading.Lock()

        self.quotes: Dict[str, Optional[float]] = {}
        self.quotes_lock = threading.Lock()

        self.alert_limits: Dict[str, Dict[str, Tuple[float, float]]] = {}
        self.alerts_lock = threading.Lock()

        self.last_updated = datetime.datetime.now()

        # Registra o objeto no daemon do Pyro e no nameserver
        self.daemon = pyro.Daemon()
        my_uri = self.daemon.register(self)
        nameserver.register(f'homebroker-{self.name}', my_uri)

        # Registra o sinal pra fechar direito o programa
        signal.signal(signal.SIGINT, self.close)

        # Cria a thread que fica pegando atualizações da bolsa
        self.thread_updates = threading.Thread(target=self.update_data, daemon=True)
        self.thread_updates.start()

        # Fica respondendo os requests dos clientes
        self.thread_request_loop = threading.Thread(target=self.run, daemon=True)
        self.thread_request_loop.start()

    def load_initial_state(self):
        self.instance_path = Path(f'./instances/{self.name}')
        clients_path = self.instance_path / 'clients'

        if not os.path.isdir(self.instance_path):
            os.mkdir(self.instance_path)
            os.mkdir(clients_path)
        
        # Tenta pegar a trava de instancia do homebroker
        try:
            open(self.instance_path / 'instance_lock.~lock', 'x').close()
        except FileExistsError:
            raise ValueError(f"A instância '{self.name}' já está rodando. Cancelando inicialização.")

        # Carrega os dados dos clientes
        client_files = [
            file_name
            for file_name in os.listdir(clients_path)
            if os.path.isfile(clients_path/file_name)]
        self.clients = {}
        for file_name in client_files:
            new_client = Client.from_file(clients_path/file_name)
            self.clients[new_client.name] = new_client

        # Carrega as outras informações
        if os.path.isfile(self.instance_path/'internal_data.json'):
            with open(self.instance_path/'internal_data.json', 'r') as fp:
                data = json.load(fp)
            self.quotes = data['quotes']
            self.alert_limits = data['alert_limits']
            self.last_updated = datetime.datetime.strptime(data['last_updated'], DATETIME_FORMAT)

    def write_internal_data_file(self):
        with self.quotes_lock:
            with self.alerts_lock:
                with open(self.instance_path/'internal_data.json', 'w') as fp:
                    json.dump({
                        'quotes': self.quotes,
                        'alert_limits': self.alert_limits,
                        'last_updated': self.last_updated.strftime(DATETIME_FORMAT)
                    }, fp)

    def run(self):
        print("Rodando Homebroker")

        try:
            self.daemon.requestLoop()
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self, *args, **kwargs):
        """
        Termina o programa.
        Fecha as conexões.

        locks:
            clients_lock
            market_lock
        """
        print("Fechando o homebroker")
        try:
            # Fecha a conexão com os clientes
            with self.clients_lock:
                for client in self.clients.values():
                    if client.status is ClientStatus.CONNECTED:
                        client.status = ClientStatus.CLOSING
                for client in self.clients.values():
                    while client.status is ClientStatus.CLOSING:
                        time.sleep(0.01)
            # Fecha a conexão com o mercado
            with self.get_market():
                self.market._pyroRelease()
        finally:
            self.write_internal_data_file()
            if os.path.isfile(self.instance_path / 'instance_lock.~lock'):
                os.remove(self.instance_path / 'instance_lock.~lock')
            sys.exit(0)

    @contextmanager
    def get_market(self):
        """Context manager pra pegar exclusividade no proxy."""
        self.market_lock.acquire()
        self.market._pyroClaimOwnership()
        try:
            yield
        finally:
            self.market_lock.release()

    def update_data(self):
        """
        Fica atualizando os dados do homebroker periodicamente.
        Envia notificações para os clientes caso ocorra algum evento.

        locks:
            update_quotes()
            update_orders()
        """
        while(True):
            time.sleep(self.update_period)
            self.update_quotes()
            self.update_orders()

    def update_quotes(self):
        """
        Atualiza as cotações de todas as ações que o homebroker observa.
        
        locks:
            quotes_lock
                market_lock
                alerts_lock
        """
        # Atualiza as cotações
        with self.quotes_lock:
            with self.get_market():
                self.quotes = self.market.get_quotes(self.quotes.keys())
            # Pega uma cópia porque essa funcao pode ser chamada de varios lugares ao mesmo tempo
            quotes_copy = self.quotes.copy()

        # Envia os alertas de limite de preço para os clientes, caso haja
        alerts_to_remove = []
        for ticker in quotes_copy:
            # Se tem alerta para a ação
            if ticker in self.alert_limits:
                with self.alerts_lock:
                    for client, limits in self.alert_limits[ticker].items():
                        # Se tem limite minimo e o valor da ação ta mais baixo que o limite
                        # Ou se tem maximo e o valor da ação ta maior
                        if ((limits[0] is not None) and (quotes_copy[ticker] <= limits[0])
                                or ((limits[1] is not None) and (quotes_copy[ticker] >= limits[1]))):
                            # Chama a callback do cliente
                            self.clients[client].notify_limit(ticker, quotes_copy[ticker])
                            alerts_to_remove.append((ticker, client))
        with self.alerts_lock:
            for ticker_client in alerts_to_remove:
                try:
                    self.alert_limits[ticker_client[0]].pop(ticker_client[1])
                # Se foi removida por outra thread, não faz mal
                except KeyError:
                    pass

        # Salva as atualizações em um arquivo
        self.write_internal_data_file()

    def update_orders(self):
        """
        Atualiza as ordens de todos os clientes do homebroker.

        locks:
            clients_lock
                orders_lock
                    market_lock
                market_lock
                quotes_lock
                    market_lock
                
        """
        with self.clients_lock:
            with self.get_market():
                active_orders_per_client = self.market.get_orders(self.clients.keys(), active_only=True)
            
            # Notificações que tem que enviar aos clientes
            # {nome do cliente: (transacoes, orderns ativas, ordens expiradas, acoes possuidas)}
            notifications_per_client = {
                client_name: [[], [] ,[], {}]
                for client_name in self.clients}

            # Pega as ordens que expiraram
            # TODO: Se tem duas ordens ativas da mesma ação e uma expira, ele não avisa

            # Separa as ordens novas
            active_orders = set()
            for orders_of_a_client in active_orders_per_client.values():
                for order in orders_of_a_client:
                    active_orders.add((order.client_name, order.ticker))
            # Se uma ordem antiga deixou de estar ativa e expirou
            # Assume que desativou pela expiração , então avisa o cliente
            for client_name, client in self.clients.items():
                with client.orders as order_data:
                    for order in order_data:
                        order_simple = (order.client_name, order.ticker)
                        if (order_simple not in active_orders) and order.is_expired():
                            notifications_per_client[client_name][2].append(order.ticker)

            # Atualiza as ordens ativas
            for client_name, client_orders in active_orders_per_client.items():
                notifications_per_client[client_name][1] = client_orders
                with self.clients[client_name].orders:
                    self.clients[client_name].orders.set(client_orders)

            # Pega as transações realizadas no último intervalo e atualiza as carteira
            # Pega as transações novas
            with self.get_market():
                transactions_per_client = self.market.get_transactions(
                    self.clients.keys(), self.last_updated.strftime(DATETIME_FORMAT))
            # Atualiza o contador de tempo
            self.last_updated = datetime.datetime.now()
            # Atualiza a carteira dos clientes e avisa
            for client_name, transactions in transactions_per_client.items():
                with self.clients[client_name].owned_stock as owned_stock:
                    if transactions:
                        notifications_per_client[client_name][0] = transactions
                        with self.get_market():
                            self.clients[client_name].owned_stock.set(
                                self.market.get_stock_owned_by_client(client_name))
                        # Coloca as ações da carteira do cliente na lista de interesse dele
                        for ticker in self.clients[client_name].owned_stock.get():
                            with self.clients[client_name].quotes as quotes:
                                if ticker not in quotes:
                                    with self.quotes_lock:
                                        with self.get_market():
                                            self.quotes[ticker] = self.market.get_quotes([ticker])
                                    quotes.append(ticker)

                    notifications_per_client[client_name][3] = owned_stock

            # Envia as notificações aos clientes
            for client, notification in notifications_per_client.items():
                # Só envia se mudou alguma coisa (transação ou ordem exirou)
                if notification[0] or notification[2]:
                    self.clients[client].notify_order(*notification)

        # Guarda as alterações em um arquivo
        for client in self.clients.values():
            client.to_file(self.instance_path)
        self.write_internal_data_file()

    @staticmethod
    def format_sse_message(data: str,
                           event: Optional[str] = None,
                           id: Optional[str] = None) -> str:
        """
        Retorna uma resposta no formato SSE.

        :param data: Mensagem que vai ser enviada.
        :param event: Nome do evento desta mensagem.
        :param id: Id da mensagem.
        """
        # TODO: Descobrir porque quebra quando põe campos além de 'data'
        if not data:
            raise ValueError("'data' must not be empty.")

        msg = ''
        if event:
            msg += 'event: {}\r\n'.format(event)
        if id:
            msg += 'id: {}\r\n'.format(id)
        msg += 'data: {}\r\n'.format(data)
        msg += '\r\n'
        return msg

    # Funções de interface com o cliente
    # Conectam com o app flask
    def add_stock_to_quotes(self, ticker, client_name) -> flask.Response:
        """
        Adiciona uma ação à lista de cotações de um cliente.
        
        locks:
            market_lock
            quotes_lock
            update_quotes()
        """
        print("add_stock_to_quotes->(", ticker, ", ",client_name, ")")

        # Checa se os argumentos são validos
        if client_name not in self.clients:
            return str(HomebrokerErrorCode.UNKNOWN_CLIENT), 404
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return str(HomebrokerErrorCode.UNKNOWN_TICKER), 404


        with self.clients[client_name].quotes as quotes:
            if ticker not in quotes:
                quotes.append(ticker)

        # Pega o valor da ação (atualiza todo mundo)
        with self.quotes_lock:
            self.quotes[ticker] = None
        self.update_quotes()

        return str(HomebrokerErrorCode.SUCCESS), 200

    def remove_stock_from_quotes(self, ticker, client_name) -> flask.Response:
        """
        Remove uma ação da lista de cotações de um cliente.
        
        locks:
            clients_lock
            quotes_lock
        """
        print("remove_stock_from_quotes", ticker, client_name)

        # Verifica o nome do cliente
        if client_name not in self.clients:
            return str(HomebrokerErrorCode.UNKNOWN_CLIENT), 404

        # Tenta remover a ação da lista de cotações do cliente
        try:
            self.clients[client_name].quotes.get().remove(ticker)
        # Se não tinha essa ação na lista
        except ValueError:
            return str(HomebrokerErrorCode.UNKNOWN_TICKER), 404

        # Verifica se algum cliente ainda tem interesse nessa ação
        has_interest = False
        with self.clients_lock:
            for client in self.clients:
                if ticker in self.clients[client].quotes:
                    has_interest = True
                    break
        # Se ninguem tem, remove da lista de ações que atualiza cotação
        if not has_interest:
            with self.quotes_lock:
                self.quotes.pop(ticker)
        
        return str(HomebrokerErrorCode.SUCCESS), 200

    def get_current_quotes(self, client_name) -> flask.Response:
        """
        Retorna as cotações atuais das ações que o cliente está interessado.

        locks:
            update_quotes()
            quotes_lock
        """
        print("get_current_quotes", client_name)

        if client_name not in self.clients:
            return str(HomebrokerErrorCode.UNKNOWN_CLIENT), 404

        self.update_quotes()

        # Pega todas as cotações desse cliente
        with self.quotes_lock:
            client_quotes : Dict[str, Optional[float]] = {
                ticker: quote for ticker, quote in self.quotes.items()
                if ticker in self.clients[client_name].quotes
            }

        return flask.jsonify(client_quotes)

    def add_quote_alert(self, ticker, lower_limit, upper_limit, client_name) -> flask.Response:
        """
        Adiciona limites de valor pra alertar um cliente sobre uma ação.
        O alerta vai ser enviado quando a ação passa do mínimo ou do máximo.

        locks:
            market_lock
            alerts_lock
        """
        print('add_quote_alert', ticker, lower_limit, upper_limit, client_name)

        # Verifica os argumentos
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return str(HomebrokerErrorCode.UNKNOWN_TICKER), 404
        if client_name not in self.clients:
            return str(HomebrokerErrorCode.UNKNOWN_CLIENT), 404
        try:
            lower_limit = int(lower_limit)
            upper_limit = int(upper_limit)
        except ValueError:
            return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

        # Adiciona o limite
        with self.alerts_lock:
            if ticker not in self.alert_limits:
                self.alert_limits[ticker] = {client_name: (lower_limit, upper_limit)}
            else:
                self.alert_limits[ticker][client_name] = (lower_limit, upper_limit)

        return str(HomebrokerErrorCode.SUCCESS), 200

    def create_order(self, order) -> flask.Response:
        """
        Cria uma ordem de compra ou de venda.
        
        locks:
            orders_lock
                market_lock
        """
        print('Create order', order)

        with self.get_market():
            # Manda pra bolsa
            error = self.market.create_order(order)
        error = MarketErrorCode(error)
        # Se deu erro, retorna e avisa o cliente
        if error is not MarketErrorCode.SUCCESS:
            error = HomebrokerErrorCode[error.name]
            if error in (HomebrokerErrorCode.EXPIRED_ORDER,):
                status = 400
            elif error in (HomebrokerErrorCode.UNKNOWN_CLIENT,
                            HomebrokerErrorCode.UNKNOWN_TICKER):
                status = 404
            elif error in (HomebrokerErrorCode.NOT_ENOUGH_STOCK,):
                status = 403
            # Se não é nenhum dos erros esperados, alguma coisa está errada com o servidor
            else:
                status = 500
            return str(error), status

        self.clients[order.client_name].orders.get().append(order)

        return str(HomebrokerErrorCode.SUCCESS), 200

    def connect_client(self, client_name) -> flask.Response:
        """
        Conecta um cliente novo ao homebroker.
        Retorna um event-stream onde vao ser passadas as notificações.
        Se o cliente não era conhecido adiciona um novo.
        Se o cliente já tinha uma conexão ativa, fecha ela e cria uma nova.

        locks:
            clients_lock
            market_lock
        """
        # Verifica se o nome é válido
        if client_name in ('Market', ''):
            return str(HomebrokerErrorCode.FORBIDDEN_NAME), 403

        # Se o cliente já tem uma conexão aberta, fecha a conexão antiga
        if (client_name in self.clients
                and self.clients[client_name].status is ClientStatus.CONNECTED):
            return str(HomebrokerErrorCode.CLIENT_ALREADY_EXISTS), 403
        # Caso cliente novo, cria e manda pro mercado
        else:
            with self.clients_lock:
                self.clients[client_name] = Client(client_name)
            with self.get_market():
                self.market.add_client(client_name)
                
        with self.get_market():
            self.clients[client_name].orders = self.market.get_orders([client_name], active_only=True)[client_name]
            self.clients[client_name].owned_stock = self.market.get_stock_owned_by_client(client_name)
        with self.quotes_lock:
            for owned_quote in self.clients[client_name].owned_stock.get():
                if (not (owned_quote in self.clients[client_name].quotes)):
                    self.clients[client_name].quotes.get().append(owned_quote)
                    self.quotes[owned_quote] = None
        self.update_quotes()
        print(f"Novo cliente: {client_name}")

        # Função que vai retornando o stream de notificações
        def stream():
            nonlocal self
            nonlocal client_name
            self.clients[client_name].status = ClientStatus.CONNECTED
            try:
                # Mensagem de inicio
                yield self.format_sse_message(data="0")
                # Fica mandando as notificações quando elas acontecerem
                while True:
                    # Fica esperando uma mensagem
                    msg = self.clients[client_name].notification_queue.get()
                    # Se algum fator externo fechou o cliente enquanto esperava,
                    # coloca a mensagem de volta na fila
                    if self.clients[client_name].status is not ClientStatus.CONNECTED:
                        self.clients[client_name].notification_queue.put(msg)
                        break
                    print('Mandando evento')
                    # Envia ao cliente
                    yield self.format_sse_message(msg)
                # Mensagem de fim
                yield self.format_sse_message(data="1")
            # Quando o cliente desconecta ou se para por algum outro motivo,
            # marca como desconectado
            finally:
                self.clients[client_name].status = ClientStatus.DISCONNECTED

        # Fica mandando stream das notificações enquanto status do cliente for connected
        response = flask.Response(stream(), mimetype='text/event-stream')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add("Cache-Control", "no-cache")
        return response

    def get_client_status(self, client_name) -> flask.Response:
        """
        Retorna o estado atual do cliente. Cotações, Ordens, carteira e alertas.
        
        locks:
            market_lock
            alerts_lock
        """
        print(f'get_client_status {client_name}')

        if client_name not in self.clients:
            return str(HomebrokerErrorCode.UNKNOWN_CLIENT), 404

        # Pega as informações do estado do cliente
        for owned_quote in self.clients[client_name].owned_stock.get():
            if (not owned_quote in self.clients[client_name].quotes):
                self.clients[client_name].quotes.get().append(owned_quote)
        with self.get_market():
            quotes: Dict[str, float] = self.market.get_quotes(
                self.clients[client_name].quotes)
            orders: List[Dict[str, Any]] = [
                Order.to_dict(order)
                for order in self.market.get_orders([client_name], active_only=True)[client_name]]
            owned_stock: Dict[str, float] = \
                self.market.get_stock_owned_by_client(client_name)
        alerts: Dict[str, Tuple[float, float]] = {}
        with self.alerts_lock:
            for ticker in self.alert_limits:
                if client_name in self.alert_limits[ticker]:
                    alerts[ticker] = self.alert_limits[ticker][client_name]
    
        return flask.jsonify(
            quotes=quotes, orders=orders, owned_stock=owned_stock, alerts=alerts)

hb_name = input("Insira o nome do homebroker: ")
homebroker = Homebroker(hb_name, 5)
print("Homebroker backend rodando")

flask_app = flask.Flask(__name__)
flask_app.config["DEBUG"] = True
print("Flask App rodando")

# Funções do Flask
@flask_app.route('/quote', methods=['POST'])
def add_stock_to_quotes() -> flask.Response:
    global homebroker
    # Pega os argumentos do request
    request_body = flask.request.get_json()
    # Se o tipo não era text/json é None
    if request_body is None:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400
    try:
        ticker = request_body['ticker']
        client_name = request_body['client_name']
    # Se não tinha um dos argumentos
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.add_stock_to_quotes(ticker, client_name)


@flask_app.route('/quote', methods=['DELETE'])
def remove_stock_from_quotes() -> flask.Response:
    global homebroker
    # Pega os argumentos do request
    try:
        client_name = flask.request.args['client_name']
        ticker = flask.request.args['ticker']
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.remove_stock_from_quotes(ticker, client_name)


@flask_app.route('/quote', methods=['GET'])
def get_current_quotes() -> flask.Response:
    global homebroker
    # Pega o nome do cliente no request
    try:
        client_name = flask.request.args['client_name']
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.get_current_quotes(client_name)


@flask_app.route('/limit', methods=['POST'])
def add_quote_alert() -> flask.Response:
    global homebroker
    # Pega os argumentos do request
    request_body = flask.request.get_json()
    # Se o tipo não era text/json é None
    if request_body is None:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400
    try:
        ticker = request_body['ticker']
        lower_limit = request_body['lower_limit']
        upper_limit = request_body['upper_limit']
        client_name = request_body['client_name']
    # Se não tinha um dos argumentos
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.add_quote_alert(ticker, lower_limit, upper_limit, client_name)


@flask_app.route('/order', methods=['POST'])
def create_order() -> flask.Response:
    global homebroker
    # Pega a order do request
    request_body = flask.request.get_json()
    # Se o tipo não era text/json é None
    if request_body is None:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400
    try:
        order = Order.from_dict('Order', request_body)

    # Se não tinha um dos argumentos ou argumento invalido
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.create_order(order)


@flask_app.route('/login', methods=['GET'])
def connect_client() -> flask.Response:
    global homebroker
    # Extrae o nome do cliente do request
    try:
        client_name = flask.request.args['client_name']
    # Se não tinha um dos argumentos
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.connect_client(client_name)


@flask_app.route('/status', methods=['GET'])
def get_client_status() -> flask.Response:
    global homebroker
    # Pega o nome do cliente no request
    try:
        client_name = flask.request.args['client_name']
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400

    return homebroker.get_client_status(client_name)


@flask_app.route('/')
def index():
    with open('./api.html', 'r') as api_file:
        return api_file.read(-1)

@flask_app.route('/close', methods=['GET'])
def close_connection() -> flask.Response:
    global homebroker
    # Extrae o nome do cliente do request
    try:
        client_name = flask.request.args['client_name']
    # Se não tinha um dos argumentos
    except KeyError:
        return str(HomebrokerErrorCode.INVALID_MESSAGE), 400
    if (homebroker.clients[client_name].status == ClientStatus.CONNECTED):
        homebroker.clients[client_name].status = ClientStatus.CLOSING
    return "", 200
    
    