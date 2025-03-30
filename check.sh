set -e

PYTHON_EXECUTABLE=${PYTHON:-python3}

# Run static type checker and verify formatting guidelines
$PYTHON_EXECUTABLE -m mypy strong_typing
$PYTHON_EXECUTABLE -m flake8 strong_typing
$PYTHON_EXECUTABLE -m mypy tests
$PYTHON_EXECUTABLE -m flake8 tests

# Run unit tests
$PYTHON_EXECUTABLE -m unittest discover
