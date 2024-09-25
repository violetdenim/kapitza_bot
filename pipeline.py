import os
import dotenv

from src.llm import LLMProcessor
from src.tts import TTSProcessor
from src.asr import ASRProcessor


# load global variables from local .env file
dotenv.load_dotenv()


class Pipeline:
    def __init__(self,
                 model_url=f"https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true"):
        # model_url = "https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-GGUF/resolve/main/Meta-Llama-3.1-8B.Q4_K_M.gguf?download=true"
        hf_token = os.environ.get('HF_AUTH')
        self.asr = ASRProcessor(hf_token=hf_token)
        self.llm = LLMProcessor(os.environ.get(
            "PROMPT_PATH"), os.environ.get("RAG_PATH"), model_url=model_url)
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
    user_name = "Василий"
    file_to_process = f"voice_note.wav"
    output_mode = "audio"
    pipe = Pipeline()
    result = pipe.process(user_name=user_name,
                          file_to_process=file_to_process, output_mode="audio")
