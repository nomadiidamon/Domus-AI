@echo off
REM Janus - Domus-AI CLI launcher (Windows).
REM Prefers the installed `janus` console script; falls back to python -m Janus.
where janus >nul 2>nul
if %errorlevel%==0 (
    janus %*
    exit /b %errorlevel%
)
pushd "%~dp0..\.."
python -m Janus %*
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
