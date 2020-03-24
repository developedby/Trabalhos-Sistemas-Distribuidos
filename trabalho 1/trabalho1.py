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
from cryptography.exceptions import InvalidSignature

# TODO: Pensar em como fazer o sistema de reputação.
# Aspectos que seriam interessantes:
#   Considerar a opinião de todos os pares
#   Desconsiderar a opinião de pares que parecem ser maliciosos
#   Classificar a gravidade da noticia falsa
#   Considerar o historico de quem ja mandou
#   Perdoar ao longo do tempo
#   Considerar a proporção de falsas e não falsas, mas prevenindo spam
#   Dar mais peso quando eu também considero a noticia como falsa

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

        # Lista dos pares conectados, contendo inclusive a propria aplicacao
        self.connected_peers = {
            self.uni_sock.getsockname(): ConnectedPeer(
                key=self.public_key_encoded,
                addr=self.uni_sock.getsockname()
            )
        }

        # ID da próxima noticia a ser enviada
        self.next_news_id = 0

        self.window = tk.Tk()
        self.window.title('Multicast News')
        self.window.frame_news = tk.Frame(self.window)
        self.window.frame_options = tk.Frame(self.window)
        # TODO: Fazer a interface e ligar aos metodos relevantes

        self.window.mainloop()

    def listen_multicast(self, sock):
        # TODO: Fazer um esquema pra fechar a thread quando a socket é fechada
        while True:
            msg = sock.recv(1024)
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError:
                # TODO: Manda algum aviso
                pass

            try:
                sender_addr = msg['address']
            except KeyError:
                # TODO: Manda um aviso
                return

            # Verifica se é um join
            if 'key' in msg:
                self.ack_new_peer(sender_addr, msg['key'])
            # Verifica se é notícia
            if 'news' in msg and 'signature' in msg:
                self.decode_news(msg['news'], msg['signature'], msg['address'])
            if 'alert' in msg and 'signature' in msg:
                self.decode_fake_news_alert(
                    msg['alert'], msg['signature'], msg['address']
                )
            # Pode ser join, noticia ou alerta de fake news
            # TODO: Decidir como passa a mensagem pra frente no programa

    def ack_new_peer(self, new_peer_addr, new_peer_key):
        """
        Adiciona um novo par que se conectou a uma das redes.
        Envia ao novo par a chave publica.

            :param new_peer_addr: Endereço (ip, porta) do novo par.
            :param new_peer_key: Chave publica para verificar a assinatura das mensagens do novo par.
                No formato PEM.
        """
        # TODO: Tem que poder atualizar o endereço de um par que ja tinha conectado
        self.connected_peers[new_peer_addr] = ConnectedPeer(new_peer_key, new_peer_addr)
        self.uni_sock.sendto(
            bytes(json.dumps({'key': self.public_key_encoded})),
            new_peer_addr
        )

    def decode_news(self, data, signature, addr):
        """A"""
        sender = None
        if addr in self.connected_peers:
            sender = self.connected_peers[addr]
        # Se quem enviou a noticia não é um par conectado
        else:
            # TODO: Manda um aviso
            return
        # Verifica se a assinatura é a certa
        try:
            sender.key.verify(signature, data, hashes.SHA512())
        except InvalidSignature:
            # TODO: Manda um aviso
            return
        # Extrae a notícia
        try:
            news = json.loads(data)
        except json.JSONDecodeError:
            # TODO: Manda um aviso
            return
        sender.add_news(news['text'], news['id'])

        # TODO: Mostra a noticia na GUI

    def decode_fake_news_alert(self, alert_data, signature, alerter_addr):
        """
        Decodifica um alerta de que uma noticia é falsa.
        Se o par que enviou a noticia dita falsa é desconhecido
        ou se a noticia é desconhecida, ignora o alerta.
        Caso contrário, recalcula a reputação de quem enviou a noticia dita falsa

            :param alert_data: Serialização binaria da mensagem de alerta.
            :param signature: Assinatura digital de quem enviou o alerta.
                Verificada contra alert_data.
            :param alerter_addr: Endereço de quem enviou o aviso.
        """
        try:
            alert = json.loads(alert_data)
        except json.JSONDecodeError:
            # TODO: manda um aviso
            return

        if (alerter_addr not in self.connected_peers
            or alert['address'] not in self.connected_peers
            or alert['id'] not in self.connected_peers[alert['address']].news
        ):
            # TODO: Manda um aviso?
            return

        # TODO: Fazer um algoritmo melhor de reputação
        self.connected_peers[alert['address']].reputation -= 1        

    def listen_unicast(self):
        """Fica escutando por mensagens no socket unicast."""
        # TODO: Fazer um esquema pra fechar a thread quando a socket é fechada
        while True:
            # Espera receber mensagem
            msg, sender_addr = self.uni_sock.recvfrom(1024)

            # Decodifica a mensagem
            # Por enquanto, a unica coisa que recebe é chave de quem já esta na rede
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError:
                # TODO: Mostrar um erro
                pass
            try:
                sender_key = msg['key']
            except KeyError:
                # TODO: Manda um aviso
                pass

            # Adiciona o par à lista de conectados
            # Se já estava conectado, atualiza para a chave enviada
            if sender_addr in self.connected_peers:
                self.connected_peers[sender_addr].key = sender_key
            else:
                self.connected_peers[sender_addr] = ConnectedPeer(sender_key, sender_addr)

    def send_news(self, news_text):
        """
        Envia uma noticia para todos os grupos em que esta conectado.
        
            :param news_text: O texto da notícia a ser enviada.
        """
        news_data = bytes(json.dumps({
            'text': news_text,
            'id': self.next_news_id,
        }), 'utf-8')
        # TODO: Ver se precisa poder escolher pra qual grupo mandar a noticia
        signature = self.private_key.sign(news_data, hashes.SHA512())
        msg = bytes(json.dumps({
            'news': news_data,
            'signature': signature,
            'address': self.uni_sock.getsockname()
        }), 'utf-8')
        
        for sock in self.multi_socks:
            sock.sendto(msg, sock.getsockname())

    def alert_fake_news(self, addr, id, reason):
        """
        Envia um alerta que uma certa noticia é falsa.

            :param addr: Endereço de quem enviou a noticia falsa.
            :param id: Id da notícia falsa.
            :param reason: Mensagem com a justificativa de porque é falsa.
        """
        alert_data = bytes(json.dumps({
            'id': id,
            'address': addr,
            'reason': reason,
        }), 'utf-8')

        signature = self.private_key.sign(alert_data, hashes.SHA512())

        msg = bytes(json.dumps({
            'alert': alert_data,
            'signature': signature,
            'address': self.uni_sock.getsockname()
        }), 'utf-8')

        for sock in self.multi_socks:
            sock.sendto(msg, sock.getsockname())

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
        self.news = {}

    def add_news(self, text, id):
        if id in self.news:
            raise IndexError(f"Id {id} da notícia é repetido")
        # TODO: Muito ineficiente, calcular um hash ou algo parecido
        if text in self.news.values():
            raise ValueError(f"Notícia já existe com outro id")
        self.news[id] = text

if __name__ == "__main__":
    MulticastNewsPeer()