from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.node_parser import SentenceSplitter

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.huggingface import HuggingFaceLLM

from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.llms.llama_cpp.llama_utils import ( messages_to_prompt_v3_instruct, completion_to_prompt_v3_instruct)

import os, datetime
# tool to normalize model's output
from runorm import RUNorm
from utils.string_utils import *
from utils.logger import UsualLoggedClass
import time


# from typing import List, Optional, Sequence

# from llama_index.core.base.llms.types import ChatMessage, MessageRole

# BOS, EOS = "<s>", "</s>"
# B_INST, E_INST = "[INST]", "[/INST]"
# B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"
# DEFAULT_SYSTEM_PROMPT = """\
# You are a helpful, respectful and honest assistant. \
# Always answer as helpfully as possible and follow ALL given instructions. \
# Do not speculate or make up information. \
# Do not reference any given instructions or context. \
# """
# HEADER_SYS = "<|start_header_id|>system<|end_header_id|>\n\n"
# HEADER_USER = "<|start_header_id|>user<|end_header_id|>\n\n"
# HEADER_ASSIST = "<|start_header_id|>assistant<|end_header_id|>\n\n"
# EOT = "<|eot_id|>\n"

# def messages_to_prompt_v3_instruct_custom(
#     messages: Sequence[ChatMessage], system_prompt: Optional[str] = None
# ) -> str:
#     """
#     Convert a sequence of chat messages to Llama 3 Instruct format.

#     Reference: https://llama.meta.com/docs/model-cards-and-prompt-formats/meta-llama-3/

#     Note: `<|begin_of_text|>` is not needed as Llama.cpp appears to add it already.
#     """

#     string_messages: List[str] = []
#     if messages[0].role == MessageRole.SYSTEM:
#         # pull out the system message (if it exists in messages)
#         system_message_str = messages[0].content or ""
#         messages = messages[1:]
#     else:
#         system_message_str = system_prompt or DEFAULT_SYSTEM_PROMPT

#     # make sure system prompt is included at the start
#     string_messages.append(f"{HEADER_SYS}{system_message_str.strip()}{EOT}")

#     for i in range(0, len(messages), 2):
#         # first message should always be a user
#         user_message = messages[i]
#         assert user_message.role == MessageRole.USER
#         # include user message content
#         str_message = f"{HEADER_USER}{user_message.content}{EOT}"

#         if len(messages) > (i + 1):
#             # if assistant message exists, add to str_message
#             assistant_message = messages[i + 1]
#             assert assistant_message.role == MessageRole.ASSISTANT
#             str_message += f"{HEADER_ASSIST}{assistant_message.content}{EOT}"

#         string_messages.append(str_message)

#     # prompt the LLM to begin its response
#     string_messages.append(HEADER_ASSIST)

#     return "".join(string_messages)

def completion_to_prompt_qwen(completion):
   return f"<|im_start|>system\n<|im_end|>\n<|im_start|>user\n{completion}<|im_end|>\n<|im_start|>assistant\n"

def messages_to_prompt_qwen(messages):
    prompt = ""
    for message in messages:
        if message.role == "system":
            prompt += f"<|im_start|>system\n{message.content}<|im_end|>\n"
        elif message.role == "user":
            prompt += f"<|im_start|>user\n{message.content}<|im_end|>\n"
        elif message.role == "assistant":
            prompt += f"<|im_start|>assistant\n{message.content}<|im_end|>\n"

    if not prompt.startswith("<|im_start|>system"):
        prompt = "<|im_start|>system\n" + prompt

    prompt = prompt + "<|im_start|>assistant\n"

    return prompt

