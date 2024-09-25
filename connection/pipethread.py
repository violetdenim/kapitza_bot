import threading
from queue import Queue
from .host import InputMedium, OutputMedium
from pipeline import Pipeline


class DummyPipeline(threading.Thread):
    """ Imitates Pipeline Interface, but does nothing"""

    def __init__(self, input: InputMedium, output: OutputMedium, timeout=None):
        threading.Thread.__init__(self)
        self.input = input
        self.output = output
        self.timeout = timeout

    def run(self):
        while True:
            try:
                data = self.input.get(timeout=self.timeout)
                if len(data) == 0:
                    raise Exception("No Data!")
            except Exception as e:
                print(f"{__class__.__name__}: no data")
                return 0
            print(f"{__class__.__name__}: sending {len(data)} bytes")
            self.output.send(data)
            self.input.task_done()


class PipelineThread(threading.Thread):
    """ Thread takes file_names from input_queue, processes them and puts answers to output_queue"""

    def __init__(self, input: Queue, output: Queue, timeout=None):
        # prevent heavy import if parent module doesn't need this thread
        threading.Thread.__init__(self)
        self.input = input
        self.output = output
        self.timeout = timeout
        self.processor = Pipeline()

    def run(self):
        while True:
            try:
                data = self.input.get(timeout=self.timeout)
                if len(data) == 0:
                    raise Exception("No Data!")
                input_user_name, input_file_name = data
            except Exception as e:
                return 0
            print("Got from queue:", input_user_name, input_file_name)
            output_file_name = self.processor.process(
                user_name=input_user_name,
                file_to_process=input_file_name)
            self.output.put(output_file_name)
            self.input.task_done()
