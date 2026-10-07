@echo off
REM Starts the Vulcan model via the generic Start-AI script.
call "%~dp0Start-AI.bat" vulcan
exit /b %errorlevel%
