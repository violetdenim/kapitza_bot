import os, socket
from connection import evaluate_my_ip

class Host:
    def __init__(self, evaluate=False):
        # self.host_name = socket.gethostname()
        if evaluate:
            self.host_ip = evaluate_my_ip()
        else:
            self.host_ip = os.environ.get("HOST_IP") 
        self.port = int(os.environ.get("HOST_PORT"))
        print(f"Host ip: {self.host_ip}, host port: {self.port}")

    def connected_client_socket(self):
        # create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_address = (self.host_ip, self.port-1)
        client_socket.connect(socket_address)
        return client_socket

    def server_socket(self):
        server_socket = socket.socket()
        server_socket.bind((self.host_ip, (self.port-1)))
        server_socket.listen(5)
        return server_socket