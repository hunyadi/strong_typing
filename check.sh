set -e

PYTHON=python3

# Run static type checker and verify formatting guidelines
$PYTHON -m mypy strong_typing
$PYTHON -m flake8 strong_typing
$PYTHON -m mypy tests
$PYTHON -m flake8 tests

# Run unit tests
$PYTHON -m unittest discover
