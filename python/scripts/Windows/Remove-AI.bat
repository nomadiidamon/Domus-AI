@echo off
REM Removes a model from Ollama. Usage: Remove-AI.bat [model]
if "%~1"=="" (
    echo Usage: Remove-AI.bat ^<model^>
    exit /b 1
)
pushd "%~dp0..\.."
python -m Janus remove %~1
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
