"""Servidor do homebroker."""
from contextlib import contextmanager
import datetime
import sys
import threading
import time
from typing import Dict, Callable, List, Tuple, Optional

import flask
import Pyro5.api as pyro
from Pyro5.errors import excepthook as pyro_excepthook

from .client import Client, ClientStatus
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
    def __init__(self, update_period: float):
        self.update_period = update_period

        # Para as exceções remotas aparecerem em um formato melhor
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

        self.datetime_format = "%Y-%m-%d %H:%M:%S"
        self.clients: Dict[str, Client] = {}
        self.quotes: Dict[str, float] = {}
        self.quotes_lock = threading.Lock()
        self.orders_lock = threading.Lock()
        self.clients_lock = threading.Lock()
        self.alerts_lock = threading.Lock()
        self.alert_limits: Dict[str, Dict[str, Tuple[float, float]]] = {}
        self.last_updated = datetime.datetime.now()

        # Registra o objeto no daemon do Pyro e no nameserver
        self.daemon = pyro.Daemon()
        my_uri = self.daemon.register(self)
        nameserver.register('homebroker', my_uri)

        # Cria a thread que fica pegando atualizações da bolsa
        self.thread_updates = threading.Thread(target=self.update_data, daemon=True)
        self.thread_updates.start()

        # Fica respondendo os requests dos clientes
        self.thread_request_loop = threading.Thread(target=self.run, daemon=True)
        self.thread_request_loop.start()

    def run(self):
        print("Rodando Homebroker")
        try:
            self.daemon.requestLoop()
        except KeyboardInterrupt:
            pass
        finally:
            print('Fechando Homebroker')
            self.close()

    def close(self):
        """
        Termina o programa.
        Fecha as conexões.

        locks:
            clients_lock
            market_lock
        """
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
        for ticker_client in alerts_to_remove:
            self.alert_limits[ticker_client[0]].pop(ticker_client[1])

    def update_orders(self):
        """
        Atualiza as ordens de todos os clientes do homebroker.

        locks:
            clients_lock
                orders_lock
                    market_lock
                market_lock
        """
        # Pega uma copia dos clientes, pra evitar problemas de concorrencia
        with self.clients_lock:
            client_names = self.clients.keys()
            with self.orders_lock:
                with self.get_market():
                    orders_per_client = self.market.get_orders(client_names, active_only=True)
                
                # Notificações que tem que enviar aos clientes
                # {nome do cliente: (transacoes, orderns ativas, ordens expiradas, acoes possuidas)}
                notifications_per_client = {client: [[], [] ,[], {}] for client in self.clients}

                # Pega as ordens que expiraram
                # Separa as ordens novas
                new_orders = set()
                for orders_of_a_client in orders_per_client.values():
                    for order in orders_of_a_client:
                        new_orders.add((order.client_name, order.ticker))
                # Separa as ordens antigas
                old_orders = set()
                for client in self.clients.values():
                    for order in client.orders:
                        old_orders.add((order.client_name, order.ticker))
                # Pega somente as ordens que ficaram inativas
                inactive_orders = old_orders.difference(new_orders)
                # Das recem inativas, pega somente as que expiraram para enviar pro cliente
                for client_name in self.clients.keys():
                    for order in self.clients[client_name].orders:
                        if ((client_name, order.ticker) in inactive_orders
                                and order.is_expired()):
                            notifications_per_client[client_name][2].append(order.ticker)

                # Atualiza as ordens ativas
                for client_name, client_orders in orders_per_client.items():
                    notifications_per_client[client_name][1] = client_orders
                    self.clients[client_name].orders = client_orders

            # Pega as transações realizadas no último intervalo e atualiza as carteira
            with self.get_market():
                transactions_per_client = self.market.get_transactions(
                    client_names, self.last_updated.strftime(self.datetime_format))
            # Warning: Pode perder alguma transação por race condition
            # Caso perca, não vai notificar o cliente, mas o resto ainda funciona
            self.last_updated = datetime.datetime.now()
            for client_name, transactions in transactions_per_client.items():
                if transactions:
                    notifications_per_client[client_name][0] = transactions
                    with self.get_market():
                        self.clients[client_name].owned_stock = \
                            self.market.get_stock_owned_by_client(client_name)
                notifications_per_client[client_name][3] = self.clients[client_name].owned_stock

            # Envia as notificações aos clientes
            for client, notification in notifications_per_client.items():
                # Só envia se mudou alguma coisa (transação ou ordem exirou)
                if notification[0] or notification[2]:
                    self.clients[client].notify_order(*notification)

    @staticmethod
    def format_sse_message(data: str,
                           event: Optional[str] = None,
                           id: Optional[str] = None) -> flask.Response:
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
            msg += 'event: {}\n'.format(event)
        if id:
            msg += 'id: {}\n'.format(id)
        msg += 'data: {}\n'.format(data)
        msg += '\n'
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
        print("add_stock_to_quotes", ticker, client_name)

        # Checa se os argumentos são validos
        if client_name not in self.clients:
            return str(HomebrokerErrorCode.UNKNOWN_CLIENT), 404
        with self.get_market():
            ticker_exists = self.market.check_ticker_exists(ticker)
        if not ticker_exists:
            return str(HomebrokerErrorCode.UNKNOWN_TICKER), 404

        self.clients[client_name].quotes.append(ticker)
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
            self.clients[client_name].quotes.remove(ticker)
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
            client_quotes = {
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

        with self.orders_lock:
            with self.get_market():
                error = self.market.create_order(order)
            error = MarketErrorCode(error)
            if error is not MarketErrorCode.SUCCESS:
                return str(HomebrokerErrorCode[error.name]), 400
            self.clients[order.client_name].orders.append(order)

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
            print(f"Novo cliente: {client_name}")

        # Função que vai retornando o stream de notificações
        def stream():
            nonlocal self
            nonlocal client_name
            self.clients[client_name].status = ClientStatus.CONNECTED
            yield self.format_sse_message(data="0")

            while True:
                msg = self.clients[client_name].notification_queue.get()
                if self.clients[client_name].status is not ClientStatus.CONNECTED:
                    self.clients[client_name].notification_queue.put(msg)
                    break
                print('Mandando evento')
                yield self.format_sse_message(msg)

            self.clients[client_name].status = ClientStatus.DISCONNECTED
            yield self.format_sse_message(data="1")

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
        with self.get_market():
            quotes = self.market.get_quotes(self.clients[client_name].quotes)
            orders = self.market.get_orders([client_name], active_only=True)[client_name]
            owned_stock = self.market.get_stock_owned_by_client(client_name)
        orders = {
            ticker: [Order.to_dict(order) for order in order_list]
            for ticker, order_list in orders.items()}
        alerts = {}
        with self.alerts_lock:
            for ticker in self.alert_limits:
                if client_name in self.alert_limits[ticker]:
                    alerts[ticker] = self.alert_limits[ticker][client_name]
    
        return flask.jsonify(
            quotes=quotes, orders=orders, owned_stock=owned_stock, alerts=alerts)

homebroker = Homebroker(5)
print("Homebroker backend rodando")

flask_app = flask.Flask(__name__)
flask_app.config["DEBUG"] = True
print("Flask App rodando")


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
