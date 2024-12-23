@echo off

rem Run static type checker and verify formatting guidelines
python -m mypy strong_typing || exit /b
python -m flake8 strong_typing || exit /b
python -m mypy tests || exit /b
python -m flake8 tests || exit /b

rem Run unit tests
python -m unittest discover || exit /b
