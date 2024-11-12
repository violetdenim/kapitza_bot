import sys, os
import argparse
from socket import *

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int)
    parser.add_argument('folder', type=str)
    return parser.parse_args(args)

class Connection:
    def __init__(self, port, store_dir='.'):
        self.store_dir = store_dir
        if store_dir not in {'.', '..'}:
            os.makedirs(store_dir, 0o777, True)
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind(('', port))
        self.serverSocket.listen(1)    
    
    def __enter__(self):
        self.connectionSocket, addr = self.serverSocket.accept()
        return self

    def receive(self, chunk_size=500):
        numBytes = self.connectionSocket.recv(4)
        numBytes = int.from_bytes(numBytes,byteorder='big')
        fileName = self.connectionSocket.recv(20)
        fileName = fileName.decode('ASCII').strip()
        out_name = os.path.join(self.store_dir, str(fileName))
        print("Receiving", fileName, ", writing to ", out_name, f", numBytes={numBytes}")
        with open(out_name, 'wb') as file:
            while numBytes > chunk_size:
                data = self.connectionSocket.recv(chunk_size)
                file.write(data)
                numBytes -= chunk_size
            if numBytes > 0:
                data = self.connectionSocket.recv(numBytes)
                file.write(data)
        return out_name
                
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connectionSocket.close()
        self.serverSocket.close()
        
        
class ConnectionThread:
    def __init__(self, port, target_folder):
        self.port = port
        self.target_folder = target_folder
    
    def run(self):
        with Connection(self.port, self.target_folder) as worker:
            while True:
                worker.receive()
        
if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    worker = ConnectionThread(args.port, target_folder=args.folder)
    worker.run()
    
