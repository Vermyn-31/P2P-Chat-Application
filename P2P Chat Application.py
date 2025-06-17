import socket
import threading
import tkinter as tk
from tkinter import messagebox
import json
import random

class ChatNode:
    def __init__(self, nickname, host, port):
        self.nickname = nickname
        self.server_socket = None
        self.connections_info = []
        self.connections_lock = threading.Lock()  # Lock for synchronizing access to connections
        self.root = None
        self.message_text = None
        self.chat_history = None
        self.host = host
        self.init_ping = 0
        self.port = int(port)
        self.id_sets = set()
        self.connections_tuple = []
        self.pm_msg, self.recipient, self.visited_nick = None, None, [self.nickname] #Temporary data

    # For setting up the GUIs
    def create_GUIs(self):
        self.root = tk.Tk()
        self.root.title("P2P Application")
        self.root.geometry("400x300")
        self.root.configure(bg="black")

        self.message_text = tk.StringVar()
        self.message_text.set("")

        self.chat_history = tk.Text(self.root)
        self.chat_history.configure(state='normal', bg="black", fg="white")
        self.chat_history.pack(fill=tk.BOTH, expand=True)

        entry_frame = tk.Frame(self.root)
        entry_frame.pack(fill=tk.X)

        message_entry = tk.Entry(entry_frame, textvariable=self.message_text)
        message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        message_entry.focus_set()
        
        send_button = tk.Button(entry_frame, text="Send", command=self.sending_message)
        send_button.pack(side=tk.RIGHT)

        self.update_chat_history(f"Node '{self.nickname}' started on {self.host}:{self.port}")
        self.update_chat_history(f"Note: Establish a connection first before using the public messages and other commands")
        self.update_chat_history("")
        self.update_chat_history(f"Basic Commands:")
        self.update_chat_history(f"'>connect <ip, 'localhost'> <port, int> <ping, int>' to connect, '>disconnect' to disconnect, '>private <recipient, str> <msg, str>' to send private messages, '>userlist' to display list of  connected users, '>nickname <new_nickname, str>' to change nicknames, '>ping <new_ping, int> <ip, 'localhost'> <port, int>' to change pins (use '>userlist' to see changes), default chat for  public messages ")
        self.update_chat_history("")
        self.update_chat_history(f"Chat History:")

        print(f"Node '{self.nickname}' started on {self.host}:{self.port}")

        message_entry.bind("<KeyRelease>", self.adjust_entry_width)
        self.root.mainloop()

    def update_chat_history(self, message):
        self.chat_history.configure(state='normal')
        self.chat_history.insert(tk.END, f"{message}\n")
        self.chat_history.configure(state='disabled')
        self.chat_history.see(tk.END)

    def show_message_box(self, title, message):
        messagebox.showinfo(title, message)

    def adjust_entry_width(self, event):
        entry_width = len(self.message_text.get()) + 10
        self.root.geometry(f"{entry_width}x300")

    # Initialization
    def start(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)

        threading.Thread(target=self.accept_clients).start()

    def accept_clients(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.receiving_messages, args=(client_socket,)).start()

    # Basic Functions
    def connect_to_node(self, host, port, ping, id):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ping = ping
        try:
            client_socket.connect((host, port))
            data = {"type":"new_conn", "nickname": self.nickname, "ping": int(ping), "host": self.host, "port": self.port, "id": id}
            encoded_data = json.dumps(data)
            client_socket.send(encoded_data.encode('utf-8'))

        except ConnectionRefusedError:
            self.update_chat_history(f"Connection refused to {host}:{port}")

    def send_public_message(self, sender_nickname, message, msg_id):
        self.id_sets.add(msg_id)
        with self.connections_lock:
            for connection in self.connections_info:
                # Establishing the connection
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((connection['host'],connection['port']))

                # Sending the data after establishing the connection
                data = {"type":"msg","msg": str(message), "sender_nick": sender_nickname,"id": msg_id}
                encoded_data = json.dumps(data)
                client_socket.send(encoded_data.encode('utf-8'))

    def send_private_message(self, recipient_nickname, message, is_True=True):
        #This function is used to determine the path with the least total ping
        while is_True:
            self.connections_tuple = sorted(self.connections_tuple, key = lambda x: x[1])
            nick, ping, host, port = self.connections_tuple.pop(0)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if recipient_nickname == nick:
                client_socket.connect((host,port))
                data = {"type":"pm_msg","nickname":self.nickname,"message":message, "ping": int(ping)}
                encoded_data = json.dumps(data)
                client_socket.send(encoded_data.encode('utf-8'))
                self.pm_msg, self.recipient, self.init_ping, self.connections_tuple, self.visited_nick = None, None, 0, [], [self.nickname]
                is_True = False
            elif recipient_nickname != nick:
                self.visited_nick.append(nick)
                client_socket.connect((host,port))
                data = {"type":"send_conn_tuple","nickname": nick, "ping":int(ping),"host":self.host, "port": self.port}
                encoded_data = data = json.dumps(data)
                client_socket.send(encoded_data.encode('utf-8'))
                is_True = False
            else:
                self.update_chat_history(f"Recipient not found!") 
                self.pm_msg, self.recipient, self.init_ping, self.connections_tuple, self.visited_nick = None, None, 0, [], [self.nickname]
                is_True = False
                
    def disconnect(self, disc_nick, ping, msg_id):
        with self.connections_lock:
            for connection in self.connections_info:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((connection['host'],connection['port']))

                data = {"type": "dis_conn", "nickname": disc_nick, "ping": int(ping), "id":msg_id}
                encoded_data = json.dumps(data)
                client_socket.send(encoded_data.encode('utf-8'))
                client_socket.close()

    def set_nickname(self, old_nickname, new_nickname, msg_id):
        self.id_sets.add(msg_id)
        with self.connections_lock:
            for connection in self.connections_info:
                if connection['nickname'] == old_nickname:
                    connection['nickname'] = new_nickname
                else:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((connection['host'],connection['port']))

                    data = {"type": 'set_nick', 'old_nick': old_nickname, 'new_nick': new_nickname, "id": msg_id}
                    encoded_data = json.dumps(data)
                    client_socket.send(encoded_data.encode('utf-8'))

    def set_ping(self, ping, host, port, msg_id):
        with self.connections_lock:
            for connection in self.connections_info:
                if connection["port"] == port:
                    connection["ping"] = ping
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((host, port))
                    data = {"type":"set_ping", "ping":int(ping), "host": self.host, "port": self.port, "id": msg_id}
                    encoded_data = json.dumps(data)
                    client_socket.send(encoded_data.encode('utf-8'))

    def node_list(self):
        with self.connections_lock:
            node_list = [str((connection['nickname'],connection['ping'])) for connection in self.connections_info]
        if node_list:
            self.update_chat_history(f"Connected Nodes: {', '.join(node_list)}")
        else:
            self.update_chat_history("Connected Nodes: None")

    def id_generator(self, lbound = 1, ubound = 100000):
        msg_id = random.randint(lbound,ubound)
        while msg_id in self.id_sets:
             msg_id = random.randint(lbound,ubound)        
        return msg_id

    def broadcast_message(self, data_type, nickname, id):
        with self.connections_lock:
            for connection in self.connections_info:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((connection['host'],connection['port']))

                data = {"type": data_type, "nickname": nickname, "id":id}
                encoded_data = json.dumps(data)
                client_socket.send(encoded_data.encode('utf-8'))
    
    def connections_tuple_convert(self, src_nick):
        tuple_list = []
        with self.connections_lock:
            for connection in self.connections_info:
                if connection["nickname"] != src_nick:
                    tuple_list.append((connection["nickname"], int(connection["ping"] + self.init_ping), connection["host"], connection["port"]))

        sorted_connection_list = sorted(tuple_list, key=lambda x: x[1])
        return sorted_connection_list

    # For sending messages and GUI on the user-side
    def sending_message(self):
        message = self.message_text.get()
        self.message_text.set("")

        if message.startswith(">connect"):
            str_split = message.split(" ", 3)
            if len(str_split) == 4:
                if int(str_split[2]) == self.port:
                    self.show_message_box("Error", "Connecting to your own IP address and port error")
                else:
                    if int(str_split[3]) > 0:
                        self.connect_to_node(str_split[1], int(str_split[2]), int(str_split[3]), self.id_generator())
                    else:
                        self.show_message_box("Error", "Ping should be a positive integer")
            else:
                self.show_message_box("Error", "Invalid connect command format.")
        
        elif message.startswith(">disconnect"):
            self.update_chat_history("Disconnected from all nodes.")
            msg_id = self.id_generator()
            self.id_sets.add(msg_id)
            self.disconnect(self.nickname, -1, msg_id)
            self.connections_info = []

        elif message.startswith(">msg "):
            self.send_public_message(self.nickname, message.split(">msg ")[1], self.id_generator())
            self.update_chat_history(f"[You]: {message.split('>msg ')[1]}")

        elif message.startswith(">private"):
            self.connections_tuple = self.connections_tuple_convert(self.nickname)
            str_split = message.split(" ", 2)
            if len(str_split) == 3:
                self.recipient, self.pm_msg = str_split[1], str_split[2]
                self.send_private_message(self.recipient, self.pm_msg)
                self.update_chat_history(f"[You]: {str_split[2]}")
            else:
                self.show_message_box("Error", "Invalid pm_msg format.")

        elif message.startswith(">userlist"):
            self.node_list()

        elif message.startswith(">nickname"):
            self.set_nickname(self.nickname, message.split(">nickname ")[1], self.id_generator())
            self.update_chat_history(f"{self.nickname} renamed to {message.split('>nickname ')[1]}")
            self.nickname = message.split(">nickname ")[1]

        elif message.startswith(">ping"):
            str_split = message.split(" ", 3)
            if len(str_split) == 4:
                self.set_ping(int(str_split[1]), str_split[2], int(str_split[3]), self.id_generator())
        
        else:
            if self.connections_info is not None:
                self.send_public_message(self.nickname, message, self.id_generator())
                self.update_chat_history(f"[You]: {message}")
            else:
                self.update_chat_history(f"[You]: {message}")

    # For receiving messages from other users
    def receiving_messages(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                data_loaded = json.loads(data)
                
                #Note: send_conn_tuple and rcv_conn_tuple are part of private message function (Used in getting the least path ping)
                if data_loaded["type"] == "send_conn_tuple":
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((data_loaded["host"],data_loaded["port"]))
                    self.init_ping = data_loaded["ping"]
                    conn_rcv_data = self.connections_tuple_convert(data_loaded["nickname"])
                    data = {"type":"rcv_conn_tuple", "conn_rcv":conn_rcv_data}
                    encoded_data = json.dumps(data)
                    client_socket.send(encoded_data.encode('utf-8'))

                elif data_loaded["type"] == "rcv_conn_tuple":
                    rcv_data = data_loaded["conn_rcv"]
                    add_conn_tuple = [tuple(item) for item in rcv_data if item[0] not in self.visited_nick]
                    self.connections_tuple += add_conn_tuple
                    self.send_private_message(self.recipient, self.pm_msg)

                elif data_loaded["type"] == "pm_msg":
                    self.update_chat_history(f"[Private from {data_loaded['nickname']}, ping={data_loaded['ping']}]: {data_loaded['message']}")

                elif data_loaded["id"] not in self.id_sets:
                    if data_loaded["type"] == "new_conn":
                        del data_loaded["type"]
                        self.update_chat_history(f"{data_loaded['nickname']} connected")
                        with self.connections_lock:
                            self.connections_info.append(data_loaded)
                        self.id_sets.add(data_loaded["id"])
                        self.connect_to_node(data_loaded["host"], data_loaded["port"], data_loaded["ping"], data_loaded["id"])

                    elif data_loaded["type"] == "dis_conn":
                        new_con = []
                        self.id_sets.add(data_loaded["id"])
                        self.update_chat_history(f"{data_loaded['nickname']} disconnected")
                        with self.connections_lock:
                            for connection in self.connections_info:
                                if connection["nickname"] == data_loaded["nickname"]:
                                    connection["ping"] = -1
                                else:
                                    new_con.append(connection)

                        self.connections_info = new_con
                        self.broadcast_message(data_loaded["type"], data_loaded["nickname"], data_loaded["id"])
    
                    elif data_loaded["type"] == "msg":
                        self.id_sets.add(data_loaded["id"])
                        self.update_chat_history(f"[Public from {data_loaded['sender_nick']}]: {data_loaded['msg']}")
                        self.send_public_message(data_loaded["sender_nick"], data_loaded["msg"], data_loaded["id"])  

                    elif data_loaded["type"] == "set_nick":
                        self.id_sets.add(data_loaded["id"])
                        self.update_chat_history(f"{data_loaded['old_nick']} renamed to {data_loaded['new_nick']}")
                        self.set_nickname(data_loaded["old_nick"], data_loaded["new_nick"], data_loaded["id"])
        
                    elif data_loaded["type"] == "set_ping":
                        with self.connections_lock:
                            for connection in self.connections_info:
                                if data_loaded["host"] == connection["host"] and data_loaded["port"] == connection["port"]:
                                    connection["ping"] = data_loaded["ping"]
            except ConnectionResetError:
                pass
            except json.JSONDecodeError:
                pass

def main():
    nickname = input("Enter nickname: ")
    host = input("Enter the host IP address('localhost' if blank): ") or 'localhost'
    port = int(input("Enter the port number: "))
    
    node = ChatNode(nickname, host, port)
    threading.Thread(target=node.start, args=(host, port)).start()
    threading.Thread(target=node.create_GUIs).start()

if __name__ == "__main__":
    main()