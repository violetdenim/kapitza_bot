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

try:
    from utils.logger import UsualLoggedClass
except:
    class UsualLoggedClass: pass

import torch, re

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
                 model_url=f"https://huggingface.co/kzipa/kap34_8_8_10/resolve/main/kap34_8_8_10.Q4_K_M.gguf", #"https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true",
                 use_llama_guard=False, prepare_for_audio=True
                 ):
        """
        prepare_for_audio specifies whether to apply postprocessing or not
        """
        super().__init__()
        self.device = torch.get_default_device()
        documents = SimpleDirectoryReader(rag_folder, recursive=True).load_data() # "data"
        Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_name, device=self.device)
        is_gguf = '.gguf' in model_url
        if not model_url.startswith("http"):
            model_path = model_url
            model_url = None
        else:
            model_path = None
            
        self.model_url = model_url
        self.model_path = model_path
        
        if is_gguf:
            Settings.llm = LlamaCPP(
                # You can pass in the URL to a GGML model to download it automatically
                model_url=model_url,
                # optionally, you can set the path to a pre-downloaded model instead of model_url
                model_path=model_path,
                temperature=0.05,
                max_new_tokens=256,
                context_window=4096,
                # kwargs to pass to __call__()
                generate_kwargs={},
                # kwargs to pass to __init__()
                # set to at least 1 to use GPU
                model_kwargs={"n_gpu_layers": 33, "split_mode": 0, "tensor_split": None, "main_gpu": torch.get_default_device().index},
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
        
        self.use_llama_guard = use_llama_guard
        self.prepare_for_audio = prepare_for_audio
        if prepare_for_audio:
            self.normalizer = RUNorm()
            self.normalizer.load(model_size="big", device=self.device)
        if self.use_llama_guard:
            from llama_index.core.llama_pack import download_llama_pack
            LlamaGuardModeratorPack = download_llama_pack("LlamaGuardModeratorPack")#, "../llamaguard_pack")
            self.llamaguard_pack = LlamaGuardModeratorPack()
        else:
            self.llamaguard_pack = None

    def postprocessing_fn(self, input_str: str):
        processed_str = drop_ending(strip_substr(input_str, ['assistant', ' ', '\n']))
        replacements = {"Вы welcome": "Пожалуйста", "Капиц": "Капиитс"}
        for k, v in replacements.items():
            processed_str = processed_str.replace(k, v)

        if self.prepare_for_audio:
            processed_str = self.normalizer.norm(processed_str)
        
        processed_str = re.sub(r"[ ]+\([ а-яА-Яa-zA-Z0–9]+\)[ ]+", "", processed_str)
        processed_str = re.sub(r"[ ]+\[[ а-яА-Яa-zA-Z0–9]+\][ ]+", "", processed_str)

        return processed_str

    def get_system_prompt(self, user_name, user_gender="F"):
        with open(self.prompt_path, "r", encoding='utf-8') as f:
            self.prompt = '\n'.join(f.readlines())
        self.prompt = self.prompt.replace("{user_name}", user_name)
        self.prompt = self.prompt.replace("{user_gender}", "женщина" if user_gender == "F" else "мужчина")
        date = datetime.datetime.now().date()
        return f"Сегодня {date.day}.{date.month}.{date.year}" + self.prompt
    
    def save_context(self):
        persist_path = self.current_user + ".json"
        self.chat_store.persist(persist_path=persist_path)
        return persist_path 

    def set_engine(self, user_name, user_gender, reset=False, custom_system_prompt=None):
        if user_name is None:
            assert(custom_system_prompt is not None)
        if user_name and reset and os.path.exists(user_name + ".json"):
            os.remove(user_name + ".json")
            self.chat_store = SimpleChatStore()
            print(f"Reseting. Creating chat store for username {user_name}")
        elif not user_name or user_name != self.current_user:
            if self.current_user is not None:
                self.chat_store.persist(persist_path=self.current_user + ".json")
                print(f"Storing chat store for username {self.current_user}")
            if user_name is not None and os.path.exists(user_name + ".json"):
                self.chat_store = SimpleChatStore.from_persist_path(persist_path=user_name + ".json")
                print(f"Loading chat store for username {user_name}")
            else:
                self.chat_store = SimpleChatStore()
                if user_name is None:
                    user_name = "user" # for technical usage of pipeline
                print(f"Creating chat store for username {user_name}")
        else:
            print("set_engine: no effect")
            return
        
        self.current_user = user_name
        
        new_prompt = self.get_system_prompt(self.current_user, user_gender=user_gender) if not custom_system_prompt else custom_system_prompt
        chat_memory = ChatMemoryBuffer.from_defaults(token_limit=8192, chat_store=self.chat_store, chat_store_key=self.current_user)
        self.chat_engine = self.index.as_chat_engine(chat_mode="simple", #"condense_plus_context", 
                                                     memory=chat_memory, 
                                                     system_prompt=new_prompt)
               
    def process_prompt(self, prompt):
        print(f"Current user={self.current_user}")
        if self.use_llama_guard: # quick check of user prompt
            moderator_response_for_input = self.llamaguard_pack.run(prompt)
            if moderator_response_for_input != "safe":
                return "Пожалуй, лучше поговорить на другую тему."
        
        response = self.chat_engine.chat(prompt)
        return self.postprocessing_fn(response.response)

    async def async_process_prompt(self, prompt):
        print(f"Current user={self.current_user}")
        if self.use_llama_guard: # quick check of user prompt
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
                # quick fix: Drop sentence, if English is present
                english_letters = ''.join(chr(c) for c in range(ord('a'), ord('z')+1)) + ''.join(chr(c) for c in range(ord('A'), ord('Z')+1))
                if len(set(text).intersection(english_letters)) == 0:
                    yield self.postprocessing_fn(text)
                text = ""
                
        if len(text):
            yield self.postprocessing_fn(text)

async def _async_test_demo():
    llm = LLMProcessor(os.environ.get("PROMPT_PATH"), os.environ.get("RAG_PATH"))
    llm.set_engine("юзернейм", "M")
    async for sentence in llm.async_process_prompt("Привет"):
        print(sentence)

def _test_demo():
    llm = LLMProcessor(os.environ.get("PROMPT_PATH"), os.environ.get("RAG_PATH"))
    llm.set_engine("юзернейм", "M")
    print(llm.process_prompt("Привет"))

if __name__ == "__main__":
    import torch
    torch.set_default_device(f'cuda:{torch.cuda.device_count()-1}')
    
    _test_demo()
    
    import asyncio
    asyncio.run(_async_test_demo())
    
  