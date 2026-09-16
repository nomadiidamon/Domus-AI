@echo off
REM Starts the Minerva model via the generic Start-AI script.
call "%~dp0Start-AI.bat" minerva
exit /b %errorlevel%
