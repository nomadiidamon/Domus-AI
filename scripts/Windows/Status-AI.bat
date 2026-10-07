@echo off
REM Shows status of running models and hardware.
pushd "%~dp0..\.."
python -m Janus status
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
