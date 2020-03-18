import queue
import socket
import struct
import sys
import threading
import tkinter as tk

ADDRESS = ('228.5.1.0', 5000)

def threadReceive(*args):
    sock = args[0]
    msg_queue = args[1]
    del args

    while True:
        msg, sender = sock.recvfrom(10240)
        msg_queue.put({
            'data': msg.decode('UTF-8'),
            'addr': sender[0]})

def get_msg_from_queue(msg_queue, text_widget, root):
    while not msg_queue.empty():
        try:
            msg = msg_queue.get(block=False)
        except queue.Empty:
            print("Ue queue ta vazia")
            break
        else:
            text_widget.insert(
                tk.END,
                '\n{}: {}'.format(msg['addr'], msg['data']))
    root.after(50, get_msg_from_queue, *(msg_queue, text_widget, root))


def send_msg(input_var, sock, addr):
    msg = input_var.get()
    input_var.set('')
    sock.sendto(bytes(msg, 'utf-8'), addr)

def main():
    root = tk.Tk()
    chat_widget = tk.Text(root)
    input_var = tk.StringVar()
    input_widget = tk.Entry(root, textvariable=input_var)
    chat_widget.grid(row=0, column=0)
    input_widget.grid(row=1, column=0)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(ADDRESS)
    mreq = struct.pack("4sl", socket.inet_aton(ADDRESS[0]), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    input_widget.bind('<Return>', lambda _: send_msg(input_var, sock, ADDRESS))
    
    msg_queue = queue.Queue()

    th_rcv_obj = threading.Thread(
        target=threadReceive,
        args=(sock, msg_queue),
        daemon=True)

    th_rcv_obj.start()
    get_msg_from_queue(msg_queue, chat_widget, root)

    root.mainloop()

if __name__ == '__main__':
    main()
