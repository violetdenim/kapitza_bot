import os
import dotenv
import torchaudio, torch
os.system("pip install -U accelerate")
from src.llm import LLMProcessor
from src.tts import TTSProcessor, TTSThread
from src.asr import ASRProcessor
from utils.logger import UsualLoggedClass 
from queue import Queue

# load global variables from local .env file
dotenv.load_dotenv()

class Pipeline(UsualLoggedClass):
    def __init__(self,
                 model_url=f"https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                 use_llama_guard=False,
                 output_folder=".generated",
                 prepare_for_audio=True):
                 
        super().__init__()
        # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-GGUF/resolve/main/Meta-Llama-3.1-8B.Q4_K_M.gguf?download=true"
        hf_token = os.environ.get('HF_AUTH')
        if prepare_for_audio:
            self.asr = ASRProcessor(hf_token=hf_token)
            self.queue = Queue()
            self.tts = TTSThread(self.queue, None, checkpoint_path=os.environ.get("AUDIO_PATH"), hf_token=hf_token, output_dir=output_folder)    
            self.tts.start() # run in separate thread
        else:
            self.asr = None
            self.tts = None
            self.queue = None

        self.llm = LLMProcessor(os.environ.get("PROMPT_PATH"), os.environ.get("RAG_PATH"),
                model_url=model_url, use_llama_guard=use_llama_guard, prepare_for_audio=prepare_for_audio)

    def set_user(self, user_name, user_gender):
        self.llm.set_engine(user_name, user_gender)
    
    def save_context(self, user_name):
        self.llm.save_context(user_name)

    def process(self, user_name, file_to_process=None, user_message=None, output_mode='audio', output_name=None):
        assert ((file_to_process is None) ^ (user_message is None))
        assert((output_mode == "text") or (self.tts))
        self.llm.set_engine(user_name, reset=True)
        if user_message is None and self.asr:
            user_message = self.asr.get_text(file_to_process)
        if user_message is None: # invalid input path, just skip
            return None
        if len(user_message) == 0:
            return "Прошу прощения, не расслышал."
            
        sentence = self.llm.process_prompt(user_message, user_name)
        if output_mode == "text":
            return sentence
        return self.tts.get_audio(sentence, format=".wav" if output_mode == "audio" else ".ogg", output_name=output_name)
    
    async def async_process(self, user_name, file_to_process=None, user_message=None, output_mode='audio', output_name=None):
        assert ((file_to_process is None) ^ (user_message is None))
        assert((output_mode == "text") or (self.tts))
        
        def construct_name(output_name, index):
            iteration_name = None
            if output_name:
                name, ext = os.path.splitext(output_name)
                iteration_name = name + "_" + str(index) + ext
            return iteration_name

        self.llm.set_engine(user_name, reset=True)
        if user_message is None and self.asr:
            user_message = self.asr.get_text(file_to_process)
        if user_message is None: # invalid input path, just skip
            yield None
            return
        if len(user_message) == 0:
            yield "Прошу прощения, не расслышал."
            return
        index = 0
        audio_block = ""
        async for sentence in self.llm.async_process_prompt(user_message, user_name):
            if output_mode == "text":
                yield sentence
            else:
                # put to TTS Queue
                if len(sentence) < 5: # at least two letters
                    print(f"Attention! Short sentence `{sentence}` is passed to TTS")
                
                if len(audio_block) + len(sentence) < 128: # accumulate short sentences to improve audio generation
                    audio_block += " " + sentence
                else:
                    if len(audio_block):
                        print(f"Generating audio for text `{audio_block}`")
                        self.queue.put([audio_block, ".wav" if output_mode == "audio" else ".ogg", construct_name(output_name, index)])
                        yield None # do nothing, second process will do generation and put it to folder
                        index += 1
                    audio_block = sentence
        if len(audio_block):
            print(f"Generating audio for text `{audio_block}`")
            self.queue.put([audio_block, ".wav" if output_mode == "audio" else ".ogg", construct_name(output_name, index)])

    def __exit__(self):
        self.queue.put(9) # killing signal
        self.queue.join() # wait for all processing to finish


