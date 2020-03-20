"""
Esta aplicação é um sistema de envio de notícias.
As notícias são enviadas por multicast e assinadas usando DSA.
É possível entrar em multiplos grupos multicast.
A aplicação também permite marcar notícias como sendo falsas.
Mantém um score de reputação baseado no numero de noticias falsas.
"""

import json
import socket
import tkinter as tk

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat


class MulticastNewsPeer:
    """Implementa a aplicação"""
    def __init__(self):
        # Chave privada do dsa
        self.private_key = dsa.generate_private_key(
            key_size=1024,
            backend=default_backend()
        )
        # Chave publica do dsa, já codificada em PEM
        self.public_key_encoded = self.private_key.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        )

        self.active_sockets = []
        self.connected_peers = []

        self.window = tk.Tk('Multicast News')
        self.window.frame_news = tk.Frame(self.window)
        self.window.frame_options = tk.Frame(self.window)

        self.window.mainloop()

    def send_news(self, news_data):
        """
        Envia uma noticia para todos os grupos em que esta conectado
        
            :param news_data: A noticia a ser enviada, em bytes
        """
        signature = private_key.sign(news_data, hashes.SHA512())
        msg = bytes(json.dumps({'data': news_data, 'signature': signature}), 'utf-8')
        
        for sock in self.active_sockets:
            sock.sendto(msg, sock.getsockname())

    def multicast_public_key(self, sock):
        """
        Envia a chave publica para um grupo multicast
        
            :param sock: O socket multicast onde vai ser enviada a chave
        """
        addr = sock.getsockname()
        sock.sendto(bytes(json.dumps({'key': self.public_key_encoded})), addr)

    def unicast_public_key(self, sock, addr):
        """
        Envia a chave publica em unicast
        
            :param sock: Socket por onde vai ser enviada a chave
            :param addr: Endereço do remetente (ip, porta)
        """
        sock.sendto(bytes(json.dumps({'key': self.public_key_encoded})), addr)

    def ack_new_peer(self, sock, new_peer_addr, new_peer_key):
        """
        Adiciona um novo par que se conectou a uma das redes.
        Envia ao novo par a chave publica.

            :param sock: Socket que recebeu a mensagem do novo par.
                A resposta é enviada por esse socket.
            :param new_peer_addr: Endereço (ip, porta) do novo par.
            :param new_peer_key: Chave publica para verificar a assinatura das mensagens do novo par.
        """
        self.connected_peers.append({
            'key': load_pem_public_key(
                new_peer_key,
                backend=default_backend
            ),
            'address': new_peer_addr
        })
        self.unicast_public_key(sock, new_peer_addr)

    def join_group(self, addr):
        """
        Entra em um novo grupo.
        Abre um socket multicast com o endereço.
        Envia a chave publica para o grupo.

            :param addr: Endereço (ip, porta) do grupo.
        """
        # Checa se ja não está no grupo
        for sock in self.active_sockets:
            if sock.getsockname() == addr:
                # TODO: Grupo repetido. Manda algum erro
                return
        # Cria um novo socket multiacst com o endereço do novo grupo
        # TODO: Checar se não é possivel usar 1 socket para todos os grupos
        self.active_sockets.append(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        )
        # TODO: Acessar com -1 pode dar problema de concorrencia
        self.active_sockets[-1].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.active_sockets[-1].setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        mreq = struct.pack("4sl", socket.inet_aton(addr[0]), socket.INADDR_ANY)
        self.active_sockets[-1].setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.active_sockets[-1].bind(addr)

        # Começa a thread que fica escutando nesse socket
        # TODO: Como escutar os unicasts?

        # Envia a chave publica
        self.multicast_public_key(self.active_sockets[-1])

if __name__ == "__main__":
    MulticastNewsPeer()