import threading

class ClientGui(threading.Thread):
    def __init__(self, app, *args, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)
        self.start()

    def run(self):
        import tkinter as tk
        self.main_window = tk.Tk()
        self.main_window.protocol("WM_DELETE_WINDOW", self.close)

        self.owned_stock_frame = tk.Frame(self.main_window)
        self.quotes_frame = tk.Frame(self.main_window)
        self.orders_frame = tk.Frame(self.main_window)

        self.owned_stock_frame.grid(column=0, row=0)
        self.quotes_frame.grid(column=1, row=0)
        self.orders_frame.grid(column=2, row=0)

        self.create_popup_name()

        self.main_window.mainloop()

    def create_popup_name(self):
        popup = tk.Toplevel()
        popup.focus_force()
        label_prompt = tk.Label(popup, text="Insira o nome de usuario")
        label_prompt.grid(row=0, column=0)
        entry_text = tk.StringVar()
        entry_text.set('')
        entry = tk.Entry(popup, textvariable=entry_text)
        entry.grid(row=1, column=0)

        def register_user_name():
            nonlocal entry_text
            nonlocal self
            nonlocal popup
            name = entry_text.get()
            self.app.name = name
            self.app.homebroker.add_client(self.app.uri, name)
            popup.destroy()

        ok_button = tk.Button(popup, text='OK', command=register_user_name)
        ok_button.grid(row=2, column=0)


    def close(self):
        self.main_window.destroy()
        self.app.running = False
