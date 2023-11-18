ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-alpine
RUN python3 -m pip install --disable-pip-version-check --upgrade pip
COPY dist/*.whl dist/
RUN python3 -m pip install --disable-pip-version-check `ls -1 dist/*.whl`
COPY tests/*.py tests/
RUN python3 -m unittest discover
