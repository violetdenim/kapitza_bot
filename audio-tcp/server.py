# This is server code to send video and audio frames over TCP
import socket, os
import threading, wave, pickle, struct
from queue import Queue
import dotenv
import time, random

dotenv.load_dotenv()
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)#os.environ.get("HOST_IP")
print(host_name, host_ip)
port = int(os.environ.get("HOST_PORT"))

class QueuedThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

        self.server_socket = socket.socket()
        self.server_socket.bind((host_ip, (port-1)))
        self.server_socket.listen(5)
        self.chunk = 1024
        self.timeout = 10.0
    
    def run(self):
        client_socket, addr = self.server_socket.accept()
        try:
            while True:
                # close connection after delay
                file_name = self.queue.get(self.timeout) 
                # prepare data to stream
                wf = wave.open(file_name, 'rb')
                while True:
                    try:
                        data = wf.readframes(self.chunk)
                        if len(data) == 0:
                            print(f"Finished transmission for file {file_name}")
                            self.queue.task_done()
                            break # break inner while, move to the next file
                        a = pickle.dumps(data)
                        message = struct.pack("Q", len(a))+a
                        client_socket.sendall(message)        
                    except Exception as e:
                        print(f"Transmission interrupted by client for file {file_name}. Exception: {e}")
                        self.server_socket.close()
                        self.queue.task_done()
                        return -1
                print("File completed")
        except Exception as e:
            print(f"Empty queue for {self.timeout} seconds! {e}")
            self.server_socket.close()
            return -1

class TaskGenerator(threading.Thread):
    def __init__(self, queue, list_of_files):
        threading.Thread.__init__(self)
        self.queue = queue
        self.list_of_files = list_of_files
    
    def run(self):
        for file in self.list_of_files:
            # push with random delay
            time.sleep(random.random() * 3.0)
            self.queue.put(file)

def queued_audio_server(files=["short.wav", "temp.wav", "short.wav", "temp.wav", "short.wav"]):
    queue = Queue()
    generator = TaskGenerator(queue, [os.path.abspath(f) for f in files])
    server = QueuedThread(queue)
    server.start()
    generator.start()
    queue.join()

def successive_audio_server(files=["short.wav", "temp.wav", "short.wav", "temp.wav", "short.wav"]):
    queue = Queue()
    server = QueuedThread(queue)
    server.start()
    for f in files:
        # push with  delay
        queue.put(os.path.abspath(f))
        time.sleep(20.0)

    queue.join()

if __name__ == "__main__":
    successive_audio_server(["short.wav", "short.wav"])


