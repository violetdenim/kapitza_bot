# build and push docker containers
# read first argument from command line. It specifies TAG
TAG=$1
echo $TAG
docker build -t kszipa/kapitza:$TAG -f docker/Dockerfile.base .
docker build -t kszipa/kapitza-bot:$TAG -f docker/Dockerfile.bot .
docker build -t kszipa/kapitza-server:$TAG -f docker/Dockerfile.server .
docker build -t kszipa/kapitza-client:$TAG -f docker/Dockerfile.client .

# push them to hub
docker push kszipa/kapitza:$TAG
docker push kszipa/kapitza-bot:$TAG
docker push kszipa/kapitza-server:$TAG
docker push kszipa/kapitza-client:$TAG

