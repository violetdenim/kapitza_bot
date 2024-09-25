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