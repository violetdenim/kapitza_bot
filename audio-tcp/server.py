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
        # connected to a client, pass files from queue to a client
        # last_transmission_time = None
        while True:
            # close connection after delay
            try:
                file_name = self.queue.get(block=True, timeout=self.timeout) 
            except Exception as e:
                print(f"Empty queue for {self.timeout} seconds! Server is closing connection.")
                self.server_socket.close()
                return 0

            # prepare data to stream
            # if last_transmission_time:
            #     minimum_delay = 3_000_000 # ns - pause between files
            #     pause_time = time.time_ns() - last_transmission_time
            #     if pause_time < minimum_delay:
            #         # take a break
            #         # TBD: for files it is better to check file ending
            #         time.sleep(minimum_delay - pause_time) 

            with open(file_name, 'rb') as f:
                while len(data := f.read(self.chunk)):
                    try:
                        message = struct.pack("Q", len(data))+data
                        client_socket.sendall(message)        
                    except Exception as e:
                        print(f"Transmission interrupted by client for file {file_name}. Exception: {e}")
                        self.server_socket.close()
                        self.queue.task_done()
                        os._exit(-1)
            print(f"Finished transmission for file {file_name}")
            self.queue.task_done()
            # last_transmission_time = time.time_ns()
       

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

def queued_audio_server(files):
    queue = Queue()
    generator = TaskGenerator(queue, [os.path.abspath(f) for f in files])
    server = QueuedThread(queue)
    server.start()
    generator.start()
    queue.join()

def successive_audio_server(files, timeout=10.0):
    queue = Queue()
    server = QueuedThread(queue)
    server.start()
    for f in files:
        # push with  delay
        queue.put(os.path.abspath(f))
        time.sleep(timeout)

    queue.join()

if __name__ == "__main__":
    successive_audio_server(["voice/1.wav", "voice/2.wav", "voice/3.wav"])
    # successive_audio_server(["voice/short.wav"])


