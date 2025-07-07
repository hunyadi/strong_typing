@echo off

rem Run static type checker and verify formatting guidelines
python -m ruff check
if errorlevel 1 goto error
python -m ruff format --check
if errorlevel 1 goto error
python -m mypy strong_typing
if errorlevel 1 goto error
python -m mypy tests
if errorlevel 1 goto error

rem Run unit tests
python -m unittest discover
if errorlevel 1 goto error

goto :EOF

:error
exit /b 1
