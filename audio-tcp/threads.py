import os
import threading
import urllib.request
from queue import Queue
import time, random
 
 
class QueuedThread(threading.Thread):
    def __init__(self, queue, id):
        threading.Thread.__init__(self)
        self.queue = queue
        self.id = id
    
    def run(self):
        while True:
            message = self.queue.get() # Получаем текст из очереди
            print(self.id, ":", message)
            # sleep for some time
            time.sleep(random.random())
            self.queue.task_done()
 
def main(messages):
    queue = Queue()
    
    for i in range(5):
        t = QueuedThread(queue, i)
        t.daemon = True
        t.start()
    
    for msg in messages:
        queue.put(msg)
 
    # Ждем завершения работы очереди
    queue.join()
 
if __name__ == "__main__":
    main("Just some words to be splitted in queue and processed by 5 threads separately".split(' '))
