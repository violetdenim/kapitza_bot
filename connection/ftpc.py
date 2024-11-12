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
        try:
            with open(filename, 'rb') as oldFile:
                #send file size
                fileSize = os.path.getsize(filename).to_bytes(4, byteorder='big')
                self.clientSocket.send(fileSize)
                #send file name
                fileName = os.path.split(filename)[-1].rjust(20)
                self.clientSocket.send(fileName.encode('ASCII'))
                #loop and send file in 500 byte increments
                readBytes = oldFile.read(chunk_size)
                while readBytes:
                    self.clientSocket.send(readBytes)
                    readBytes = oldFile.read(chunk_size)
        except Exception as e:
            print(f'Got error {e} during file transmission')
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clientSocket.close()
        
class ConnectionThread:
    def __init__(self, ip, port, monitoring_folder):
        self.ip, self.port = ip, port
        self.monitoring_folder = monitoring_folder
        os.makedirs(self.monitoring_folder, 0o777, True)
        self.timeout = 3
    
    def run(self):
        with Connection(self.ip, self.port) as worker:
            while True:
                files = os.listdir(self.monitoring_folder)
                for f in files:
                    file_name = os.path.join(self.monitoring_folder, f)
                    worker.send(file_name)
                    os.remove(file_name)
                if len(files):
                    time.sleep(self.timeout)

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    worker = ConnectionThread(args.ip, args.port, args.folder)
    worker.run()
