@echo off

rem Clear %ERRORLEVEL%
ver > nul

rem Clean up output from previous runs
if exist dist rmdir /s /q dist
if errorlevel 1 goto error
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"
if errorlevel 1 goto error

rem Run static type checker and unit tests
call check.bat
if errorlevel 1 goto error

rem Create PyPI package for distribution
python -m build --sdist --wheel
if errorlevel 1 goto error

goto :EOF

:error
exit /b 1
