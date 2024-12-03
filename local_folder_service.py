import time, os
import dotenv
import asyncio
from pipeline import Pipeline
from src.gender import detect_gender


class OneThreadProcessor:
    """ Thread monitors input folder and puts new_filenames into the queue"""
    def __init__(self, input_folder=".received", check_freq=1.0, **pipeline_args):
        self.input = input_folder
        self.check_freq = check_freq
        os.makedirs(self.input, 0o777, True)

        self.processor = Pipeline(**pipeline_args)
        self.object_state = 0
        
    async def process_newuser_file(self, target_name):
        assert(self.object_state == 0)
        self.object_state = 1
        self.processor.tts.engine.get_audio("Здравствуйте, меня зовут Сергей Капица! Представьтесь, пожалуйста.", output_name=target_name)
        
    async def process_username(self, input_file_name, target_name):
        assert(self.object_state == 1)
        self.object_state = 0
        _name = os.path.split(input_file_name)[-1]
        _, _ext = os.path.splitext(_name)
        if _ext == ".txt":
            with open(input_file_name, 'r', encoding='utf-16') as f:
                user_answer = f.read()
        else:
            user_answer = self.processor.asr.get_text(input_file_name)
            
        if user_answer is None:
            print(f"Couldn't fetch username: {user_answer} from file {input_file_name}. Setting name to Дорогой друг")
            username = "Дорогой друг"
            usergender = "M"
        else:
            custom_prompt = """Ты - система аутентификации для ASR. Пользователя просили представиться. Выведи в ответ только его или её имя в именительном (звательном) падеже и отчество, если он указал его.
                Фамилию игнорируй, если пользователь специально не обозначил полное обращение. Если ввод нерелевантен, выведи !

                Например:
                Ввод: Андрюшей звать. Вывод: Андрюша.
                Ввод: Меня зовут Катя. Вывод: Катя.
                Ввод: Антоном меня звать. Вывод: Антон.
                Ввод: Иван Петрович. Вывод: Иван Петрович.
                Ввод: Меня зовут Амаяк Акопян. Вывод: Амаяк.
                Ввод: Леди Гага. Вывод: Леди Гага.
                Ввод: Джон Джонс. Вывод: Джон.
                Ввод: Хуанг Ли Вьет. Вывод: Хуанг.
                Ввод: Си Цзиньпин. Вывод: Цзиньпин.
                Ввод: Меня зовут Патель. Вывод: Патель.
                Ввод: Иван Мухин. Только так и никак иначе. Вывод: Иван Мухин.
                Ввод: Мухин Иван. Я люблю свою фамилию. Вывод: Иван Мухин.
                """
            self.processor.llm.set_engine(user_name=None, user_gender=None, reset=True, custom_system_prompt=custom_prompt)
            print(f"User answered: {user_answer}")
            user_answer = self.processor.llm.chat_engine.chat(user_answer).response
            user_answer = user_answer.strip(".,! ").capitalize()
            
            username = user_answer
            if _ext != ".txt":
                usergender = detect_gender(input_file_name)
            else:
                usergender = 'F'
            print(f"User name: {username}")
            print(f"User gender: {usergender}")

        self.processor.set_user(username, usergender)
        self.processor.tts.engine.get_audio(f"{username}, приятно познакомиться", output_name=target_name)
        
    async def process_request(self, input_file_name, target_name):
        assert(self.object_state == 0)
        _name = os.path.split(input_file_name)[-1]
        _, _ext = os.path.splitext(_name)
        if _ext == '.txt':
            # override user_messaage with file content
            with open(input_file_name, 'r', encoding='utf-16') as f:
                user_message = f.read()
            file_name = None
        else:
            user_message = None
            file_name = input_file_name
        async for name in self.processor.async_process(file_to_process=file_name, user_message=user_message, output_name=target_name):
            print(f"main thread got result {name}")
            pass
    
    async def run(self):
        while True:
            time.sleep(self.check_freq)
            files = os.listdir(self.input)
            # fetch files using creation date
            if len(files):
                sorted_files = list(sorted([os.path.join(self.input, file_name) for file_name in files], key=lambda x: os.path.getctime(x)))
                audio_engine = self.processor.tts.engine
                self.is_expecting_username = False
                try:
                    for input_file_name in sorted_files:
                        if not os.path.exists(input_file_name):
                            continue
                        t = time.time_ns()
                        # process in place
                        _name = os.path.split(input_file_name)[-1]
                        # use same names in output as in input
                        target_name = os.path.join(audio_engine.folder, os.path.splitext(_name)[0] + ".wav")
                       
                        if _name == "newuser":
                            await self.process_newuser_file(target_name)
                        else:
                            if self.object_state == 1: # expect user name as an answer
                                await self.process_username(input_file_name, target_name)
                            else:
                                n_repeat = 1
                                timeout = 0
                                while n_repeat > 0:
                                    try:
                                        await self.process_request(input_file_name, target_name)                         
                                        n_repeat = 0 # done
                                    except Exception as e:
                                        print(f"Got exception {e}")
                                        n_repeat -= 1
                                        if n_repeat <= 0:
                                            raise Exception("Unsuccessfully tried to process request")
                                        else:
                                            time.sleep(timeout)
                        if os.path.exists(input_file_name):
                            os.remove(input_file_name)    
                        t = time.time_ns() - t
                        print(f"Processing {input_file_name} took {t/1_000_000_000} s")
                except Exception as e:
                    print(f"Execution aborted with Exception {e}")
                    print(f"Cleaning up all files inside {self.input}")
                    files = list(os.listdir(self.input))
                    for f in files:
                        _full_path = os.path.join(self.input, f)
                        if os.path.exists(_full_path):
                            os.remove(_full_path)
                    print(f"Finished cleanup. Resume execution, starting with newuser")
                    self.object_state = 0

if __name__ == "__main__":    
    import sys
    if len(sys.argv) > 1:
        n_tts = max(1, min(8, int(sys.argv[1])))
    else:
        n_tts = 1

    dotenv.load_dotenv()
    # allocate last available graphics card as default device
    import torch
    #torch.set_default_device(f'cuda:{torch.cuda.device_count()-1}')
    torch.set_default_device('cuda:0')

    
    from utils.logger import logger
    logger.log_mode = "s"

    input_folder = ".received"
    output_folder = ".generated"
    os.environ["LLAMA_INDEX_CACHE_DIR"] = "../llama-files"
    model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
    # model_url = f"https://huggingface.co/kzipa/kap34_8_8_10/resolve/main/kap34_8_8_10.Q4_K_M.gguf"
    use_llama_guard = False

    for work_dir in [input_folder, output_folder]:
        os.makedirs(work_dir, 0o777, True)
        for f in os.listdir(work_dir):
            os.remove(os.path.join(work_dir, f))
    # also cleanup user-logging files
    for f in os.listdir('.'):
        if os.path.splitext(f)[-1] == ".json":
            os.remove(f)

    runnable = OneThreadProcessor(input_folder=input_folder, check_freq=1.0,
                                  output_folder=output_folder, model_url=model_url, use_llama_guard=use_llama_guard, n_tts=n_tts)
    asyncio.run(runnable.run())