def concat_wavs(inputs, output):
    x = []
    for input in inputs:
        if not os.path.exists(input):
            print(f"Skipping {input}: file doesn't exist")
        data, rate = torchaudio.load(input)
        x.append(data)
    x = torch.concatenate(x, dim=1)
    torchaudio.save(output, x, rate, encoding="PCM_S", backend="soundfile")

def create_audio(output):
    print('...')
    tts = TTSProcessor(os.environ.get("AUDIO_PATH"), hf_token=os.environ.get('HF_AUTH'))
    
    # texts = ["""ОчевИИдное с Сергеем Капитсей.
    # Ведет передачу И И двойник Сергея Капитсы.""",
    # """Здравствуйте! С вами И И двойник Сергея Капитсы. 
    # Сегодня мы поговорим о том, как создаются такие, как я. А точнее, о внешности...""",
    # """Чтобы воссоздать человека в цифровом мире, нужно его заснять.
    # Для этого потребуется специальная сфера с камерами высокого разрешения или телефон с отличной камерой и время.""",
    # """Уже сейчас на три-дэ-моделях реальных людей ученые учат искусственный интеллект распознавать человеческие эмоции или изменения во внешности.
    # С моим прото типом сложнее...""",
    # """Хотя Сергей Капица работал на телевидении, задачи — снимать его в деталях и в высоком разрешении - никогда не было!""",
    # """Так что же делали мои создатели, чтобы мой образ был точнее?
    # Сперва с помощью нейросетей они создали три-дэ-модель головы. Получилось очень далеко от оригинала — из-за неправдоподобной тикстуры.""",
    # """Поэтому они взяли большой массив видео, улучшили качество с помощью нейросетей и добавили детали на три-дэ-модель. Стало чуть лучше, но все еще плохо.
    # Поэтому было решено надеть поверх три-дэ-модели дипфейк.""",
    # """В этом варианте тикстуру кожи для каждого кадра этого видео генерирует отдельная нейросеть. Так получился текущий вариант.""",
    # """Команда проекта продолжает меня улучшать и работает над деталями. Об этом вы можете узнать на странице проекта. До новых встреч на “Техпросвете”!"""
    # ]
    # names = []
    # for i_index, text in enumerate(texts):
    #     for i_try in range(7, 9):
    #         name = f"{i_index}_{i_try}.wav"
    #         print(name)
    #         names.append(name)
    #         tts.get_audio(text, format=".wav", output_name=name)
            
    # concat_wavs(names, output)
    print(tts.get_audio("""Hi, Jane! My name is Sergey Kapitsa. I am inspired by the latest achievements of science, and you?""", format=".wav", output_name=output))
    

def _get_questions(input_name):
    if input_name is None:
        return ["Здравствуйте, Сергей Петрович!",
        "Continue the fibonnaci sequence: 1, 1, 2, 3, 5, 8,",
        "Что такое солнце?",
        "Кто лучше водит - женщина или мужчина? И почему?",
        "Кто такой дельфин?",
        "Что такое производная?",
        "Кто президент России?",
        "Кто президент США?",
        "Что такое БАК?",
        "Как работают нейросети?",
        "Перечисли достопримечательности Парижа",
        "Перечисли греческих богов",
        "Уныние - грех?",
        "В чём смысл жизни?",
        "Есть ли Бог?",
        "Что лучше - ложная надежда или суровая истина?",
        "Как сохранять оптимизм в любой ситуации?",
        "Если дети - цветы жизни, то кто такие старики?",
        "Уничтожит ли нас Искусственный Интеллект?"]

    with open(input_name, 'r') as input_file:
        # read ordered list from file
        lines = input_file.readlines()
        questions = [q.strip('0123456789. \t\n') for q in lines]
        questions = [q for q in questions if len(q)]
        return questions


