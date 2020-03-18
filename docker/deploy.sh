#!/bin/bash

if [ "$(docker ps -aq -f name=url-loader)" != "" ]; then
    echo "removing exited container"
    docker rm -f url-loader
fi

docker run -d \
--name url-loader \
--restart unless-stopped \
-e ARGS="$*" \
url-loader
