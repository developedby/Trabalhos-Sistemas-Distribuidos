"""
Esta aplicação é um sistema de envio de notícias.
As notícias são enviadas por multicast e assinadas usando DSA.
É possível entrar em multiplos grupos multicast.
A aplicação também permite marcar notícias como sendo falsas.
Mantém um score de reputação baseado no numero de noticias falsas.
"""

import json
import socket
import threading
import tkinter as tk

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat

# TODO: Pensar em como fazer o sistema de reputação.
# Aspectos que seriam interessantes:
#   Considerar a opinião de todos os pares
#   Desconsiderar a opinião de pares que parecem ser maliciosos
#   Classificar a gravidade da noticia falsa
#   Considerar o historico de quem ja mandou
#   Perdoar ao longo do tempo
#   Considerar a proporção de falsas e não falsas, mas prevenindo spam

# TODO: Evitar a duplicação de mensagens.
# Checar sempre se o par já é conhecido e se essa mensagem já foi recebida
# Se aplica tanto para noticias quanto para entrada de pares e aviso de fake news

# TODO: Criar a estrutura das noticias
# Ex: (ID, texto)


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

        # Lista dos sockets multicast, um para cada grupo multicast conectado
        self.multi_socks = []

        # Socket unicast, um para toda a aplicação
        self.uni_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self.uni_sock.bind((socket.gethostbyname(socket.gethostname()), 0))
        # TODO: Iniciar a thread do socket unicast

        # Lista dos pares conectados, contendo 
        self.connected_peers = []

        self.window = tk.Tk()
        self.window.title('Multicast News')
        self.window.frame_news = tk.Frame(self.window)
        self.window.frame_options = tk.Frame(self.window)
        # TODO: Fazer a interface e ligar aos metodos relevantes

        self.window.mainloop()

    def listen_multicast(self, sock):
        # TODO: Fazer um esquema pra fechar a thread quando a socket é fechada
        while True:
            msg, sender = sock.recvfrom(1024)
            # TODO: Decodificar a mensagem multicast
            # Pode ser join, noticia ou alerta de fake news
            # TODO: Decidir como passa a mensagem pra frente no programa

    def listen_unicast(self):
        # TODO: Fazer um esquema pra fechar a thread quando a socket é fechada
        while True:
            msg, sender = sock.recvfrom(1024)
            # TODO: Decodificar a mensagem unicast (chave de pares nos grupos)
            # TODO: Conectar ao par, verificando se ja existe, atualizando nesse caso
        pass

    def send_news(self, news_data):
        """
        Envia uma noticia para todos os grupos em que esta conectado.
        
            :param news_data: A noticia a ser enviada, em bytes.
        """
        # TODO: Ver se precisa poder escolher pra qual grupo mandar a noticia
        signature = self.private_key.sign(news_data, hashes.SHA512())
        msg = bytes(json.dumps({'data': news_data, 'signature': signature}), 'utf-8')
        
        for sock in self.multi_socks:
            sock.sendto(msg, sock.getsockname())

    def ack_new_peer(self, new_peer_addr, new_peer_key):
        """
        Adiciona um novo par que se conectou a uma das redes.
        Envia ao novo par a chave publica.

            :param new_peer_addr: Endereço (ip, porta) do novo par.
            :param new_peer_key: Chave publica para verificar a assinatura das mensagens do novo par.
                No formato PEM.
        """
        # TODO: Tem que poder atualizar o endereço de um par que ja tinha conectado
        self.connected_peers.append(ConnectedPeer(new_peer_key, new_peer_addr))
        self.uni_sock.sendto(
            bytes(json.dumps({'key': self.public_key_encoded})),
            new_peer_addr
        )

        #deveria ser
        # for peer in self.connected_peers:
        #     self.uni_sock.sendto(
        #         bytes(json.dumps({'key': peer.key})),
        #         new_peer_addr
        # )
        # self.connected_peers.append(ConnectedPeer(new_peer_key, new_peer_addr))

    def join_group(self, addr):
        """
        Entra em um novo grupo multicast.
        Abre um socket multicast com o endereço.
        Envia a chave publica para o grupo.

            :param addr: Endereço (ip, porta) do grupo.
        """
        # Checa se ja não está no grupo
        for sock in self.multi_socks:
            if sock.getsockname() == addr:
                # TODO: Grupo repetido. Manda algum erro
                return
        # Cria um novo socket multiacst com o endereço do novo grupo
        # TODO: Checar se não é possivel usar 1 socket para todos os grupos
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.multi_socks.append(
            socket.socket(new_socket)
        )
        new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        new_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        mreq = struct.pack("4sl", socket.inet_aton(addr[0]), socket.INADDR_ANY)
        new_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        new_socket.bind(addr)

        # Começa a thread que fica escutando nesse socket
        # TODO: Fazer a thread que escuta multicast

        # Envia a chave publica e o endereço
        new_socket.sendto(
            bytes(json.dumps({
                'key': self.public_key_encoded,
                'address': self.uni_sock.getsockname()
            })),
            addr
        )

    def exit_group(self, addr):
        """
        Sai do grupo multicast.
        """
        # Checa se está no grupo
        sock_to_close = None
        for sock in self.multi_socks:
            if sock.getsockname() == addr:
                sock_to_close = sock
                break

        if sock_to_close:
            sock_to_close.close()
            self.multi_socks.remove(sock_to_close)
        else:
            # TODO: Cara nao encontrado no grupo
            pass

class ConnectedPeer:
    """
    Representa um par com quem se conectou em um dos grupos multicast.
    
        :param key: Chave publica do par, para verificar assinatura.
            No formato PEM.
        :param addr: Endereço (ip, porta) do par.
    """
    def __init__(self, key, addr):
        self.key = load_pem_public_key(key, backend=default_backend)
        self.addr = addr
        self.reputation = 0

if __name__ == "__main__":
    MulticastNewsPeer()