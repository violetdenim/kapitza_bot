import threading
from queue import Queue
from .host import InputMedium, OutputMedium
from pipeline import Pipeline
import os

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
        # variable to store current username, expect user answer as result
        self.username = None

    def run(self):
        while True:
            try:
                data = self.input.get(timeout=self.timeout)
                if len(data) == 0:
                    raise Exception("No Data!")
                input_file_name = data
            except Exception as e:
                return 0
            print("Got from queue:", input_file_name)
            if input_file_name == "newuser":
                # initiate new protocol, ask user his name
                self.username = None
                output_file_name = self.processor.tts.get_audio("Здравствуйте, меня зовут Сергей Капица! Представьтесь, пожалуйста.")
            else:
                if self.username is None: # expect user name as an answer
                    user_answer = self.processor.asr.get_text(input_file_name)
                    print(f"User answered: {user_answer}")
                    self.username = user_answer
                    self.processor.llm.set_engine(user_name=None, reset=True, custom_system_prompt="""Ты - система аутентификации для ASR. Пользователя просили представиться. Выведи в ответ только его имя.""")
                    self.username = self.processor.llm.prompt(user_answer)
                    self.processor.set_user(self.username)
                    output_file_name = self.processor.tts.get_audio(f"{self.username}, приятно познакомиться")
                else:
                    output_file_name = self.processor.process(
                        user_name=self.username,
                        file_to_process=input_file_name)
            os.remove(input_file_name)
            self.output.put(output_file_name)
            self.input.task_done()
