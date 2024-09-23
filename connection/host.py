import os, socket
from .get_ip import evaluate_my_ip

class Host:
    def __init__(self, ip, port):
        # self.host_name = socket.gethostname()
        self.host_ip = ip if ip else evaluate_my_ip() # os.environ.get("HOST_IP") 
        self.port = port if port else 9611 
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