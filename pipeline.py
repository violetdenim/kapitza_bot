import sys
import os
import dotenv

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


if __name__ == '__main__':
    # result = pipe.process(user_name="Василий",
    #                       file_to_process=f"voice/1.wav", output_mode="audio")
    # print(f"Answer to Василий saved to {result}")
    
    msg = "Здравствуйте, Сергей Петрович!"
    # override system outputs
    default_out, default_err = sys.stdout, sys.stderr
    with open(os.devnull, 'w'), open(os.devnull, 'w') as sys.stdout, sys.stderr:
        sys.stderr = open(os.devnull, 'w')
        pipe = Pipeline(use_llama_guard=False)
        result = pipe.process(user_name="Василий", user_message=msg, output_mode="text")
    sys.stdout, sys.stderr = default_out, default_err
    print(f"Василий: {msg}")
    print(f"Сергей Петрович: {result}")