@echo off
REM Starts the Mercury model via the generic Start-AI script.
call "%~dp0Start-AI.bat" mercury
exit /b %errorlevel%
