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

        self.main_window.mainloop()

    def close(self):
        self.main_window.destroy()
        self.app.running = False
