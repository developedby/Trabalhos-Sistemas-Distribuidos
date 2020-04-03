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
import time
import tkinter as tk
from tkinter import ttk

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
from cryptography.exceptions import InvalidSignature


# TODO: Pensar em como melhorar o sistema de reputação.
# Aspectos que seriam interessantes:
#   Considerar a opinião de todos os pares
#   Desconsiderar a opinião de pares que parecem ser maliciosos
#   Classificar a gravidade da noticia falsa
#   Considerar o historico de quem ja mandou
#   Perdoar ao longo do tempo
#   Considerar a proporção de falsas e não falsas, mas prevenindo spam
#   Dar mais peso quando eu também considero a noticia como falsa


class MulticastNewsPeer:
    """
    Implementa a aplicação.
    Para rodar é preciso chamar start().
    """
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
        self.uni_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.uni_sock.bind((socket.gethostbyname(socket.gethostname()), 0))
        self.uni_thread = threading.Thread(target=self.listen_unicast, daemon=True)
        self.uni_thread.start()

        # Dicionario com os pares conectados
        # As chaves sãoi os endereços dos pares
        self.connected_peers = {}

        # ID da próxima noticia a ser enviada
        self.next_news_id = 0

    def start(self):
        """Roda o programa."""
        self.create_gui()

        # Adiciona o próprio programa como um par inicial
        # Tem que ser depois de criar a GUI para colocar como um item na lista de pares
        self.add_new_peer(self.uni_sock.getsockname(), self.public_key_encoded)

        # Roda o programa
        self.window.mainloop()

    # Métodos para a gui
    def create_gui(self):
        """Cria a GUI"""
        self.window = tk.Tk()
        self.window.title('Multicast News')
        self.window.protocol("WM_DELETE_WINDOW", self.tk_on_closing)

        # Frames da janela principal
        self.window.frame_news = tk.Frame(
            self.window, relief=tk.RIDGE, borderwidth=3
        )
        self.window.frame_news.grid(row=0, column=0, sticky='nsew')
        self.window.frame_options = tk.Frame(self.window)
        self.window.frame_options.grid(row=0, column=1, sticky='ns')
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        # Widgets da parte do chat
        self.window.frame_news.rowconfigure(1, weight=1)
        self.window.frame_news.columnconfigure(0, weight=1)
        tk.Label(self.window.frame_news, text="Histórico de notícias")\
            .grid(row=0, column=0, columnspan=2)
        self.window.chat = tk.Text(self.window.frame_news, state='disable')
        self.window.chat.grid(row=1, column=0, sticky='nsew')
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
        self.window.frame_group.grid(row=0, column=0, sticky='nsew')
        self.window.frame_fake_news = tk.Frame(
            self.window.frame_options, relief=tk.RIDGE, borderwidth=3
        )
        self.window.frame_fake_news.grid(row=1, column=0, sticky='nsew')
        self.window.frame_connected_peer = tk.Frame(
            self.window.frame_options, relief=tk.RIDGE, borderwidth=3
        )
        self.window.frame_connected_peer.grid(row=2, column=0, sticky='nsew')

        # Widgets relacionados aos grupos multicast
        self.window.frame_group.columnconfigure(0, weight=1)
        self.window.frame_group_entries = tk.Frame(self.window.frame_group)
        self.window.frame_group_entries.grid(row=0, column=0)
        self.window.frame_group_buttons = tk.Frame(self.window.frame_group)
        self.window.frame_group_buttons.grid(row=1, column=0)
        ttk.Separator(self.window.frame_group)\
            .grid(row=2, column=0, sticky='we')
        self.window.frame_connected_groups = tk.Frame(self.window.frame_group)
        self.window.frame_connected_groups.grid(row=3, column=0)
        # Frame Group Entries
        tk.Label(self.window.frame_group_entries, text="Group IP")\
            .grid(row=0, column=0)
        self.window.group_ip_entry = self.create_entry(self.window.frame_group_entries)
        self.window.group_ip_entry.grid(row=0, column=1)
        tk.Label(self.window.frame_group_entries, text="Group port")\
            .grid(row=1, column=0)
        self.window.group_port_entry = self.create_entry(self.window.frame_group_entries)
        self.window.group_port_entry.grid(row=1, column=1)
        # Frame Group Buttons
        self.window.join_group_btn = tk.Button(
            self.window.frame_group_buttons,
            command=self.join_group_btn_action,
            text="Join Group"
        )
        self.window.join_group_btn.grid(row=0, column=0)
        self.window.exit_group_btn = tk.Button(
            self.window.frame_group_buttons,
            command=self.exit_group_btn_action,
            text="Exit Group"
        )
        self.window.exit_group_btn.grid(row=0, column=1)
        # Frame Connected Groups
        tk.Label(self.window.frame_connected_groups, text='Grupos conectados:')\
            .grid(row=0, column=0, columnspan=2)
        self.window.group_treeview = ttk.Treeview(
            self.window.frame_connected_groups,
            columns=('port')
        )
        self.window.group_treeview.column('#0', width=130)
        self.window.group_treeview.column('port', width=60)
        self.window.group_treeview.heading('#0', text='IP')
        self.window.group_treeview.heading('port', text='port')
        self.window.group_treeview.grid(row=1, column=0)
        self.window.group_treeview_scrollbar = tk.Scrollbar(self.window.frame_connected_groups)
        self.window.group_treeview_scrollbar.grid(row=1, column=1, sticky='ns')
        self.window.group_treeview['yscrollcommand'] = \
            self.window.group_treeview_scrollbar.set

        # Widgets relacionados à fake news
        self.window.frame_fake_news.columnconfigure(0, weight=1)
        self.window.frame_fake_news_entries = tk.Frame(self.window.frame_fake_news)
        self.window.frame_fake_news_entries.grid(row=0, column=0)
        self.window.frame_fake_news_buttons = tk.Frame(self.window.frame_fake_news)
        self.window.frame_fake_news_buttons.grid(row=1, column=0)
        # Frame Fake News Entries
        tk.Label(self.window.frame_fake_news_entries, text="Fake news IP")\
            .grid(row=0, column=0)
        self.window.fake_news_ip_entry = self.create_entry(self.window.frame_fake_news_entries)
        self.window.fake_news_ip_entry.grid(row=0, column=1)
        tk.Label(self.window.frame_fake_news_entries, text="Fake news port")\
            .grid(row=1, column=0)
        self.window.fake_news_port_entry = self.create_entry(self.window.frame_fake_news_entries)
        self.window.fake_news_port_entry.grid(row=1, column=1)
        tk.Label(self.window.frame_fake_news_entries, text="Fake news id")\
            .grid(row=2, column=0)
        self.window.fake_news_id_entry = self.create_entry(self.window.frame_fake_news_entries)
        self.window.fake_news_id_entry.grid(row=2, column=1)
        tk.Label(self.window.frame_fake_news_entries, text="Fake news reason")\
            .grid(row=3, column=0)
        self.window.fake_news_reason_entry = self.create_entry(self.window.frame_fake_news_entries)
        self.window.fake_news_reason_entry.grid(row=3, column=1)
        # Frame Fake News Buttons
        self.window.fake_news_alert_btn = tk.Button(
            self.window.frame_fake_news_buttons,
            command=self.fake_news_alert_btn_action,
            text="Send Alert"
        )
        self.window.fake_news_alert_btn.grid(row=0, column=0)

        # Widgets da lista de pares conectados
        tk.Label(self.window.frame_connected_peer, text="Pares Conectados")\
            .grid(row=0, column=0, columnspan=2)
        self.window.peers_treeview = ttk.Treeview(
            self.window.frame_connected_peer,
            columns=('port', 'reputação')
        )
        self.window.peers_treeview.heading('#0', text='IP')
        self.window.peers_treeview.heading('port', text='port')
        self.window.peers_treeview.heading('reputação', text='reputação')
        self.window.peers_treeview.column('#0', width=130)
        self.window.peers_treeview.column('port', width=60)
        self.window.peers_treeview.column('reputação', width=80)
        self.window.peers_treeview.grid(row=1, column=0)
        self.window.peers_treeview_scrollbar = tk.Scrollbar(self.window.frame_connected_peer)
        self.window.peers_treeview_scrollbar.grid(row=1, column=1, sticky='ns')
        self.window.peers_treeview['yscrollcommand'] = \
            self.window.peers_treeview_scrollbar.set

    @staticmethod
    def create_entry(root):
        entry = tk.Entry(root)
        entry.var = tk.StringVar()
        entry['textvariable'] = entry.var
        return entry

    @staticmethod
    def is_valid_ipv4(ip):
        blocks = ip.split('.')
        if (len(blocks) != 4
            or not ((0 <= int(blocks[0]) <= 255)
                and (0 <= int(blocks[1]) <= 255)
                and (0 <= int(blocks[2]) <= 255)
                and (0 <= int(blocks[3]) <= 255)
            )
        ):
            return False
        else:
            return True

    @staticmethod
    def is_valid_multicast_ipv4(ip):
        blocks = ip.split('.')
        if (MulticastNewsPeer.is_valid_ipv4(ip) and (224 <= int(blocks[0]) <= 239)):
            return True
        else:
            return False
    
    def send_news_btn_action(self):
        """
        Envia a noticia escrita em news_entry para os grupos conectados.
        Chamado quando o usuario pressiona send_news_btn.
        """
        print("Apertou send_news_btn")
        text = self.window.news_entry.var.get()
        if not text:
            print("send_news_btn_action: Texto vazio")
            return
        self.send_news(text)

    def join_group_btn_action(self):
        """
        Usa o valor das entries pra tentar entrar no grupo.
        Chamado quando o usuario pressiona join_group_btn.
        """
        print("Apertou join_group_btn")
        ip = self.window.group_ip_entry.var.get()
        if not self.is_valid_multicast_ipv4(ip):
            print("join_group_btn_action: IP", ip, "invalido")
            return
        try:
            port = int(self.window.group_port_entry.var.get())
        except ValueError:
            print("join_group_btn_action: Porta", port, "invalida")
            return

        self.join_group((ip, port))

    def exit_group_btn_action(self):
        """
        Usa o valor das entries pra tentar sair do grupo.
        Chamado quando o usuario pressiona exit_group_btn
        """
        print("Apertou exit_group_btn")
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
        Chamado quando o usuário pressiona fake_news_alert_btn.
        """
        print("Apertou fake_news_alert_btn")
        ip = self.window.fake_news_ip_entry.var.get()
        if not self.is_valid_ipv4(ip):
            print("Alert fake news: ip invalido.", ip)
            return

        try:
            port = int(self.window.fake_news_port_entry.var.get())
        except ValueError:
            print("Alert fake news: Porta invalida.", port)
            return

        address = (ip, port)
        if address not in self.connected_peers:
            print("Alert fake news: Endereço desconhecido.", address)
            return

        peer = self.connected_peers[address]
        id_ = self.window.fake_news_id_entry.var.get()
        if id_ not in peer.news:
            print("Alert fake news: ID de noticia desconhecido.", id_)
            return

        reason = self.window.fake_news_reason_entry.var.get()
        self.alert_fake_news(address, id_, reason)

    def tk_on_closing(self):
        """Callback para fechar o programa quando clica no X da janela ou da alt-f4"""
        print("Fechando programa")

        print("Fechando socket unicast")
        try:
            self.uni_sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.uni_sock.close()
        while self.uni_thread.is_alive():
            time.sleep(0.1)
            print("Esperando thread unicast")

        print("Fechando sockets multicast")
        for i, sock in enumerate(self.multi_socks):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        for thread in self.multi_threads:
            while thread.is_alive():
                time.sleep(0.1)
                print("Esperando thread multicast")
        # Fecha a GUI
        self.window.destroy()

    # Métodos das outras coisas
    def listen_multicast(self, sock):
        print("Começando socket multicast no endereço", sock.getsockname())
        while True:
            try:
                msg = sock.recv(1024)
            except InterruptedError:
                print("Fechando thread multicast")
                return
            except OSError:
                print("Fechando thread multicast")
                return

            if not msg:
                continue

            print('recebeu no grupo', sock.getsockname(), 'mensagem:', msg)
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError:
                print("listen_multicast: Nãoi conseguiu decodificar JSON")
                continue

            try:
                sender_addr = msg['address']
            except KeyError:
                print("listen_multicast: Mensagem não tem o campo 'address'")
                continue

            # Verifica se é um join
            if 'key' in msg:
                self.ack_new_peer(tuple(sender_addr), msg['key'].encode('latin-1'))
            # Verifica se é notícia
            if 'news' in msg and 'signature' in msg:
                self.decode_news(msg['news'].encode('latin-1'), msg['signature'].encode('latin-1'), tuple(msg['address']))
            if 'alert' in msg and 'signature' in msg:
                self.decode_fake_news_alert(
                    msg['alert'], msg['signature'].encode('latin-1'), tuple(msg['address'])
                )

    def add_new_peer(self, new_peer_addr, new_peer_key):
        """
        Adiciona um par à lista de conectados.

            :param new_peer_addr: Endereço (ip, port) do novo par
            :param new_peer_key: Chave do novo par
        """
        # Se já estava conectado, atualiza para a chave enviada
        if new_peer_addr in self.connected_peers:
            return

        self.connected_peers[new_peer_addr] = ConnectedPeer(new_peer_key, new_peer_addr)
        peer = self.connected_peers[new_peer_addr]
        self.window.peers_treeview.insert(
            '',
            0,
            f"{peer.addr[0]},{peer.addr[1]}",
            text=peer.addr[0],
            values=(peer.addr[1], peer.reputation)
        )

    def ack_new_peer(self, new_peer_addr, new_peer_key):
        """
        Adiciona um novo par que se conectou a uma das redes.
        Chamado quando recebe a mensagem na porta multicast.
        Envia ao novo par a chave publica.

            :param new_peer_addr: Endereço (ip, porta) do novo par.
            :param new_peer_key: Chave publica para verificar a assinatura das mensagens do novo par.
                No formato PEM.
        """
        # Adiciona o par
        self.add_new_peer(new_peer_addr, new_peer_key)
        # Envia a chave publica a esse par
        self.uni_sock.sendto(
            bytes(json.dumps({'key': self.public_key_encoded.decode('latin-1')}), 'utf-8'),
            new_peer_addr
        )

    def decode_news(self, data, signature, addr):
        """
        Verifica se a noticia recebida é valida.
        Se for, adiciona para a lista de noticias e mostra na GUI.
        """
        sender = None
        if addr in self.connected_peers:
            sender = self.connected_peers[addr]
        # Se quem enviou a noticia não é um par conectado
        else:
            print("sender nao encontrado")
            return
        print('decodificou endereço. Sender é', sender)

        # Verifica se a assinatura é a certa
        try:
            sender.key.verify(signature, data, hashes.SHA512())
        except InvalidSignature:
            print("assinatura zuou")
            return
        print('verificou a assinatura')

        # Extrae a notícia
        try:
            news = json.loads(data)
        except json.JSONDecodeError:
            print("nao conseguiu extrair a mensagem")
            return
        print('decodificou a noticia. é', news)

        try:
            sender.add_news(news['text'], news['id'])
        except ValueError:
            print("add_news: Texto repetido enviado por", sender)
            return
        except IndexError:
            print("add_news: ID repetido enviado por", sender)
            return
        self.update_reputation_display(sender)

        self.window.chat.configure(state='normal')
        self.window.chat.insert('1.0', '\n')
        self.window.chat.insert('1.0', f"{addr} - {news['id']}: {news['text']}")
        self.window.chat.configure(state='disable')

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
        # Tenta decodificar o JSON do alerta
        try:
            alert = json.loads(alert_data)
        except json.JSONDecodeError:
            print("decode_fake_news_alert: Não conseguiu decodificar json")
            return
        fake_news_addr = tuple(alert['address'])
        fake_news_id = alert['id']

        # Checa se que alertou é conhecido
        if (alerter_addr not in self.connected_peers):
            print("decode_fake_news_alert: alerter_addr", alerter_addr, "desconhecido")
            return

        # Checa se quem é suspeito é conhecido
        if fake_news_addr not in self.connected_peers:
            print("decode_fake_news_alert: fake_news_addr", fake_news_addr, "desconhecido")
            return
        suspected_peer = self.connected_peers[fake_news_addr]

        # Checa se a notícia suspeita é conhecida
        if fake_news_id not in suspected_peer.news:
            print("decode_fake_news_alert: ID de noticia", fake_news_id, "desconhecido")
            return
        suspected_news = suspected_peer.news[fake_news_id]

        # Checa se o alerta não é repetido
        if alerter_addr in suspected_news.fake_news_alerters:
            print("decode_fake_news_alert: recebeu alerta repetido")
            return
        suspected_news.fake_news_alerters.add(alerter_addr)

        # Diminui a reputação e atualiza a tabela
        self.connected_peers[fake_news_addr].decrease_reputation()
        self.update_reputation_display(self.connected_peers[fake_news_addr])

        # Mostra uma mensagem no chat que recebeu alerta de fakle news
        self.window.chat['state'] = 'normal'
        self.window.chat.insert('1.0', '\n')
        self.window.chat.insert('1.0', (
            f"{alerter_addr}: "
            f"Reportou que a noticia '{fake_news_id}' de {fake_news_addr} é falsa"
        ))
        self.window.chat['state'] = 'disable'
  
    def update_reputation_display(self, peer):
        values = self.window.peers_treeview.item(f'{peer.addr[0]},{peer.addr[1]}')['values']
        values[1] = peer.reputation
        self.window.peers_treeview.item(
            f'{peer.addr[0]},{peer.addr[1]}',
            values=values
        )

    def listen_unicast(self):
        """Fica escutando por mensagens no socket unicast."""
        print("Começando o socket unicast")
        while True:
            # Espera receber mensagem
            try:
                msg, sender_addr = self.uni_sock.recvfrom(1024)
            except InterruptedError:
                print("Fechando thread unicast")
                return
            except OSError:
                print("Fechando thread unicast")
                return

            if not msg:
                continue

            print("Recebeu de", sender_addr, "mensagem unicast")
            # Decodifica a mensagem
            # Por enquanto, a unica coisa que recebe é chave de quem já esta na rede
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError:
                print("listen_unicast: Não conseguiu decodificar o JSON")
                continue
            try:
                sender_key = msg['key'].encode('latin-1')
            except KeyError:
                print("listen_unicast: Mensagem não tem o campo 'key'")
                continue

            self.add_new_peer(sender_addr, sender_key)

    def send_news(self, news_text):
        """
        Envia uma noticia para todos os grupos em que esta conectado.
        
            :param news_text: O texto da notícia a ser enviada.
        """
        news_data = json.dumps({
            'text': news_text,
            'id': str(self.next_news_id),
        })
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
                print("join_group: Tentou entrar mais uma vez no mesmo grupo")
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
            threading.Thread(target=lambda: self.listen_multicast(new_socket), daemon=True)
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

            :param addr: Endereço (IP, porta) do grupo multicast
        """
        # Pega a socket do grupo
        sock_to_close = None
        for sock in self.multi_socks:
            if sock.getsockname() == addr:
                sock_to_close = sock
                break

        # Se tava participando do grupo
        if sock_to_close:
            # Fecha a socket
            sock_idx = self.multi_socks.index(sock_to_close)
            try:
                sock_to_close.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock_to_close.close()
            # Espera a thread dessa socket acabar
            thread_to_close = self.multi_threads[sock_idx]
            while thread_to_close.is_alive():
                time.sleep(0.05)
            # Limpa
            self.multi_threads.remove(thread_to_close)
            self.multi_socks.remove(sock_to_close)
            # Tira da GUI
            self.window.group_treeview.delete(f"{addr[0]},{addr[1]}")
        else:
            print("exit_group: Tentou sair de um grupo que não fazia parte")
            pass

    def alert_fake_news(self, addr, id_, reason):
        """
        Envia um alerta que uma certa noticia é falsa.

            :param addr: Endereço de quem enviou a noticia falsa.
            :param id: Id da notícia falsa.
            :param reason: Mensagem com a justificativa de porque é falsa.
        """
        alert_data = json.dumps({
            'id': id_,
            'address': addr,
            'reason': reason,
        })

        signature = self.private_key.sign(bytes(alert_data, 'latin-1'), hashes.SHA512())

        msg = bytes(json.dumps({
            'alert': alert_data,
            'signature': signature.decode('latin-1'),
            'address': self.uni_sock.getsockname()
        }), 'utf-8')

        print("Enviando que a noticia", id_, "de", addr, "é falsa")
        for sock in self.multi_socks:
            sock.sendto(msg, sock.getsockname())


