import sys, os
import argparse
from socket import *
import logging
from utils.helper import formatted_datetime

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
        logging.info("establishing connection")
        self.connectionSocket, addr = self.serverSocket.accept()
        return self

    def receive(self, chunk_size=500):
        numBytes = self.connectionSocket.recv(4)
        fileName = self.connectionSocket.recv(128)
        try:
            numBytes = int.from_bytes(numBytes, byteorder='big')
            fileName = fileName.decode('ascii').strip()
        except Exception as e:
            msg = f"Got exception {e} during transmitted header interpretation."
            print(msg)
            logging.error(msg)
            return None
        out_name = os.path.join(self.store_dir, str(fileName))
        if len(fileName) > 0:
            print("Receiving", fileName, ", writing to ", out_name, f", numBytes={numBytes}")
            try:
                with open(out_name, 'wb') as file:
                    while numBytes:
                        expectedBytes = min(numBytes, chunk_size)
                        data = self.connectionSocket.recv(expectedBytes, )
                        file.write(data)
                        numBytes -= len(data)
                return out_name
            except Exception as e:
                msg = f"Got exception {e} during file transmission."
                print(msg)
                logging.error(msg)
        return None
                
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info("closing connection")
        self.connectionSocket.close()
        self.serverSocket.close()
        
               
if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG, filename="ftpc_log.log", filemode="w")
    logging.info(formatted_datetime())
    with Connection(args.port, args.folder) as worker:
        logging.info(f"connected through {args.port} to folder {args.folder}")
        while True:
            try:
                worker.receive()
            except Exception as e:
                msg = f"Got exception {e}"
                logging.error(msg)
                print(msg)
    
