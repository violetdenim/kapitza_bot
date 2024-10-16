import sys
import os
import dotenv
import torchaudio, torch
import time
os.system("pip install -U accelerate")
from src.llm import LLMProcessor
from src.tts import TTSProcessor
from src.asr import ASRProcessor

from utils.logger import UsualLoggedClass 


# load global variables from local .env file
dotenv.load_dotenv()


class Pipeline(UsualLoggedClass):
    def __init__(self,
                 model_url=f"https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                 use_llama_guard=False,
                 output_folder=".generated"):
                 
        super().__init__()
        # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-GGUF/resolve/main/Meta-Llama-3.1-8B.Q4_K_M.gguf?download=true"
        hf_token = os.environ.get('HF_AUTH')
        self.asr = ASRProcessor(hf_token=hf_token)
        self.llm = LLMProcessor(os.environ.get(
            "PROMPT_PATH"), os.environ.get("RAG_PATH"),
            model_url=model_url,
            use_llama_guard=use_llama_guard)
        self.tts = TTSProcessor(os.environ.get(
            "AUDIO_PATH"), hf_token=hf_token, output_dir=output_folder)    

    def set_user(self, user_name):
        self.llm.set_engine(user_name)
    
    def save_context(self, user_name):
        self.llm.save_context(user_name)

    def process(self, user_name, file_to_process=None, user_message=None, output_mode='audio', output_name=None):
        assert ((file_to_process is None) ^ (user_message is None))
        self.llm.set_engine(user_name, reset=True)
        if user_message is None:
            user_message = self.asr.get_text(file_to_process)
        if user_message is None: # invalid input path, just skip
            return None
        if len(user_message) == 0:
            return None, "Прошу прощения, не расслышал."
        else:
            answer = self.llm.process_prompt(user_message, user_name)
        if output_mode == "text":
            return answer
        return self.tts.get_audio(answer, format=".wav" if output_mode == "audio" else ".ogg", output_name=output_name)

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
    tts.get_audio("""генеративную маску""", format=".wav", output_name=output)
    

def get_questions(input_name):
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


def pipe_on_questions(pipe, questions, output_name=None):
    if output_name and os.path.exists(output_name):
        os.remove(output_name)
    for msg in questions:
        # if output_name is None:
        #     _x = sys.stdout, sys.stderr
        #     sys.stdout, sys.stderr = open(os.devnull, 'w'), open(os.devnull, 'w')
        result = pipe.process(user_name="Василий", user_message=msg,  output_mode="text")
            # sys.stdout, sys.stderr = _x
        print(f"Василий: {msg}")
        print(f"Сергей Петрович: {result}")
        
        if output_name is not None:
            with open(output_name, 'a+') as out_file:
                out_file.write(f"Василий: {msg}\n")
                out_file.write(f"Сергей Петрович: {result}\n")

def interactive_dialogue(pipe, log=True):
    name = input("Здравствуйте! Меня зовут Сергей Петрович Капица. А Вас? >")
    name = name.strip(' ')
    print(f"Очень приятно, {name}. Давайте продолжим разговор!")
    while True:
        try:
            msg = input(f'{name}: ')
        except Exception as e:
            break
        if not log:
            _x = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = open(os.devnull, 'w'), open(os.devnull, 'w')
        ans = pipe.process(user_name=name, user_message=msg, output_mode="text")
        if not log:
            sys.stdout, sys.stderr = _x
        print(f'Сергей Петрович: {ans}')

if __name__ == '__main__':
    # use this interface to enable\disable logging on application level
    from utils.logger import logger
    logger.log_mode = "s"

    # names = [f for f in os.listdir('.') if os.path.splitext(f)[-1] == ".wav"]
    # names = sorted(names)
    # print(names)
    # concat_wavs(names, "generated.wav")
    # create_audio("generated3.wav")
    # exit()
    os.environ["HUGGINGFACE_ACCESS_TOKEN"] = os.environ["HF_AUTH"]
    # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true"
    # model_url = 'https://huggingface.co/QuantFactory/Meta-Llama-3-70B-Instruct-GGUF-v2/resolve/main/Meta-Llama-3-70B-Instruct-v2.Q4_K_M.gguf?download=true'
    # model_url = "https://huggingface.co/QuantFactory/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct.Q4_K_M.gguf?download=true"
    quant = "Q4_K_M" # "BF16"#
    model_url=f"https://huggingface.co/kzipa/kap34_8_8_10/resolve/main/kap34_8_8_10.{quant}.gguf?download=true"
    # enable logging
    pipe = Pipeline(model_url=model_url, use_llama_guard=False)
    # quest = get_questions("questions.txt")
    # pipe_on_questions(pipe, quest, output_name="llama3_answers.txt")
    interactive_dialogue(pipe, log=True)
    