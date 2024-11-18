import threading
from queue import Queue
import time

class KillableThread(threading.Thread):
    def __init__(self, input: Queue):
        super().__init__()
        self._kill = threading.Event()
        self.input = input

    def run(self):
        while True:
            is_killed = self._kill.wait(0.05)
            if is_killed:
                break
            item = input.get(block=True)
            print(item)
            input.task_done()
        
        print("Killing Thread")

    def kill(self):
        self._kill.set()
        
input = Queue()
t = KillableThread(input)
t.start()
input.put(1)
input.put(2)
input.put(3)
input.put(4)
input.put(5)
input.join()
t.kill()