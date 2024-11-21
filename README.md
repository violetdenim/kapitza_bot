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

```
# ./docker_build.sh latest
# build and push docker containers
docker build -t kszipa/kapitza -f docker/Dockerfile.base .
docker build -t kszipa/kapitza-bot -f docker/Dockerfile.bot .
docker build -t kszipa/kapitza-server -f docker/Dockerfile.server .
docker build -t kszipa/kapitza-client -f docker/Dockerfile.client .

# push them to hub
docker push kszipa/kapitza:folder_service
docker push kszipa/kapitza-bot:folder_service
docker push kszipa/kapitza-server:folder_service
docker push kszipa/kapitza-client:folder_service
```

```
# pull docker containers to target system
docker pull kszipa/kapitza:folder_service
docker pull kszipa/kapitza-bot:folder_service
docker pull kszipa/kapitza-server:folder_service
docker pull kszipa/kapitza-client:folder_service

# test docker containers
docker run --rm --gpus all -it --network=host kszipa/kapitza:folder_service
docker run --rm --gpus all -t --network=host kszipa/kapitza-bot:folder_service
docker run --rm --gpus all -t --network=host kszipa/kapitza-server:folder_service
docker run --rm --gpus all -t --network=host kszipa/kapitza-client:folder_service
```

Запуск и настройка интерактивного контейнера:
```
docker run --rm --gpus all -it --network=host kszipa/kapitza:folder_service
```
```
conda init
source /root/.bashrc
conda activate kap_env
python local_folder_service.py
```
Attach second shell to the running container:
```
docker ps
# insert suited container index into command below
docker exec -ti {cid} sh
```