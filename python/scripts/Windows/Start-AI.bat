@echo off
REM Starts a model (Ollama server first if needed). Usage: Start-AI.bat [model]  (default: mercury)
set MODEL=%~1
if "%MODEL%"=="" set MODEL=mercury
pushd "%~dp0..\.."
python -m Janus start %MODEL%
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