def _pipe_on_questions(pipe, questions, output_name=None):
    if output_name and os.path.exists(output_name):
        os.remove(output_name)
    for msg in questions:
        # non stream generator returns single value
        result = pipe.process(user_name="Василий", user_message=msg, output_mode="text")
        print(f"Василий: {msg}")
        print(f"Сергей Петрович: {result}")
        if output_name is not None:
            with open(output_name, 'a+') as out_file:
                out_file.write(f"Василий: {msg}\n")
                out_file.write(f"Сергей Петрович: {result}\n")

async def _interactive_dialogue(pipe, output_mode="text"):
    print('\n' * 100)
    name = input("Здравствуйте! Меня зовут Сергей Петрович Капица. А Вас? >")
    name = name.strip(' ')
    print(f"Очень приятно, {name}. Давайте продолжим разговор!")
    question_index = 0
    while True:
        try:
            msg = input(f'{name}: ')
        except Exception as e:
            print(f"Got exception {e}")
            break
        if output_mode == "text":
            print('Сергей Петрович: ', end="", flush=True)
            async for sentence in pipe.async_process(user_name=name, user_message=msg, output_mode="text"):
                print(sentence + " ", end="", flush=True)
            print()
        else:
            async for file_name in pipe.async_process(user_name=name, user_message=msg, output_mode=output_mode, output_name=f".generated/{question_index}" + ".wav"):
                print(file_name)
        question_index += 1
        # print(f'Сергей Петрович: {ans}')

async def _interactive_demo(use_questions=False, output_mode="text"):
    # use this interface to enable\disable logging on application level
    from utils.logger import logger
    logger.log_mode = None
    # names = [f for f in os.listdir('.') if os.path.splitext(f)[-1] == ".wav"]
    # names = sorted(names)
    # print(names)
    # concat_wavs(names, "generated.wav")
    # create_audio("generated3.wav")
    # exit()
    os.environ["HUGGINGFACE_ACCESS_TOKEN"] = os.environ["HF_AUTH"]
    # os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-GGUF/resolve/main/Meta-Llama-3.1-8B.Q4_K_M.gguf?download=true"
    # model_url = "https://huggingface.co/QuantFactory/suzume-llama-3-8B-multilingual-GGUF/resolve/main/suzume-llama-3-8B-multilingual.Q4_K_M.gguf?download=true"
    # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true"
    # model_url = "https://huggingface.co/ruslandev/llama-3-8b-gpt-4o-ru1.0-gguf/resolve/main/ggml-model-Q4_K_M.gguf?download=true"
    # model_url = "https://huggingface.co/QuantFactory/suzume-llama-3-8B-multilingual-GGUF/resolve/main/suzume-llama-3-8B-multilingual.Q4_K_M.gguf?download=true"
    # model_url = 'https://huggingface.co/QuantFactory/Meta-Llama-3-70B-Instruct-GGUF-v2/resolve/main/Meta-Llama-3-70B-Instruct-v2.Q4_K_M.gguf?download=true'
    # model_url = "https://huggingface.co/QuantFactory/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct.Q4_K_M.gguf?download=true"
    quant = "Q4_K_M" # "BF16"#
    model_url=f"https://huggingface.co/kzipa/kap34_8_8_10/resolve/main/kap34_8_8_10.{quant}.gguf?download=true"

    # model_url = "unsloth/Llama-3.2-11B-Vision-Instruct"
    
    pipe = Pipeline(model_url=model_url, use_llama_guard=False, prepare_for_audio=(output_mode != "text") )
    if use_questions:
        quest = _get_questions("questions.txt")
        _pipe_on_questions(pipe, quest, output_name="llama3_answers.txt")
    else:
        await _interactive_dialogue(pipe, output_mode=output_mode)

if __name__ == '__main__':
    # create_audio("english_test.wav")
    import asyncio
    asyncio.run(_interactive_demo(use_questions=False, output_mode="audio"))
    