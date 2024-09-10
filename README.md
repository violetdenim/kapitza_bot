# kapitza_bot
Source Code for _`Kapitza.AI`_ project
## .env
create local file `.env` with system variables.
```BOT_TOKEN=***
HUGGINGFACE_ACCESS_TOKEN=***
PROMPT_PATH="prompt.txt"
RAG_PATH="docs"
```
Copy `BOT_TOKEN` to access telegram and
`HUGGINGFACE_ACCESS_TOKEN` to access `huggingface.co` if needed

# conda environment
system cuda 12.1
```
conda create -n kap_env python=3.11 && conda activate kap_env && pip install -r requirements.txt
```
# 