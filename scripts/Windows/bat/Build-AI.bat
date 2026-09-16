@echo off
REM Builds a model from its Modelfile. Usage: Build-AI.bat [model]  (default: mercury)
set MODEL=%~1
if "%MODEL%"=="" set MODEL=mercury
pushd "%~dp0..\.."
python -m Janus build %MODEL%
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
