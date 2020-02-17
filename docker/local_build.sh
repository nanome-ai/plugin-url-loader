if [[ $(docker volume ls -f name=urlloader-volume -q) ]]; then
    echo "Skipping volume creation"
else
    echo "Creating new docker volume"
    docker volume create urlloader-volume
fi

docker build -f .Dockerfile -t urlloader:latest ..