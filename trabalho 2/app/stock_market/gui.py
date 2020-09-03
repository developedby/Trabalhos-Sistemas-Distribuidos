import threading


class StockMarketGui(threading.Thread):
    def __init__(self, app, *args, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)
        self.start()

    def run(self):
        # Tkinter é chato e só deixa usar na mesma thread em que foi importado
        import tkinter as tk
        self.main_window = tk.Tk()
        self.main_window.protocol("WM_DELETE_WINDOW", self.close)
        self.main_window.mainloop()

    def close(self):
        self.main_window.destroy()
        self.app.running = False
    