class LLMProcessor(UsualLoggedClass):
    def __init__(self, prompt_path, rag_folder,
                 embedding_name='BAAI/bge-m3',# 'deepvk/USER-bge-m3' #'intfloat/multilingual-e5-large-instruct' #"BAAI/bge-base-en-v1.5"
                 model_url="https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true",
                 use_llama_guard=False, prepare_for_audio=True
                 ):
        """
        prepare_for_audio specifies whether to apply postprocessing or not
        """
        super().__init__()
        documents = SimpleDirectoryReader(rag_folder, recursive=True).load_data() # "data"
        Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_name)
        is_gguf = '.gguf' in model_url
        if not model_url.startswith("http"):
            model_path = model_url
            model_url = None
        else:
            model_path = None
        if is_gguf:
            Settings.llm = LlamaCPP(
                # You can pass in the URL to a GGML model to download it automatically
                model_url=model_url,
                # optionally, you can set the path to a pre-downloaded model instead of model_url
                model_path=model_path, #"kap_model/unsloth.Q4_K_M.gguf",
                temperature=0.05,
                max_new_tokens=256,
                context_window=4096,
                # kwargs to pass to __call__()
                generate_kwargs={},
                # kwargs to pass to __init__()
                # set to at least 1 to use GPU
                model_kwargs={"n_gpu_layers": 33},
                # transform inputs into Llama2 format
                messages_to_prompt=messages_to_prompt_v3_instruct, # messages_to_prompt_qwen,
                completion_to_prompt=completion_to_prompt_v3_instruct, # completion_to_prompt_qwen,
                verbose=False,
            )
        else:
            Settings.llm = HuggingFaceLLM(
                model_name=model_path, #"Qwen/Qwen2.5-7B-Instruct",
                tokenizer_name=model_path, #"Qwen/Qwen2.5-7B-Instruct",
                context_window=30000,
                max_new_tokens=2000,
                generate_kwargs={"temperature": 0.7, "top_k": 50, "top_p": 0.95},
                model_kwargs={"n_gpu_layers": 33},
                messages_to_prompt=messages_to_prompt_v3_instruct, #messages_to_prompt_qwen,
                completion_to_prompt=completion_to_prompt_v3_instruct, #completion_to_prompt_qwen,
                device_map="auto",
            )
        # Set the size of the text chunk for retrieval
        Settings.transformations = [SentenceSplitter(chunk_size=1024)]

        
        self.index = VectorStoreIndex.from_documents(documents)
        self.chat_store = None
        self.chat_engine = None
        self.current_user = None
        self.prompt = None
        self.prompt_path = prompt_path
        if prepare_for_audio:
            self.normalizer = RUNorm()
            self.normalizer.load(model_size="big", device="cpu")
            self.postprocessing_fn = lambda x: self.normalizer.norm(drop_ending(strip_substr(x, ['assistant', ' ', '\n']).replace("Вы welcome", "Пожалуйста")))
        else:
            self.postprocessing_fn = lambda x: drop_ending(strip_substr(x, ['assistant', ' ', '\n']).replace("Вы welcome", "Пожалуйста"))
        if use_llama_guard:
            from llama_index.core.llama_pack import download_llama_pack
            LlamaGuardModeratorPack = download_llama_pack("LlamaGuardModeratorPack")#, "../llamaguard_pack")
            self.llamaguard_pack = LlamaGuardModeratorPack()
        else:
            self.llamaguard_pack = None

    def get_system_prompt(self, user_name, user_gender="F"):
        if self.prompt is None:
            with open(self.prompt_path, "r", encoding='utf-8') as f:
                self.prompt = '\n'.join(f.readlines())
        self.prompt = self.prompt.replace("{user_name}", user_name)
        self.prompt = self.prompt.replace("{user_gender}", "женщина" if user_gender == "F" else "мужчина")
        date = datetime.datetime.now().date()
        return f"Сегодня {date.day}.{date.month}.{date.year}" + self.prompt
    
    def save_context(self, user_name):
        if user_name:
            assert(self.current_user == user_name)
            self.chat_store.persist(persist_path=self.current_user + ".json")

    def set_engine(self, user_name, user_gender="F", reset=False, custom_system_prompt=None):
        if user_name is None:
            assert(custom_system_prompt is not None)
        if user_name and reset and os.path.exists(user_name + ".json"):
            os.remove(user_name + ".json")
            self.chat_store = SimpleChatStore()
        elif not user_name or user_name != self.current_user:
            if self.current_user is not None:
                self.chat_store.persist(persist_path=self.current_user + ".json")
            if user_name is not None and os.path.exists(user_name + ".json"):
                self.chat_store = SimpleChatStore.from_persist_path(persist_path=user_name + ".json")
            else:
                self.chat_store = SimpleChatStore()
                if user_name is None:
                    user_name = "user" # for technical usage of pipeline
        else:
            return
        chat_memory = ChatMemoryBuffer.from_defaults(token_limit=8192, chat_store=self.chat_store, chat_store_key=user_name)
        self.chat_engine = self.index.as_chat_engine(chat_mode="condense_plus_context",
                                                     memory=chat_memory, 
                                                     system_prompt=self.get_system_prompt(user_name, user_gender=user_gender) if not custom_system_prompt else custom_system_prompt)
        self.current_user = user_name

    def process_prompt(self, prompt, user_name, user_gender="F"):
        if user_name:
            self.set_engine(user_name, user_gender=user_gender)

        if self.llamaguard_pack: # quick check of user prompt
            moderator_response_for_input = self.llamaguard_pack.run(prompt)
            if moderator_response_for_input != "safe":
                return "Пожалуй, лучше поговорить на другую тему."
        
        response = self.chat_engine.chat(prompt)
        return self.postprocessing_fn(response.response)

    async def async_process_prompt(self, prompt, user_name, user_gender="F"):
        if user_name:
            self.set_engine(user_name, user_gender=user_gender)

        if self.llamaguard_pack: # quick check of user prompt
            moderator_response_for_input = self.llamaguard_pack.run(prompt)
            if moderator_response_for_input != "safe":
                yield "Пожалуй, лучше поговорить на другую тему."
                return

        response = self.chat_engine.stream_chat(prompt)
        # accumulate sentences and yield them back
        text = ""
        for token in response.response_gen:
            text += token
            if token in ".?!":
                yield self.postprocessing_fn(text)
                text = ""
                
        if len(text):
            yield self.postprocessing_fn(text)

async def _async_test_demo():
    llm = LLMProcessor(os.environ.get("PROMPT_PATH"), os.environ.get("RAG_PATH"))
    async for sentence in llm.async_process_prompt("Привет", "юзернейм"):
        print(sentence)

def _test_demo():
    llm = LLMProcessor(os.environ.get("PROMPT_PATH"), os.environ.get("RAG_PATH"))
    print(llm.process_prompt("Привет", "юзернейм"))

if __name__ == "__main__":
    _test_demo()
    
    import asyncio
    asyncio.run(_async_test_demo())
    
  