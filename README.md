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

``` [docker-build.sh]
# build and push docker containers
docker build -t kszipa/kapitza -f docker/Dockerfile.base .
docker build -t kszipa/kapitza-bot -f docker/Dockerfile.bot .
docker build -t kszipa/kapitza-server -f docker/Dockerfile.server .
docker build -t kszipa/kapitza-client -f docker/Dockerfile.client .

# push them to hub
docker push kszipa/kapitza
docker push kszipa/kapitza-bot
docker push kszipa/kapitza-server
docker push kszipa/kapitza-client
```

```
# pull docker containers to target system
docker pull kszipa/kapitza-bot
docker pull kszipa/kapitza-server
docker pull kszipa/kapitza-client

# test docker containers
docker run --rm --gpus all -t --network=host kszipa/kapitza-bot
docker run --rm --gpus all -t --network=host kszipa/kapitza-server
docker run --rm --gpus all -t --network=host kszipa/kapitza-client
```