class ConnectedPeer:
    """
    Representa um par com quem se conectou em um dos grupos multicast.
    
        :param key: Chave pública da assinatura do par.
        :param addr: Endereço (ip, porta) que identifica o par
    """
    def __init__(self, key, addr):
        self.key = load_pem_public_key(key, backend=default_backend())
        self.addr = addr
        self.reputation = 0
        self.news = {}

    def __str__(self):
        return str(self.addr)

    def add_news(self, text, id_):
        """Adiciona a noticia ao par e recalcula a reputação"""
        # Checa por ID repetido
        if id_ in self.news:
            raise IndexError(f"Id {id_} da notícia é repetido")

        # Checa por texto repetido
        # TODO: Muito ineficiente, calcular um hash ou algo parecido
        for key in self.news:
            if self.news[key].text == text:
                raise ValueError(f"Notícia já existe com outro id")

        # Cria a noticia
        self.news[id_] = News(id_, text)

        # Sobe 0.3 se reputação >= 0
        # Sobe 0.1 se reputação <= -20
        reputation_delta = 0.3 + max(min(self.reputation/10, 0), -0.2)
        self.reputation += reputation_delta

    def decrease_reputation(self):
        """Diminui a reputação em um passo. Usado quando descobre fake"""
        self.reputation -= 1


class News:
    """
    Representa uma noticia.

        :param id_: Identicador único de uma notícia em um par
        :param text: Corpo da notícia
    """
    def __init__(self, id_, text):
        self.id = id_
        self.text = text
        # Conjunto de pessoas que avisaram que essa notícia é fake news
        self.fake_news_alerters = set()


if __name__ == "__main__":
    program = MulticastNewsPeer()
    program.start()
