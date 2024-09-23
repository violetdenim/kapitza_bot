import os, socket

class Host:
    def __init__(self):
        self.host_name = socket.gethostname()
        self.host_ip = socket.gethostbyname(self.host_name) # os.environ.get("HOST_IP")
        self.port = int(os.environ.get("HOST_PORT"))

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