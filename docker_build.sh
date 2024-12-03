# build and push docker containers
# read first argument from command line. It specifies TAG
TAG=$1
echo $TAG

docker build -t kszipa/kapitza:$TAG --build-arg TAG=$TAG -f docker/Dockerfile.base . #--no-cache 
docker build -t kszipa/kapitza-bot:$TAG --build-arg TAG=$TAG -f docker/Dockerfile.bot . 
docker build -t kszipa/kapitza-server:$TAG --build-arg TAG=$TAG -f docker/Dockerfile.server . 
docker build -t kszipa/kapitza-client:$TAG --build-arg TAG=$TAG -f docker/Dockerfile.client .

# push them to hub
docker push kszipa/kapitza:$TAG
docker push kszipa/kapitza-bot:$TAG
docker push kszipa/kapitza-server:$TAG
docker push kszipa/kapitza-client:$TAG

