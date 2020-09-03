import threading
import tkinter as tk


class ClientGui(threading.Thread):
    def __init__(self):
        self.main_window = tk.Tk()

    def run(self):
        self.main_window.mainloop()