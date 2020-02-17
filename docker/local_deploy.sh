if [ "$(docker ps -aq -f name=urlloader)" != "" ]; then
    # cleanup
    echo "removing exited container"
    docker rm -f urlloader
fi

ARGS=$*

docker run -d \
--restart always \
-e ARGS="$ARGS" \
-v urlloader-volume:/app \
--name urlloader urlloader