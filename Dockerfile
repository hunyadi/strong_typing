ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-alpine
RUN python3 -m pip install --upgrade pip
COPY dist/*.whl dist/
RUN python3 -m pip install `ls -1 dist/*.whl`
COPY tests/*.py tests/
RUN python3 -m unittest discover
