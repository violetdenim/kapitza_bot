import os
import socket
from .get_ip import evaluate_my_ip
from queue import Queue
import time


class Host:
    def __init__(self, ip, port):
        self.host_ip = ip if ip else evaluate_my_ip()
        self.port = port if port else 9611
        self.socket_address = (self.host_ip, self.port-1)

    def connected_client_socket(self):
        # create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = False
        while not connected:
            try:
                client_socket.connect(self.socket_address)
                connected = True
            except Exception as e:
                print(f"Client can not connect for {self.socket_address}")
                time.sleep(10)
                continue
        return client_socket

    def server_socket(self):
        server_socket = socket.socket()
        server_socket.bind(self.socket_address)
        server_socket.listen(5)
        print(f"Created server socket for {self.socket_address}")
        return server_socket


class Sender:
    def __init__(self, host: Host):
        self.server_socket = host.server_socket()
        self.client_socket = None

    def establish_connection(self):
        self.client_socket, _ = self.server_socket.accept()

    def send(self, data):
        if not self.client_socket:
            self.establish_connection()
        self.client_socket.sendall(data)

    def __exit__(self):
        if self.client_socket:
            self.client_socket.close()
        self.server_socket.close()


class Receiver:
    def __init__(self, host: Host):
        self.host = host
        self.socket = None
        self.chunk = 4096 + 44  # + wav.header

    def establish_connection(self):
        self.socket = self.host.connected_client_socket()

    def get(self, timeout=None):
        if not self.socket:
            self.establish_connection()
        self.socket.settimeout(timeout)
        return self.socket.recv(self.chunk)

    def __exit__(self):
        if self.socket:
            self.socket.close()


class InputMedium:
    """if port is None, medium is queue, otherwise host with given ip"""

    def __init__(self, ip=None, port=None, connector=None):
        self.port = port
        if connector is not None:
            self.connection = connector
        else:
            if self.port is None:
                self.connection = Queue()
            else:  # create socket
                self.connection = Receiver(Host(ip=ip, port=port))

    def get_connection(self):
        return self.connection

    def get(self, timeout):
        return self.connection.get(timeout=timeout)

    def task_done(self):
        if isinstance(self.connection, Queue):
            self.connection.task_done()

    def __exit__(self):
        self.connection.__exit__()


class OutputMedium:
    """if port is None, medium is queue, otherwise host with given ip"""

    def __init__(self, ip=None, port=None, connector=None):
        self.port = port
        if connector is not None:
            self.connection = connector
        else:
            if self.port is None:
                self.connection = Queue()
            else:  # create socket
                self.connection = Sender(Host(ip=ip, port=port))

    def get_connection(self):
        return self.connection

    def send(self, data):
        if isinstance(self.connection, Queue):
            self.connection.put(data)
        else:
            self.connection.send(data)

    def __exit__(self):
        self.connection.__exit__()
