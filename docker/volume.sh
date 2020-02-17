if [[ "$OSTYPE" == "linux-gnu" ]]; then
        docker volume inspect urlloader-volume
elif [[ "$OSTYPE" == "darwin"* ]]; then
        docker volume inspect urlloader-volume
elif [[ "$OSTYPE" == "cygwin" ]]; then
        docker volume inspect urlloader-volume
elif [[ "$OSTYPE" == "msys" ]]; then
        docker volume inspect urlloader-volume
elif [[ "$OSTYPE" == "win32" ]]; then
        docker volume inspect urlloader-volume
elif [[ "$OSTYPE" == "freebsd"* ]]; then
        docker volume inspect urlloader-volume
else
        docker volume inspect urlloader-volume
fi