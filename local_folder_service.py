import threading
from queue import Queue
from connection.pipethread import PipelineThread
import time, os
import dotenv

class FolderMonitor(threading.Thread):
    """ Thread monitors input folder and puts new_filenames into the queue"""
    def __init__(self, output: Queue, input_folder=".received"):
        threading.Thread.__init__(self)
        self.input = input_folder
        self.output = output
    
    def run(self):
        while True:
            for file_name in os.listdir(self.input):
                self.output.put(os.path.join(self.input, file_name))
            time.sleep(1.0)
        pass

if __name__ == "__main__":
    dotenv.load_dotenv()
    
    q1, q2 = Queue(), Queue()
    pipeline = PipelineThread(q1, q2, timeout=None)

    FolderMonitor(q1).start()
    pipeline.start()

    q1.join()
    q2.join()
