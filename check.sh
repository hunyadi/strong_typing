set -e

# Run static type checker and verify formatting guidelines
python3 -m mypy strong_typing
python3 -m flake8 strong_typing
python3 -m mypy tests
python3 -m flake8 tests

# Run unit tests
python3 -m unittest discover
