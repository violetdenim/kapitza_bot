# kapitza_bot
Source Code for _`Kapitza.AI`_ project
## .env
create local file `.env` with system variables.
```BOT_TOKEN=***
HF_AUTH==***
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

# Docker
```
# build docker container
docker build -t kszipa/kapitza-bot .
docker push kszipa/kapitza-bot
# pull docker container
docker pull kszipa/kapitza-bot
# run existing docker container
docker run --rm --gpus all kszipa/kapitza-bot
# or
docker run --gpus all kszipa/kapitza-bot
```

# Client - Server app
Servers - sends audio to client

Client - uses pipeline to generate audio-answer and sends it back to server

Dockerfile.request - generates container for Server

Dockerfile.response - generates container for Client
```
docker build -t kszipa/kapitza-server -f Dockerfile.request .
docker run -t --network=host kszipa/kapitza-server
docker push kszipa/kapitza-server

docker build -t kszipa/kapitza-client -f Dockerfile.response .
docker run --rm --gpus all -t --network=host kszipa/kapitza-client
docker push kszipa/kapitza-client
```

