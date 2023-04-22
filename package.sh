set -e
if [ -d dist ]; then rm -rf dist; fi
if [ -d json_strong_typing.egg-info ]; then rm -rf json_strong_typing.egg-info; fi
python3 -m build
docker build --build-arg PYTHON_VERSION=3.8 .
docker build --build-arg PYTHON_VERSION=3.9 .
docker build --build-arg PYTHON_VERSION=3.10 .
docker build --build-arg PYTHON_VERSION=3.11 .
