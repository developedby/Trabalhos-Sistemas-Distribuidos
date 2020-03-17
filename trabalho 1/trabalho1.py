import json
import socket
import tkinter as tk

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat

class MulticastNewsPeer:
    def __init__(self):
        self.private_key = dsa.generate_private_key(
            key_size=1024,
            backend=default_backend()
        )

        self.unicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.unicast_socket.bind('', 0)
        self.active_sockets = []

        self.connected_peers = []

        self.window = tk.Tk('Multicast News')
        self.window.frame_news = tk.Frame(self.window)
        self.window.frame_options = tk.Frame(self.window)

        self.window.mainloop()

    def send_news(self, news_data):
        signature = private_key.sign(news_data, hashes.SHA512())
        msg = bytes(json.dumps({'data': news_data, 'signature': signature}), 'utf-8')
        
        for sock in self.active_sockets:
            sock.sendto(msg, sock.getsockname())

    def ack_new_peer(self, new_peer_addr, new_peer_key):
        self.connected_peers.append({
            'key': load_pem_public_key(
                new_peer_key,
                backend=default_backend
            ),
            'address': new_peer_addr
        })

        self.unicast_socket.sendto(
            self.private_key.public_key().public_bytes(
                Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
            )
        )

    def join_group(self, address):
        for sock in self.active_sockets:
            if sock.getsockname() == address:
                # TODO: Grupo repetido. Manda algum erro
                return
        self.active_sockets.append(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        )
        self.active_sockets[-1].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.active_sockets[-1].setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        mreq = struct.pack("4sl", socket.inet_aton(address[0]), socket.INADDR_ANY)
        self.active_sockets[-1].setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.active_sockets[-1].bind(address)

if __name__ == "__main__":
    MulticastNewsPeer()