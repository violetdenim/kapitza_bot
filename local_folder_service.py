import time, os
import dotenv
import asyncio

from pipeline import Pipeline


class OneThreadProcessor:
    """ Thread monitors input folder and puts new_filenames into the queue"""
    def __init__(self, input_folder=".received", check_freq=1.0, **pipeline_args):
        self.input = input_folder
        self.check_freq = check_freq
        os.makedirs(self.input, 0o777, True)

        self.processor = Pipeline(**pipeline_args)
        # variable to store current username, expect user answer as result
        self.username = None
    
    async def run(self):
        while True:
            files = [os.path.join(self.input, file_name) for file_name in os.listdir(self.input)]
            # fetch files using creation date
            sorted_files = sorted(files, key=lambda x: os.path.getctime(x))
            if len(sorted_files):
                t = time.time_ns()
                for input_file_name in sorted_files:
                    # process in place
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
                            async for output_file_name in self.processor.async_process(user_name=self.username, file_to_process=input_file_name, output_name=target_name):
                                print(output_file_name)
                    os.remove(input_file_name)
                t = time.time_ns() - t
                print(f"Processing {input_file_name} took {t/1_000_000_000} s")
            else:
                time.sleep(self.check_freq)

if __name__ == "__main__":
    dotenv.load_dotenv()
    
    input_folder = ".received"
    output_folder = ".generated"
    # model_url = "https://huggingface.co/kzipa/kap34_8_8_10/resolve/main/kap34_8_8_10.Q4_K_M.gguf?download=true"
    model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
    use_llama_guard = False

    os.makedirs(input_folder, 0o777, True)
    os.makedirs(output_folder, 0o777, True)
    for f in os.listdir(output_folder):
        os.remove(os.path.join(output_folder, f))
    for f in os.listdir(input_folder):
        os.remove(os.path.join(input_folder, f))

    runnable = OneThreadProcessor(input_folder=input_folder, check_freq=1.0, output_folder=output_folder, model_url=model_url, use_llama_guard=use_llama_guard)
    asyncio.run(runnable.run())
