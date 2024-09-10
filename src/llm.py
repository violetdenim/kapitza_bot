from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.llms.huggingface import HuggingFaceLLM
from transformers import BitsAndBytesConfig

from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.llms.llama_cpp.llama_utils import (
    messages_to_prompt,
    completion_to_prompt,
)

from runorm import RUNorm
from src.utils import *
import os

normalizer = RUNorm()
normalizer.load(model_size="big", device="cpu")

llamaguard_pack = None
# from llama_index.core.llama_pack import download_llama_pack
# os.environ["HUGGINGFACE_ACCESS_TOKEN"] = "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"
# LlamaGuardModeratorPack = download_llama_pack("LlamaGuardModeratorPack", "./llamaguard_pack")
# llamaguard_pack = LlamaGuardModeratorPack()

from llama_index.llms.llama_cpp.llama_utils import (
    messages_to_prompt_v3_instruct,
    completion_to_prompt_v3_instruct,
)

class LLMProcessor:
    def __init__(self, prompt_path, rag_folder):
        documents = SimpleDirectoryReader(rag_folder, recursive=True).load_data()#"data"
        
        embedding_name='BAAI/bge-m3'
        #'deepvk/USER-bge-m3' 
        #'intfloat/multilingual-e5-large-instruct'
        #"BAAI/bge-base-en-v1.5"

        Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_name)
        Settings.llm = LlamaCPP(
            # You can pass in the URL to a GGML model to download it automatically
            model_url="https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true",
            # optionally, you can set the path to a pre-downloaded model instead of model_url
            model_path=None, #"kap_model/unsloth.Q4_K_M.gguf",
            temperature=0.05,
            max_new_tokens=256,
            context_window=4096,
            # kwargs to pass to __call__()
            generate_kwargs={},
            # kwargs to pass to __init__()
            # set to at least 1 to use GPU
            model_kwargs={"n_gpu_layers": 33},
            # transform inputs into Llama2 format
            messages_to_prompt=messages_to_prompt_v3_instruct,
            completion_to_prompt=completion_to_prompt_v3_instruct,
            verbose=True,
        )
        
        self.index = VectorStoreIndex.from_documents(documents)
        
        self.chat_store = None
        self.chat_engine = None
        self.current_user = None
        self.prompt = None
        self.prompt_path = prompt_path
        self.postprocessing_fn = lambda x: normalizer.norm(drop_ending(strip_substr(x, ['assistant', ' ', '\n'])))

    def get_system_prompt(self, user_name):
        if self.prompt is None:
            with open(self.prompt_path, "r") as f:
                self.prompt = '\n'.join(f.readlines())
                print(self.prompt)
        return self.prompt
    
    def save_context(self, user_name):
        assert(self.current_user == user_name)
        self.chat_store.persist(persist_path=self.current_user + ".json")

    def set_engine(self, user_name, reset=False):
        if reset and os.path.exists(user_name + ".json"):
            os.remove(user_name + ".json")
            self.chat_store = SimpleChatStore()
            print("Creating new chat store")
        elif user_name != self.current_user:
            if self.current_user is not None:
                self.chat_store.persist(persist_path=self.current_user + ".json")
            if os.path.exists(user_name + ".json"):
                self.chat_store = SimpleChatStore.from_persist_path(persist_path=user_name + ".json")
                print(f"Creating {user_name} chat store")
            else:
                self.chat_store = SimpleChatStore()
                print("Creating new chat store")
        else:
            return
        chat_memory = ChatMemoryBuffer.from_defaults(token_limit=4096,
                                                     chat_store=self.chat_store, chat_store_key=user_name)
        self.chat_engine = self.index.as_chat_engine(chat_mode="condense_plus_context",
                                                     memory=chat_memory,
                                                     system_prompt=self.get_system_prompt(user_name))
        self.current_user = user_name
        

    def process_prompt(self, prompt, user_name):
        self.set_engine(user_name)
        if llamaguard_pack:
            moderator_response_for_input = llamaguard_pack.run(prompt)
            print(f"moderator response for input: {moderator_response_for_input}")

            # Check if the moderator response for input is safe
            if moderator_response_for_input == "safe":
                response = self.chat_engine.chat(prompt) #query_engine.query(query)

                # Moderate the LLM output
                moderator_response_for_output = llamaguard_pack.run(str(response))
                print(
                    f"moderator response for output: {moderator_response_for_output}"
                )
                # Check if the moderator response for output is safe
                if moderator_response_for_output != "safe":
                    response = None
            else:
                response = None
            # response = self.chat_engine.chat(prompt)
            if response is None:
                return "Пожалуй, лучше поговорить на другую тему."
        else:
             response = self.chat_engine.chat(prompt)
        # return normalizer.norm(drop_ending(strip_substr(response.response, ['assistant', ' ', '\n'])))
        return self.postprocessing_fn(response.response)
  