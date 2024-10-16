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

    def __init__(self, input: Queue, output: Queue, timeout=None, pipeline_args={}):
        # prevent heavy import if parent module doesn't need this thread
        threading.Thread.__init__(self)
        self.input = input
        self.output = output
        self.timeout = timeout
        self.processor = Pipeline(**pipeline_args)
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
                print(f"You should have never read this! {e}")
                return 0

            if not os.path.exists(input_file_name):
                self.input.task_done()
                continue

            print("Got from queue:", input_file_name)
            _name = os.path.split(input_file_name)[-1]
            # use same names in output as in input
            target_name = os.path.join(self.processor.tts.folder, os.path.splitext(_name)[0] + ".wav")
            if _name == "newuser":
                # initiate new protocol, ask user his name
                self.username = None
                output_file_name = self.processor.tts.get_audio("Здравствуйте, меня зовут Сергей Капица! Представьтесь, пожалуйста.", output_name=target_name)
            else:
                if self.username is None: # expect user name as an answer
                    user_answer = self.processor.asr.get_text(input_file_name)
                    if user_answer is None:
                        print(f"Couldn't fetch username: {user_answer} from file {input_file_name}. Setting name to Дорогой друг")
                        self.username = "Дорогой друг"
                    else:
                        user_answer = user_answer.strip(".,! ").capitalize()
                        print(f"User answered: {user_answer}")
                        self.username = user_answer
                    # self.processor.llm.set_engine(user_name=None, reset=True, custom_system_prompt="""Ты - система аутентификации для ASR. Пользователя просили представиться. Выведи в ответ только его имя.""")
                    # self.username = self.processor.llm.process_prompt(user_answer, user_name="user")
                    # print(f"System concluded: {user_answer}")
                    self.processor.set_user(self.username)
                    output_file_name = self.processor.tts.get_audio(f"{self.username}, приятно познакомиться", output_name=target_name)
                else:
                    output_file_name = self.processor.process(user_name=self.username, file_to_process=input_file_name, output_name=target_name)
            assert(output_file_name == target_name)
            if self.output:
                if output_file_name is not None:
                    self.output.put(output_file_name)
            os.remove(input_file_name)
            self.input.task_done()
