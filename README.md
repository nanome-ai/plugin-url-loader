# Nanome - URL Loader

A Nanome Plugin to load molecules from a URL.

## Dependencies

[Docker](https://docs.docker.com/get-docker/)

## Usage

To run URL Loader in a Docker container:

```sh
$ cd docker
$ ./build.sh
$ ./deploy.sh -a <plugin_server_address> [optional args]
```

---

In Nanome:

- Activate Plugin
- Click Run
- Enter a molecular code (e.g. "1YUI"), and click "Load"


## Development

To run URL Loader with autoreload:

```sh
$ python3 -m pip install -r requirements.txt
$ python3 run.py -r -a <plugin_server_address> [optional args]
```

## License

MIT
