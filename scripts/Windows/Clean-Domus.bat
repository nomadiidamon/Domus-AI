@echo off
REM Uninstalls Domus-AI and removes build/Python artifacts via scripts\clean_domus.py.
pushd "%~dp0..\.."
python scripts\clean_domus.py %*
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
