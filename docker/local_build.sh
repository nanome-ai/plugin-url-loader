if [[ $(docker volume ls -f name=url-loader-volume -q) ]]; then
    echo "Skipping volume creation"
else
    echo "Creating new docker volume"
    docker volume create url-loader-volume
fi

docker build -f urlloader.Dockerfile -t urlloader:latest ..