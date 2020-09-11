import datetime
import threading
from typing import Sequence, Mapping

import Pyro5.api as pyro

from ..enums import HomebrokerErrorCode, OrderType
from ..order import Order, Transaction

class ClientGui(threading.Thread):
    """
    Interface gráfica do cliente. Cuida de toda a interação com o usuário.

    Como usa Tkinter que é single-threaded,
    as noticações recebidas do servidor são armazenadas
    e só são mostradas na GUI quando ela atualizar.

    :param app: Referencia ao Client.
    :param update_period: A cada quantos milisegundos atualiza a interface.
    """
    def __init__(self, app: "Client", update_period: int = 500, *args, **kwargs):
        self.app = app
        self.update_period = update_period

        self.error_messages = {
            HomebrokerErrorCode.NOT_ENOUGH_STOCK: "Não tem ações suficientes para realizar a ordem de venda.",
            HomebrokerErrorCode.UNKNOWN_TICKER: "Ação não encontrada."
        }
        self.datetime_format = "%Y-%m-%d %H:%M:%S"

        # Variaveis pra comunicar mudancas para a gui
        self.quotes = {}  # Ticker: price
        self.owned_stock = {}  # Ticker: amount
        self.active_orders = [] # lista de Order
        self.new_messages = []  # strings
        self.notified_alerts = {}

        self.update_lock = threading.Lock()

        super().__init__(*args, **kwargs)
        self.start()

    def run(self):
        """Inicia a Thread da GUI."""
        # Precisa importar tkinter aqui e não global porque não é multithread
        import tkinter as tk
        from tkinter import ttk
        # Por isso, precisa armazenar uma referencia ao modulo
        self.tk = tk
        self.ttk = ttk

        # Cria a janela principal
        self.main_window = self.tk.Tk()
        self.main_window.withdraw()
        self.main_window.title("Cliente Homebroker")
        self.main_window.protocol("WM_DELETE_WINDOW", self.close)
        self.assemble_main_window()

        # Cria o popup para inserir o nome de usuário
        self.create_popup_user_name()

        # Fica atualizando a GUI a cada tanto tempo
        self.main_window.after(self.update_period, self.update_gui)

        self.main_window.mainloop()

    def update_gui(self):
        """
        Atualiza a interface gráfica periodicamente
        com as informações enviadas e recebidas pela aplicação.
        """
        self.update_limits()
        self.update_orders()
        self.update_owned_stock()
        self.main_window.after(self.update_period, self.update_gui)

    def update_limits(self):
        """Mostra um alerta para cada limite alcançado e remove-o."""
        with self.update_lock:
            for ticker in self.notified_alerts:
                self.insert_message(
                    f"Limite alcançado para {ticker}. "
                    f"Valor atual: {self.notified_alerts[ticker]}")

                try:
                    item = self.quotes_frame.treeview.item(ticker)
                except Exception:
                    pass
                else:
                    values = list(item['values'])
                    values[1] = ''
                    self.quotes_frame.treeview.item(ticker, values=values)
            self.notified_alerts = {}

    def update_orders(self):
        """Atualiza as ordens ativas."""
        with self.update_lock:
            self.orders_frame.treeview.delete(
                *self.orders_frame.treeview.get_children())
            for order in self.active_orders:
                self.insert_order_in_treeview(order)

    def update_owned_stock(self):
        """Atualiza a carteira."""
        new_tickers = []
        with self.update_lock:
            self.owned_stock_frame.treeview.delete(
                *self.owned_stock_frame.treeview.get_children())
            for ticker in self.owned_stock:
                # Se é uma ação nova, marca pra ser adicionada
                if ticker not in self.quotes:
                    new_tickers.append(ticker)
                # Se não, atualiza o valor
                else:  
                    stock_value = self.owned_stock[ticker] * self.quotes[ticker]
                    self.owned_stock_frame.treeview.insert(
                        '', 'end', ticker,
                        text=ticker,
                        values=(self.owned_stock[ticker], stock_value)
                    )
        for ticker in new_tickers:
            self.add_quote(ticker)

    def assemble_main_window(self):
        """Monta a janela principal."""
        self.main_window.rowconfigure(0, weight=1)
        self.main_window.rowconfigure(1, weight=1)
        self.main_window.columnconfigure(0, weight=1)
        self.main_window.columnconfigure(1, weight=1)

        self.quotes_frame = self.tk.Frame(
            self.main_window, relief=self.tk.RIDGE, borderwidth=3)
        self.orders_frame = self.tk.Frame(
            self.main_window, relief=self.tk.RIDGE, borderwidth=3)
        self.owned_stock_frame = self.tk.Frame(
            self.main_window, relief=self.tk.RIDGE, borderwidth=3)
        self.messages_frame = self.tk.Frame(
            self.main_window, relief=self.tk.RIDGE, borderwidth=3)

        self.quotes_frame.grid(row=0, column=0, sticky='nswe')
        self.orders_frame.grid(row=0, column=1, sticky='nswe')
        self.owned_stock_frame.grid(row=1, column=0, sticky='nswe')
        self.messages_frame.grid(row=1, column=1, sticky='nswe')

        self.assemble_quotes_frame()
        self.assemble_owned_stock_frame()
        self.assemble_orders_frame()
        self.assemble_messages_frame()

    def assemble_quotes_frame(self):
        """Monta o frame com as cotações atuais e widgets associados."""
        # Widgets Quotes Frame
        frame = self.quotes_frame
        frame.rowconfigure(2, weight=1)

        frame.title_label = self.tk.Label(frame, text="Cotações")
        frame.update_btn = self.tk.Button(
            frame, text="Atualizar", command=self.update_quotes)
        frame.treeview = self.ttk.Treeview(frame, columns=('quote', 'alert'))
        #frame.treeview_scrollbar = self.tk.Scrollbar(frame)
        frame.quote_btns_frame = self.tk.Frame(
            frame, relief=self.tk.RIDGE, borderwidth=3)
        frame.alert_btns_frame = self.tk.Frame(
            frame, relief=self.tk.RIDGE, borderwidth=3)

        frame.title_label.grid(row=0, column=0, columnspan=1)
        frame.update_btn.grid(row=0, column=1, columnspan=1)
        frame.treeview.grid(row=2, column=0, columnspan=2, sticky='nswe')
        #frame.treeview_scrollbar.grid(row=2, column=1, sticky='ns')
        frame.quote_btns_frame.grid(row=3, column=0, sticky='nswe')
        frame.alert_btns_frame.grid(row=3, column=1, sticky='nswe')

        frame.treeview.column('#0', width=100)
        frame.treeview.column('quote', width=100)
        frame.treeview.column('alert', width=150)
        frame.treeview.heading('#0', text='Nome')
        frame.treeview.heading('quote', text='Cotação')
        frame.treeview.heading('alert', text='Alerta registrado')
        #frame.treeview['yscrollcommand'] = frame.treeview_scrollbar.set

        # Widgets de adicionar e remover cotação
        frame = self.quotes_frame.quote_btns_frame
        frame.title_text = self.tk.Label(frame, text="Adicionar ou remover cotação")
        frame.separator = self.ttk.Separator(frame)
        frame.entry_text = self.tk.Label(frame, text="Nome da ação")
        frame.entry_textvar = self.tk.StringVar()
        frame.entry = self.tk.Entry(frame, textvariable=frame.entry_textvar)
        frame.add_btn = self.tk.Button(
            frame, command=self.add_quote_button_callback, text='Adicionar')
        frame.remove_btn = self.tk.Button(
            frame, command=self.remove_quote_button_callback, text='Remover')

        frame.title_text.grid(row=0, column=0)
        frame.separator.grid(row=1, column=0, sticky='we')
        frame.entry_text.grid(row=2, column=0)
        frame.entry.grid(row=3, column=0)
        frame.add_btn.grid(row=4, column=0)
        frame.remove_btn.grid(row=5, column=0)

        # Widgets de adicionar alerta de limite
        frame = self.quotes_frame.alert_btns_frame
        frame.title_text = self.tk.Label(frame, text="Adicionar alerta de limite")
        frame.separator = self.ttk.Separator(frame)
        frame.name_text = self.tk.Label(frame, text="Nome da ação")
        frame.name_textvar = self.tk.StringVar()
        frame.name_entry = self.tk.Entry(frame, textvariable=frame.name_textvar)
        frame.lower_text = self.tk.Label(frame, text="Preço mínimo")
        frame.lower_textvar = self.tk.StringVar()
        frame.lower_entry = self.tk.Entry(frame, textvariable=frame.lower_textvar)
        frame.upper_text = self.tk.Label(frame, text="Preço máximo")
        frame.upper_textvar = self.tk.StringVar()
        frame.upper_entry = self.tk.Entry(frame, textvariable=frame.upper_textvar)
        frame.add_btn = self.tk.Button(frame, command=self.add_limit_alert_button_callback, text="Adicionar")

        frame.title_text.grid(row=0, column=0, columnspan=2)
        frame.separator.grid(row=1, column=0, columnspan=2, sticky='we')
        frame.name_text.grid(row=2, column=0)
        frame.name_entry.grid(row=2, column=1)
        frame.lower_text.grid(row=3, column=0)
        frame.lower_entry.grid(row=3, column=1)
        frame.upper_text.grid(row=4, column=0)
        frame.upper_entry.grid(row=4, column=1)
        frame.add_btn.grid(row=5, column=0, columnspan=2)

    def assemble_owned_stock_frame(self):
        """Monta o frame das ações possuidas (carteira)."""
        frame = self.owned_stock_frame
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        frame.title_text = self.tk.Label(frame, text="Carteira")
        frame.treeview = self.ttk.Treeview(frame, columns=('amount', 'value'))

        frame.title_text.grid(row=0, column=0)
        frame.treeview.grid(row=1, column=0, sticky='nswe')

        frame.treeview.column('#0', width=100)
        frame.treeview.column('amount', width=100)
        frame.treeview.column('value', width=150)
        frame.treeview.heading('#0', text='Nome')
        frame.treeview.heading('amount', text='Quantidade')
        frame.treeview.heading('value', text='Valor Total')

    def assemble_orders_frame(self):
        """Monta o frame com as ordens de compra e venda e widgets associados."""
        frame = self.orders_frame
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        frame.title_text = self.tk.Label(frame, text="Ordens de compra e venda ativas")
        frame.treeview = self.ttk.Treeview(
            frame, column=('price', 'amount', 'type', 'expiration'))
        frame.create_order_frame = self.tk.Frame(
            frame, relief=self.tk.RIDGE, borderwidth=3)

        frame.title_text.grid(row=0, column=0)
        frame.treeview.grid(row=1, column=0, sticky='nswe')
        frame.create_order_frame.grid(row=2, column=0)

        frame.treeview.column('#0', width=100)
        frame.treeview.column('price', width=100)
        frame.treeview.column('amount', width=100)
        frame.treeview.column('type', width=50)
        frame.treeview.column('expiration', width=150)
        frame.treeview.heading('#0', text='Nome')
        frame.treeview.heading('price', text='Preço')
        frame.treeview.heading('amount', text='Quantidade')
        frame.treeview.heading('type', text='Tipo')
        frame.treeview.heading('expiration', text='Expiração')

        # Widgets do frame de criar ordens
        frame = self.orders_frame.create_order_frame
        frame.title_text = self.tk.Label(frame, text="Criar ordem")
        frame.separator = self.ttk.Separator(frame)
        frame.name_text = self.tk.Label(frame, text="Nome da ação")
        frame.name_textvar = self.tk.StringVar()
        frame.name_entry = self.tk.Entry(frame, textvariable=frame.name_textvar)
        frame.price_text = self.tk.Label(frame, text="Preço")
        frame.price_textvar = self.tk.StringVar()
        frame.price_entry = self.tk.Entry(frame, textvariable=frame.price_textvar)
        frame.amount_text = self.tk.Label(frame, text="Quantidade")
        frame.amount_textvar = self.tk.StringVar()
        frame.amount_entry = self.tk.Entry(frame, textvariable=frame.amount_textvar)
        frame.expiration_text = self.tk.Label(frame, text="Expiração (minutos)")
        frame.expiration_textvar = self.tk.StringVar()
        frame.expiration_entry = self.tk.Entry(frame, textvariable=frame.expiration_textvar)
        frame.type_radio_var = self.tk.StringVar()
        frame.buy_radio = self.tk.Radiobutton(
            frame, text='Compra', var=frame.type_radio_var, value=OrderType.BUY.value)
        frame.sell_radio = self.tk.Radiobutton(
            frame, text='Venda', var=frame.type_radio_var, value=OrderType.SELL.value)
        frame.add_btn = self.tk.Button(frame, command=self.add_order, text="Criar")

        frame.title_text.grid(row=0, column=0, columnspan=4)
        frame.separator.grid(row=1, column=0, columnspan=4, sticky='we')
        frame.name_text.grid(row=2, column=0)
        frame.name_entry.grid(row=2, column=1)
        frame.price_text.grid(row=3, column=0)
        frame.price_entry.grid(row=3, column=1)
        frame.amount_text.grid(row=2, column=2)
        frame.amount_entry.grid(row=2, column=3)
        frame.expiration_text.grid(row=3, column=2)
        frame.expiration_entry.grid(row=3, column=3)
        frame.buy_radio.grid(row=4, column=0, columnspan=2)
        frame.sell_radio.grid(row=4, column=2, columnspan=2)
        frame.add_btn.grid(row=5, column=0, columnspan=4)

    def assemble_messages_frame(self):
        """Monta o frame das mensagens."""
        frame = self.messages_frame
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        frame.title_text = self.tk.Label(frame, text="Mensagens")
        frame.textbox = self.tk.Text(frame, state='disable')
        frame.scrollbar = self.tk.Scrollbar(frame)

        frame.title_text.grid(row=0, column=0, columnspan=2)
        frame.textbox.grid(row=1, column=0, sticky='nswe')
        frame.scrollbar.grid(row=1, column=1, sticky='ns')

        frame.textbox['yscrollcommand'] = frame.scrollbar.set

    def create_popup_user_name(self):
        """Cria a popup que pergunta o nome de usuário."""
        self.popup = self.tk.Toplevel()
        self.popup.title('')
        self.popup.focus_force()

        self.popup.label_prompt = self.tk.Label(self.popup, text="Insira o nome de usuario")
        self.popup.label_prompt.grid(row=0, column=0)

        self.popup.entry_text = self.tk.StringVar()
        self.popup.entry_text.set('')

        self.popup.entry = self.tk.Entry(self.popup, textvariable=self.popup.entry_text)
        self.popup.entry.grid(row=1, column=0)

        self.popup.ok_button = self.tk.Button(self.popup, text='OK', command=self.register_user_name)
        self.popup.ok_button.grid(row=2, column=0)

    def register_user_name(self):
        """
        Envia o nome de usuário para o servidor e pega o estado atual do cliente.
        
        Callback do botão do popup de registrar nome de usuário.
        """
        self.app.homebroker._pyroClaimOwnership()
        name = self.popup.entry_text.get()
        error_code = self.app.homebroker.add_client(self.app.uri, name)
        # A serialização de Enum no Pyro é o seu `value` 
        error_code = HomebrokerErrorCode(error_code)

        # Se o nome inserido não é permitido, fecha a aplicação
        if error_code is HomebrokerErrorCode.FORBIDDEN_NAME:
            self.popup.entry.grid_forget()
            self.popup.label_prompt['text'] = 'Nome não permitido'
            self.popup.ok_button['command'] = self.close
            return

        # Registra o nome escolhido na aplicação
        self.app.name = name

        # Fecha o popup e mostra a janela principal
        self.popup.destroy()
        self.popup = None
        self.main_window.deiconify()

        # Pega o estado inicial do cliente com o servidor e coloca na gui
        with self.update_lock:
            quotes, orders, owned_stock, alerts = (
                self.app.homebroker.get_client_status(self.app.name))

            self.quotes = quotes
            for ticker in self.quotes:
                self.quotes_frame.treeview.insert(
                    '', 'end', ticker,
                    text=ticker,
                    values=(self.quotes[ticker], ''))
            self.active_orders = orders
            self.owned_stock = owned_stock
            for ticker in alerts:
                insert_limit_alert_in_treeview(ticker, alerts[ticker][0], alerts[ticker])


    def add_quote(self, ticker: str):
        """
        Tenta adicionar uma ação na lista de interesses de cotações.
        Se conseguir, passa a mostrar sua cotação na GUI.
        Se der erro, mostra uma mensagem.

        Se conseguir adicionar, limpa as Entry.
        """
        with self.update_lock:
            if not ticker or ticker in self.quotes:
                return
            error_code = self.app.add_stock_to_quotes(ticker)
            if error_code is not HomebrokerErrorCode.SUCCESS:
                self.insert_error_message(ticker, error_code)
                return
            self.quotes[ticker] = None
            self.quotes_frame.treeview.insert('', 'end', ticker, text=ticker, values=('', ''))
        self.quotes_frame.quote_btns_frame.entry_textvar.set('')
        # Precisa atualizar as cotações para ter algum valor pra mostrar
        self.update_quotes()

    def add_quote_button_callback(self):
        """Callback do botão de adicionar ação a lista de cotações. Chama `add_quote()`."""
        ticker = self.quotes_frame.quote_btns_frame.entry_textvar.get().upper()
        self.add_quote(ticker)

    def remove_quote_button_callback(self):
        """
        Tenta remover uma ação na lista de interesses de cotações.
        Se conseguir, deixa de mostrar sua cotação na GUI.
        Se der erro, mostra uma mensagem.

        Se conseguir remover, limpa as Entry.
        """
        ticker = self.quotes_frame.quote_btns_frame.entry_textvar.get().upper()
        if ticker in self.owned_stock:
            self.insert_message("Não pode remover cotação de ação possuída.")
            return
        with self.update_lock:
            if not ticker or ticker not in self.quotes:
                return
            error_code = self.app.remove_stock_from_quotes(ticker)
            if error_code is not HomebrokerErrorCode.SUCCESS:
                self.insert_error_message(ticker, error_code)
                return
            self.quotes.pop(ticker)
            self.quotes_frame.treeview.delete(ticker)
        self.quotes_frame.quote_btns_frame.entry_textvar.set('')

    def update_quotes(self):
        """
        Atualiza a cotação das ações na lista de cotações.
        Chamado quando o usuário aperta o botão.
        """
        with self.update_lock:
            self.quotes = self.app.get_current_quotes()
            for ticker in self.quotes:
                values = list(self.quotes_frame.treeview.item(ticker)['values'])
                values[0] = self.quotes[ticker]
                self.quotes_frame.treeview.item(ticker, values=values)

    def add_limit_alert_button_callback(self):
        """
        Tentar registrar um alerta de limites de ganho e perda com o servidor.
        Se conseguir, passa a mostrar os limites na GUI.
        Se der erro, mostra uma mensagem.

        Callback do botão de adicionar alerta de limites.
        """
        # Pega o nome da ação e verifica se é valido
        ticker = self.quotes_frame.alert_btns_frame.name_textvar.get().upper()
        if not ticker or ticker not in self.quotes:
            return

        # Pega os valores dos limites, verificando se são válidos
        limit_count = 0
        lower = self.quotes_frame.alert_btns_frame.lower_textvar.get()
        if not lower:
            lower = None
        else:
            try:
                lower = float(lower)
            except ValueError:
                return
            else:
                limit_count += 1
        upper = self.quotes_frame.alert_btns_frame.upper_textvar.get()
        if not upper:
            upper = None
        else:
            try:
                upper = float(upper)
            except ValueError:
                return
            else:
                limit_count += 1
        if not limit_count:
            return

        with self.update_lock:
            # Envia para o servidor
            error_code = self.app.add_quote_alert(ticker, lower, upper)
            if error_code is not HomebrokerErrorCode.SUCCESS:
                self.insert_error_message(ticker, error_code)
                return
            # Passa a mostrar na GUI
            self.insert_limit_alert_in_treeview(ticker, lower, upper)

        self.quotes_frame.alert_btns_frame.name_textvar.set('')
        self.quotes_frame.alert_btns_frame.lower_textvar.set('')
        self.quotes_frame.alert_btns_frame.upper_textvar.set('')

    def add_order(self):
        """
        Tenta criar uma ordem de compra e venda.
        Se conseguir mostra na GUI.
        Se der erro, mostra uma mensagem.

        Callback do botão de criar ordem.
        """
        # Pega os valores das entries
        ticker = self.orders_frame.create_order_frame.name_textvar.get().upper()
        price = self.orders_frame.create_order_frame.price_textvar.get()
        amount = self.orders_frame.create_order_frame.amount_textvar.get()
        expiration = self.orders_frame.create_order_frame.expiration_textvar.get()
        order_type = self.orders_frame.create_order_frame.type_radio_var.get()
        # Checa se todas as caixa estão preenchidas
        if not ticker or not price or not amount or not expiration or not order_type:
            return
        
        # Checa se os valores são validos
        try:
            price = float(price)
            amount = float(amount)
            expiration = float(expiration)
        except ValueError:
            return
        if expiration <= 0:
            return

        order_type = OrderType(order_type)
        expiration = datetime.datetime.now() + datetime.timedelta(minutes=expiration)
        with self.update_lock:
            # Cria ordem no homebroker
            error_code, order = self.app.create_order(
                order_type, ticker, amount, price, expiration)
            if error_code is not HomebrokerErrorCode.SUCCESS:
                self.insert_error_message(ticker, error_code)
                return
            # Adiciona na lista de ordens
            self.active_orders.append(order)
            self.insert_order_in_treeview(order)

        # Limpa as entries
        self.orders_frame.create_order_frame.name_textvar.set('')
        self.orders_frame.create_order_frame.price_textvar.set('')
        self.orders_frame.create_order_frame.amount_textvar.set('')
        self.orders_frame.create_order_frame.expiration_textvar.set('')
        self.orders_frame.create_order_frame.type_radio_var.set('')

    def insert_order_in_treeview(self, order: Order):
        """Insere uma ordem na Treeview (tabela) das ordens."""
        self.orders_frame.treeview.insert(
            '', 'end',
            text=order.ticker,
            values=(
                str(order.price),
                str(order.amount),
                ('Compra' if order.type is OrderType.BUY else 'Venda'),
                order.expiry_date.strftime(self.datetime_format)
            )
        )

    def insert_limit_alert_in_treeview(self, ticker, lower_limit, upper_limit):
        """Insere um alerta de limite no campo correto da Treeview (tabela) de cotações."""
        values = list(self.quotes_frame.treeview.item(ticker)['values'])
        values[1] = str((lower_limit, upper_limit))
        self.quotes_frame.treeview.item(ticker, values=values)

    def notify_limit(self, ticker: str, current_value: float):
        """Notifica a GUI que um limite foi atingido."""
        with self.update_lock:
            self.notified_alerts[ticker] = current_value

    def notify_order(self,
                     transactions: Sequence[Transaction],
                     active_orders: Sequence[Order],
                     expired_orders: Sequence[str],
                     owned_stock: Mapping[str, float]):
        """
        Notifica a GUI dos eventos sobre ordens (transações e ordens expiradas),
        além de atualizar a carteira e as ordens ativas.
        """
        # Mostra uma mensagem para cada transação
        for transaction in transactions:
            self.insert_message((
                f"Transação executada: "
                f"{'Vendeu ' if transaction.seller_name == self.app.name else 'Comprou '}"
                f"{transaction.amount} ações de {transaction.ticker} por "
                f"{transaction.price} cada em "
                f"{transaction.datetime.strftime(self.datetime_format)}."
            ))

        for ticker in expired_orders:
            self.insert_message(f"Uma ordem de {ticker} expirou.")

        with self.update_lock:
            self.active_orders = active_orders
            self.owned_stock = owned_stock

    def insert_message(self, message: str):
        """Insere uma mensagem nova na caixa de texto de mensagens."""
        self.messages_frame.textbox['state'] = 'normal'
        self.messages_frame.textbox.insert('1.0', '\n')
        self.messages_frame.textbox.insert(
            '1.0',
            f"{datetime.datetime.now().strftime(self.datetime_format)} - {message}"
        )
        self.messages_frame.textbox['state'] = 'disable'

    def insert_error_message(self, ticker: str, error_code: HomebrokerErrorCode):
        """Insere uma mensagem de erro na caixa de texto de mensagens."""
        self.insert_message(f'{ticker}: {self.error_messages[error_code]}')

    def close(self):
        self.main_window.destroy()
        self.app.running = False
