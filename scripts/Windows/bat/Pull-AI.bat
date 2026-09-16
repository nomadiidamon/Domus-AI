@echo off
REM Downloads a model from the Ollama registry. Usage: Pull-AI.bat <model>
if "%~1"=="" (
    echo Usage: Pull-AI.bat ^<model^>
    exit /b 1
)
pushd "%~dp0..\.."
python -m Janus pull %~1
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
