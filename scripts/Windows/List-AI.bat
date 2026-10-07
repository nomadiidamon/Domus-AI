@echo off
REM Lists models installed in Ollama.
pushd "%~dp0..\.."
python -m Janus list
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
