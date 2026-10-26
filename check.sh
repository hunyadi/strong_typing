#!/bin/sh
#
# Type-safe data interchange for Python data classes.
# https://github.com/hunyadi/strong_typing

set -e

PYTHON_EXECUTABLE=${PYTHON:-python3}

# Run static type checker and verify formatting guidelines
$PYTHON_EXECUTABLE -m ruff check
$PYTHON_EXECUTABLE -m ruff format --check
$PYTHON_EXECUTABLE -m mypy strong_typing
$PYTHON_EXECUTABLE -m mypy tests

# Run unit tests
$PYTHON_EXECUTABLE -m unittest discover
