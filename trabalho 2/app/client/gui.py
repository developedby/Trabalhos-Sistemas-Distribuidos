import threading

import Pyro5.api as pyro

from ..enums import HomebrokerErrorCode, OrderType

class ClientGui(threading.Thread):
    def __init__(self, app, update_period: int = 500, *args, **kwargs):
        # Referencia a classe Client
        self.app = app

        # Variaveis pra comunicar mudancas para a gui
        self.update_period = update_period
        self.update_lock = threading.Lock()
        self.quotes = {}
        self.alerts = {}
        self.owned_stock = {}
        self.active_orders = {}
        self.new_messages = []

        super().__init__(*args, **kwargs)
        self.start()

    def run(self):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.ttk = ttk
        self.main_window = self.tk.Tk()
        self.main_window.withdraw()
        self.main_window.title("Cliente Homebroker")
        self.main_window.protocol("WM_DELETE_WINDOW", self.close)
        self.assemble_main_window()

        self.create_popup_user_name()

        self.main_window.after(self.update_period, self.update_gui)

        self.main_window.mainloop()

    def update_gui(self):
        """
        Atualiza a interface gráfica periodicamente
        com as informações enviadas pela aplicação.
        """
        with self.update_lock:
            self.main_window.after(self.update_period, self.update_gui)

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
        frame.entry = self.tk.Entry(frame)
        frame.add_btn = self.tk.Button(
            frame, command=self.add_quote, text='Adicionar')
        frame.remove_btn = self.tk.Button(
            frame, command=self.remove_quote, text='Remover')

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
        frame.add_btn = self.tk.Button(frame, command=self.add_alert, text="Adicionar")

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
        """Monta o frame das ações possuidas."""
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
        frame.treeview = self.ttk.Treeview(frame, column=('price', 'amount', 'expiration'))
        frame.create_order_frame = self.tk.Frame(frame, relief=self.tk.RIDGE, borderwidth=3)

        frame.title_text.grid(row=0, column=0)
        frame.treeview.grid(row=1, column=0, sticky='nswe')
        frame.create_order_frame.grid(row=2, column=0)

        frame.treeview.column('#0', width=100)
        frame.treeview.column('price', width=100)
        frame.treeview.column('amount', width=100)
        frame.treeview.column('expiration', width=150)
        frame.treeview.heading('#0', text='Nome')
        frame.treeview.heading('price', text='Preço')
        frame.treeview.heading('amount', text='Quantidade')
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
        self.app.homebroker._pyroClaimOwnership()
        name = self.popup.entry_text.get()
        error_code = self.app.homebroker.add_client(self.app.uri, name)
        error_code = HomebrokerErrorCode(error_code)
        if error_code is HomebrokerErrorCode.FORBIDDEN_NAME:
            self.popup.entry.grid_forget()
            self.popup.label_prompt['text'] = 'Nome não permitido'
            self.popup.ok_button['command'] = self.close
        else:
            self.app.name = name
            self.main_window.deiconify()
            self.popup.destroy()
            self.popup = None

    def add_quote(self):
        pass

    def remove_quote(self):
        pass

    def update_quotes(self):
        pass

    def add_alert(self):
        pass

    def add_order(self):
        pass

    def close(self):
        self.main_window.destroy()
        self.app.running = False
