import sys
import os
import dotenv
os.system("pip install -U accelerate")
from src.llm import LLMProcessor
from src.tts import TTSProcessor
from src.asr import ASRProcessor


# load global variables from local .env file
dotenv.load_dotenv()


class Pipeline:
    def __init__(self,
                 model_url=f"https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true",
                 use_llama_guard=False):
        # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-GGUF/resolve/main/Meta-Llama-3.1-8B.Q4_K_M.gguf?download=true"
        hf_token = os.environ.get('HF_AUTH')
        self.asr = ASRProcessor(hf_token=hf_token)
        self.llm = LLMProcessor(os.environ.get(
            "PROMPT_PATH"), os.environ.get("RAG_PATH"),
            model_url=model_url,
            use_llama_guard=use_llama_guard)
        self.tts = TTSProcessor(os.environ.get(
            "AUDIO_PATH"), hf_token=hf_token)

    def set_user(self, user_name):
        self.llm.set_engine(user_name)

    def save_context(self, user_name):
        self.llm.save_context(user_name)

    def process(self, user_name, file_to_process=None, user_message=None, output_mode='audio'):
        assert ((file_to_process is None) ^ (user_message is None))
        self.llm.set_engine(user_name, reset=True)
        if user_message is None:
            user_message = self.asr.get_text(file_to_process)
        if len(user_message) == 0:
            return None, "Прошу прощения, не расслышал."
        else:
            answer = self.llm.process_prompt(user_message, user_name)
        if output_mode == "text":
            return answer
        return self.tts.get_audio(answer, format=".wav" if output_mode == "audio" else ".ogg")

def create_audio():
    tts = TTSProcessor(os.environ.get("AUDIO_PATH"), hf_token=os.environ.get('HF_AUTH'))
    text = """ОчвИИдное с Сергеем Капицей.
    Ведет передачу ИИ-двойник Сергея Капицы.
Здравствуйте! С вами ИИ-двойник Сергея Капицы. 

Сегодня мы поговорим о том, как создаются такие, как я. А точнее, о внешности
Чтобы «воссоздать» человека в цифровом мире, нужно его заснять.
Для этого потребуется специальная сфера с камерами высокого разрешения
Или телефон с отличной камерой и время
Уже сейчас на 3D-моделях реальных людей
Ученые учат искусственный интеллект
Распознавать человеческие эмоции или изменения во внешности
С моим прототипом сложнее
Хотя Сергей Капица работал на телевидении
Задачи — снимать его в деталях
и в высоком разрешении никогда не было
Так что же делали мои создатели
Чтобы мой образ был точнее?
Сперва с помощью нейросетей они создали 3D-модель головы
Получилось очень далеко от оригинала — из-за неправдоподобной текстуры
Поэтому они взяли большой массив видео, улучшили качество с помощью нейросетей
и добавили детали на 3D-модель
Стало чуть лучше, но все еще плохо
Поэтому было решено надеть поверх 3D-модели deepfake
В этом варианте текстуру кожи для каждого кадра этого видео генерирует отдельная нейросеть
Так получился текущий вариант
Команда проекта продолжает меня улучшать
И работает над деталями
Об этом вы можете узнать на странице проекта
До новых встреч на “Техпросвете”!
"""
    print(tts.get_audio(text, format=".wav"))

if __name__ == '__main__':
    create_audio()
    exit()
    os.environ["HUGGINGFACE_ACCESS_TOKEN"] = os.environ["HF_AUTH"]
    # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true"
    # model_url = 'https://huggingface.co/QuantFactory/Meta-Llama-3-70B-Instruct-GGUF-v2/resolve/main/Meta-Llama-3-70B-Instruct-v2.Q4_K_M.gguf?download=true'
    quant = "BF16"#"Q4_K_M"
    model_url = f"/home/zipa/DataFromD/lara_pc_data/kap34_8_8_10.{quant}.gguf"#.gguf"

    pipe = Pipeline(model_url=model_url, use_llama_guard=False)
    predefined = False
    if predefined:
        for msg in [ "Здравствуйте, Сергей Петрович!",
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
        "Уничтожит ли нас Искусственный Интеллект?"]:
            _x = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = open(os.devnull, 'w'), open(os.devnull, 'w')
            result = pipe.process(user_name="Василий", user_message=msg,  output_mode="text")
            sys.stdout, sys.stderr = _x
            print(f"Василий: {msg}")
            print(f"Сергей Петрович: {result}")
    else:
        name = input("Здравствуйте! Меня зовут Сергей Петрович Капица. А Вас? >")
        name = name.strip(' ')
        print(f"Очень приятно, {name}. Давайте продолжим разговор!")
        while True:
            try:
                msg = input(f'{name}: ')
            except Exception as e:
                break
            _x = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = open(os.devnull, 'w'), open(os.devnull, 'w')
            ans = pipe.process(user_name=name, user_message=msg, output_mode="text")
            sys.stdout, sys.stderr = _x
            print(f'Сергей Петрович: {ans}')