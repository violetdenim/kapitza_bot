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
        fileName = self.connectionSocket.recv(128)
        print(numBytes, fileName)
        numBytes = int.from_bytes(numBytes, byteorder='big')
        fileName = fileName.decode('ascii').strip()
        out_name = os.path.join(self.store_dir, str(fileName))
        if len(fileName) > 0:
            print("Receiving", fileName, ", writing to ", out_name, f", numBytes={numBytes}")
            with open(out_name, 'wb') as file:
                while numBytes:
                    expectedBytes = min(numBytes, chunk_size)
                    data = self.connectionSocket.recv(expectedBytes, )
                    file.write(data)
                    numBytes -= len(data)
            return out_name
        return None
                
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
    
