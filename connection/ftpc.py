import sys, os, time
import argparse
from socket import *
import logging
from utils.helper import formatted_datetime

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
                    msg = f"Got exception {e} during attempt to open file in FS. Will repeat try in 1 second"
                    print(msg)
                    logging.error(msg)
                    time.sleep(1) # copying is in progress!
            
            numBytes = os.path.getsize(filename)
            fileSize = numBytes.to_bytes(4, byteorder='big')
            fileName = os.path.split(filename)[-1].rjust(128).encode('ascii')
            
            self.clientSocket.send(fileSize)
            self.clientSocket.send(fileName)
            msg = f"Sending {filename}, numBytes={numBytes}"
            print(msg)
            logging.info(msg)
            #loop and send file in 500 byte increments            
            while True:
                readBytes = oldFile.read(chunk_size)
                if readBytes and len(readBytes):
                    logging.info(f"Sending {len(readBytes)}")
                    self.clientSocket.send(readBytes)
                else:
                    break
            oldFile.close()
            return 0
        except Exception as e:
            msg = f'Got error {e} during file transmission'
            print(msg)
            logging.error(msg)
            if oldFile:
                oldFile.close()
            return -1
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clientSocket.close()

    
if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG, filename="ftpc_log.log", filemode="w")
    logging.info(formatted_datetime())
    
    os.makedirs(args.folder, 0o777, True)
    with Connection(args.ip, args.port) as worker:
        logging.info(f"connected through {args.ip}:{args.port} to folder {args.folder}")
        while True:
            files = os.listdir(args.folder)
            for f in files:
                file_name = os.path.join(args.folder, f)
                if worker.send(file_name) == 0:
                    logging.info(f"removing {file_name}")
                    os.remove(file_name)
                else:
                    msg = 'Closing connection due to an unexpected error'
                    print(msg)
                    logging.error(msg)
                    break # break cycle, close connection
            if len(files) == 0:
                time.sleep(0.1)
