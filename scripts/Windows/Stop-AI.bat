@echo off
REM Stops a model, or all models and the Ollama server. Usage: Stop-AI.bat [model]
pushd "%~dp0..\.."
python -m Janus stop %~1
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
