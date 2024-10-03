import threading
from queue import Queue
from connection.pipethread import PipelineThread
import time, os
import dotenv

class FolderMonitor(threading.Thread):
    """ Thread monitors input folder and puts new_filenames into the queue"""
    def __init__(self, output: Queue, input_folder=".received", check_freq=1.0):
        threading.Thread.__init__(self)
        self.input = input_folder
        self.output = output
        self.check_freq = check_freq
        os.makedirs(self.input, 0o777, True)
    
    def run(self):
        while True:
            for file_name in os.listdir(self.input):
                self.output.put(os.path.join(self.input, file_name))
            time.sleep(self.check_freq)

if __name__ == "__main__":
    dotenv.load_dotenv()
    # cleanup .generated
    input_folder = ".received"
    output_folder = ".generated"
    os.makedirs(input_folder, 0o777, True)
    os.makedirs(output_folder, 0o777, True)
    for f in os.listdir(output_folder):
        os.remove(os.path.join(output_folder, f))
    for f in os.listdir(input_folder):
        os.remove(os.path.join(input_folder, f))
    
    filenames_queue = Queue()
    PipelineThread(filenames_queue, None, timeout=None).start()
    FolderMonitor(filenames_queue, input_folder=input_folder, check_freq=1.0).start()
    filenames_queue.join()
