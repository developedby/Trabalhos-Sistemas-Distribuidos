"""
Esta aplicação é um sistema de envio de notícias.
As notícias são enviadas por multicast e assinadas usando DSA.
É possível entrar em multiplos grupos multicast.
A aplicação também permite marcar notícias como sendo falsas.
Mantém um score de reputação baseado no numero de noticias falsas.
"""

import json
import socket
import struct
import threading
import tkinter as tk
from tkinter import ttk

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
        self.multi_threads = []

        # Socket unicast, um para toda a aplicação
        self.uni_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self.uni_sock.bind((socket.gethostbyname(socket.gethostname()), 0))
        self.uni_thread = threading.Thread(target=self.listen_unicast)
        self.uni_thread.start()

        # Lista dos pares conectados, contendo inclusive a propria aplicacao
        self.connected_peers = {
            self.uni_sock.getsockname(): ConnectedPeer(
                key=self.public_key_encoded,
                addr=self.uni_sock.getsockname()
            )
        }

        # ID da próxima noticia a ser enviada
        self.next_news_id = 0

        self.create_gui()        

        self.window.mainloop()

    # Métodos para a gui
    def create_gui(self):
        print(self.connected_peers[self.uni_sock.getsockname()].key)
        print(type(self.connected_peers[self.uni_sock.getsockname()].key))
        teste = self.connected_peers[self.uni_sock.getsockname()]
        print(type(teste))
        print(teste.key)
        print(type(teste.key))
        """Cria a GUI"""
        self.window = tk.Tk()
        self.window.title('Multicast News')
        self.window.protocol("WM_DELETE_WINDOW", self.tk_on_closing)

        # Frames da janela principal
        self.window.frame_news = tk.Frame(
            self.window, relief=tk.RIDGE, borderwidth=3
        )
        self.window.frame_news.grid(row=0, column=0)
        self.window.frame_options = tk.Frame(self.window)
        self.window.frame_options.grid(row=0, column=1)

        # Widgets da parte do chat
        tk.Label(self.window.frame_news, text="Histórico de notícias")\
            .grid(row=0, column=0, columnspan=2)
        self.window.chat = tk.Text(self.window.frame_news, state='disabled')
        self.window.chat.grid(row=1, column=0)
        self.window.chat_scrollbar = tk.Scrollbar(
            self.window.frame_news
        )
        self.window.chat_scrollbar.grid(row=1, column=1, sticky='ns')
        self.window.chat['yscrollcommand'] = self.window.chat_scrollbar.set
        self.window.news_entry = self.create_entry(self.window.frame_news)
        self.window.news_entry.grid(row=2, column=0)
        self.window.send_news_btn = tk.Button(
            self.window.frame_news,
            command=self.send_news_btn_action,
            text="Enviar notícia"
        )
        self.window.send_news_btn.grid(row=3, column=0)

        # Frames do controle da aplicação
        self.window.frame_group = tk.Frame(
            self.window.frame_options, relief=tk.RIDGE, borderwidth=3
        )
        self.window.frame_group.grid(row=0, column=0)
        self.window.frame_fake_news = tk.Frame(
            self.window.frame_options, relief=tk.RIDGE, borderwidth=3
        )
        self.window.frame_fake_news.grid(row=1, column=0)

        # Widgets relacionados aos grupos multicast
        tk.Label(self.window.frame_group, text="Group IP")\
            .grid(row=0, column=0)
        self.window.group_ip_entry = self.create_entry(self.window.frame_group)
        self.window.group_ip_entry.grid(row=0, column=1)
        tk.Label(self.window.frame_group, text="Group port")\
            .grid(row=1, column=0)
        self.window.group_port_entry = self.create_entry(self.window.frame_group)
        self.window.group_port_entry.grid(row=1, column=1)
        self.window.join_group_btn = tk.Button(
            self.window.frame_group,
            command=self.join_group_btn_action,
            text="Join Group"
        )
        self.window.join_group_btn.grid(row=2, column=0)
        self.window.exit_group_btn = tk.Button(
            self.window.frame_group,
            command=self.exit_group_btn_action,
            text="Exit Group"
        )
        self.window.exit_group_btn.grid(row=2, column=1)
        # TODO: Arrumar
        self.window.connected_groups_frame = tk.Frame(self.window.frame_group)
        self.window.connected_groups_frame.grid(row=3, column=0, columnspan=2)
        tk.Label(self.window.connected_groups_frame, text='Grupos conectados:')\
            .grid(row=0, column=0, columnspan=2)
        self.window.group_treeview = ttk.Treeview(
            self.window.connected_groups_frame,
            columns=('IP', 'port')
        )
        self.window.group_treeview.heading('IP', text='IP')
        self.window.group_treeview.heading('port', text='port')
        self.window.group_treeview.grid(row=1, column=0)
        self.window.group_treeview_scrollbar = tk.Scrollbar(self.window.connected_groups_frame)
        self.window.group_treeview_scrollbar.grid(row=1, column=1, sticky='ns')
        self.window.group_treeview['yscrollcommand'] = \
            self.window.group_treeview_scrollbar.set

        # Widgets relacionados à fake news
        tk.Label(self.window.frame_fake_news, text="Fake news IP")\
            .grid(row=0, column=0)
        self.window.fake_news_ip_entry = self.create_entry(self.window.frame_fake_news)
        self.window.fake_news_ip_entry.grid(row=0, column=1)
        tk.Label(self.window.frame_fake_news, text="Fake news port")\
            .grid(row=1, column=0)
        self.window.fake_news_port_entry = self.create_entry(self.window.frame_fake_news)
        self.window.fake_news_port_entry.grid(row=1, column=1)
        tk.Label(self.window.frame_fake_news, text="Fake news id")\
            .grid(row=2, column=0)
        self.window.fake_news_id_entry = self.create_entry(self.window.frame_fake_news)
        self.window.fake_news_id_entry.grid(row=2, column=1)
        tk.Label(self.window.frame_fake_news, text="Fake news reason")\
            .grid(row=3, column=0)
        self.window.fake_news_reason_entry = self.create_entry(self.window.frame_fake_news)
        self.window.fake_news_reason_entry.grid(row=3, column=1)
        self.window.fake_news_alert_btn = tk.Button(
            self.window.frame_fake_news,
            command=self.fake_news_alert_btn_action,
            text="Send Alert"
        )
        self.window.fake_news_alert_btn.grid(row=4, column=0, columnspan=2)

    @staticmethod
    def create_entry(root):
        entry = tk.Entry(root)
        entry.var = tk.StringVar()
        entry['textvariable'] = entry.var
        return entry

    @staticmethod
    def is_valid_multicast_ipv4(ip):
        blocks = ip.split('.')
        if (len(blocks) != 4
            or not ((224 <= int(blocks[0]) <= 239)
                and (0 <= int(blocks[1]) <= 255)
                and (0 <= int(blocks[2]) <= 255)
                and (0 <= int(blocks[3]) <= 255)
            )
        ):
            return False
        else:
            return True
    
    def send_news_btn_action(self):
        """Envia a noticia escrita em news_entry para os grupos conectados"""
        self.send_news(self.window.news_entry.var.get())

    def join_group_btn_action(self):
        """
        Usa o valor das entries pra tentar entrar no grupo.
        Chamado quando o usuario pressiona join_group_btn
        """
        ip = self.window.group_ip_entry.var.get()
        if not self.is_valid_multicast_ipv4(ip):
            return
        try:
            port = int(self.window.group_port_entry.var.get())
        except ValueError:
            return

        self.join_group((ip, port))

    def exit_group_btn_action(self):
        """
        Usa o valor das entries pra tentar sair do grupo.
        Chamado quando o usuario pressiona exit_group_btn
        """
        ip = self.window.group_ip_entry.var.get()
        if not self.is_valid_multicast_ipv4(ip):
            return
        try:
            port = int(self.window.group_port_entry.var.get())
        except ValueError:
            return

        self.exit_group((ip, port))

    def fake_news_alert_btn_action(self):
        """
        Pega os valores das entries para tentar enviar um alerta de fake news.
        Chamado quando o usuário pressiona fake_news_alert_btn
        """
        ip = self.window.fake_news_ip_entry.var.get()
        if not self.is_valid_multicast_ipv4(ip):
            return

        try:
            port = int(self.window.fake_news_port_entry.var.get())
        except ValueError:
            return

        address = (ip, port)
        if address not in self.connected_peers:
            return

        peer = self.connected_peers[address]
        if id not in peer.news:
            return

        reason = self.window.fake_news_reason_entry.var.get()
        self.alert_fake_news(address, id, reason)

    def tk_on_closing(self):
        self.uni_sock.close()
        for sock in self.multi_socks:
            sock.close()
        self.window.destroy()

    # Métodos das outras coisas
    def listen_multicast(self, sock):
        # TODO: Fazer um esquema pra fechar a thread quando a socket é fechada
        print("Começando socket multicast no endereço", sock.getsockname())
        while True:
            msg = sock.recv(1024)
            print('recebeu mensagem:', msg)
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
                self.ack_new_peer(tuple(sender_addr), msg['key'].encode('latin-1'))
            # Verifica se é notícia
            if 'news' in msg and 'signature' in msg:
                self.decode_news(msg['news'], msg['signature'].encode('latin-1'), tuple(msg['address']))
            if 'alert' in msg and 'signature' in msg:
                self.decode_fake_news_alert(
                    msg['alert'], msg['signature'].encode('latin-1'), tuple(msg['address'])
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
        print('legal')
        print(type(self.connected_peers[new_peer_addr]))
        print(type(self.connected_peers[new_peer_addr].key))
        teste = None
        if new_peer_addr in self.connected_peers:
            teste = self.connected_peers[new_peer_addr]
        print(type(teste))
        print(teste.key)
        print(teste)
        print(new_peer_addr)
        self.uni_sock.sendto(
            bytes(json.dumps({'key': self.public_key_encoded.decode('latin-1')}), 'utf-8'),
            new_peer_addr
        )
        print('depois temos', teste.key)

    def decode_news(self, data, signature, addr):
        """
        Verifica se a noticia recebida é valida.
        Se for, adiciona para a lista de noticias e mostra na GUI.
        """
        print(data, signature, addr)

        sender = None
        if addr in self.connected_peers:
            sender = self.connected_peers[addr]
        # Se quem enviou a noticia não é um par conectado
        else:
            print("sender nao encontrado")
            # TODO: Manda um aviso
            return
        print('decodificou endereço. Sender é', sender)
        print(type(sender))
        print(type(sender.key))
        print(sender.key)

        # Verifica se a assinatura é a certa
        try:
            sender.key.verify(signature, data, hashes.SHA512())
        except InvalidSignature:
            print("assinatura zuou")
            # TODO: Manda um aviso
            return
        print('verificou a assinatura')

        # Extrae a notícia
        try:
            news = json.loads(data)
        except json.JSONDecodeError:
            print("nao conseguiu extrair a mensagem")
            # TODO: Manda um aviso
            return
        print('decodificou a noticia. é', news)

        sender.add_news(news['text'], news['id'])

        self.window.chat.insert('1.0', f"{addr} - {news['id']}: {news['text']}")

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
        print("Começando o socket unicast")
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
        news_data = json.dumps({
            'text': news_text,
            'id': self.next_news_id,
        })
        # TODO: Ver se precisa poder escolher pra qual grupo mandar a noticia
        signature = self.private_key.sign(bytes(news_data, 'latin-1'), hashes.SHA512())
        msg = bytes(json.dumps({
            'news': news_data,
            'signature': signature.decode('latin-1'),
            'address': self.uni_sock.getsockname()
        }), 'utf-8')
        
        for sock in self.multi_socks:
            sock.sendto(msg, sock.getsockname())
        print("enviou a noticia de id", self.next_news_id)
        self.next_news_id += 1

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
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#, socket.IPPROTO_UDP)
        self.multi_socks.append(new_socket)
        new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        new_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        mreq = struct.pack("4sl", socket.inet_aton(addr[0]), socket.INADDR_ANY)
        new_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        new_socket.bind(addr)

        # Começa a thread que fica escutando nesse socket
        self.multi_threads.append(
            threading.Thread(target=lambda: self.listen_multicast(new_socket))
        )
        self.multi_threads[-1].start()

        self.window.group_treeview.insert(
            '', 0, f"{addr[0]},{addr[1]}", text=addr[0], values=addr[1]
        )

        # Envia a chave publica e o endereço
        new_socket.sendto(
            bytes(json.dumps({
                'key': self.public_key_encoded.decode('latin-1'),
                'address': self.uni_sock.getsockname()
            }), 'utf-8'),
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

        self.window.group_treeview.delete(f"{addr[0]},{addr[1]}")

    def alert_fake_news(self, addr, id, reason):
        """
        Envia um alerta que uma certa noticia é falsa.

            :param addr: Endereço de quem enviou a noticia falsa.
            :param id: Id da notícia falsa.
            :param reason: Mensagem com a justificativa de porque é falsa.
        """
        alert_data = json.dumps({
            'id': id,
            'address': addr,
            'reason': reason,
        })

        signature = self.private_key.sign(bytes(alert_data, 'latin-1'), hashes.SHA512())

        msg = bytes(json.dumps({
            'alert': alert_data,
            'signature': signature.decode('latin-1'),
            'address': self.uni_sock.getsockname()
        }), 'utf-8')

        for sock in self.multi_socks:
            sock.sendto(msg, sock.getsockname())

class ConnectedPeer:
    """
    Representa um par com quem se conectou em um dos grupos multicast.
    
        :param key: Chave publica do par, para verificar assinatura.
            No formato PEM.
        :param addr: Endereço (ip, porta) do par.
    """
    def __init__(self, key, addr):
        self.key = load_pem_public_key(key, backend=default_backend())
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