import sys, os, time
import argparse
from socket import *


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('ip', type=str)
    parser.add_argument('port', type=int)
    parser.add_argument('folder', type=str)
    return parser.parse_args(args)

class Connection:
    def __init__(self, ip, port, timeout=3):
        self.clientSocket = socket(AF_INET, SOCK_STREAM)
        self.ip, self.port, self.timeout = ip, port, timeout
    
    def __enter__(self):
        connected = False
        while not connected:
            try:
                self.clientSocket.connect((self.ip, self.port))
                connected = True
            except:
                time.sleep(self.timeout)
        return self
    
    def send(self, filename, chunk_size=500):
        assert(os.path.exists(filename))
        oldFile = None
        try:
            while not oldFile:
                try:
                    oldFile = open(filename, 'rb')
                except Exception as e:
                    time.sleep(1) # copying is in progress!
            
            # send file size
            numBytes = os.path.getsize(filename)
            fileSize = numBytes.to_bytes(4, byteorder='big')
            self.clientSocket.send(fileSize)
            # send file name
            fileName = os.path.split(filename)[-1].rjust(128)
            self.clientSocket.send(fileName.encode('ascii'))
            print(f"Sending {filename}, numBytes={numBytes}")
            #loop and send file in 500 byte increments
            readBytes = oldFile.read(chunk_size)
            while readBytes:
                self.clientSocket.send(readBytes)
                readBytes = oldFile.read(chunk_size)
            oldFile.close()
            return 0
        except Exception as e:
            print(f'Got error {e} during file transmission')
            if oldFile:
                oldFile.close()
            return -1
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clientSocket.close()

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    os.makedirs(args.folder, 0o777, True)
    with Connection(args.ip, args.port) as worker:
        while True:
            files = os.listdir(args.folder)
            for f in files:
                file_name = os.path.join(args.folder, f)
                if worker.send(file_name) == 0:
                    os.remove(file_name)
                else:
                    print('Closing connection due to an unexpected error')
                    break # break cycle, close connection
            if len(files) == 0:
                time.sleep(0.1)
