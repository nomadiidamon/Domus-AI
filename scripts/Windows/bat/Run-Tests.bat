@echo off
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0..\ps1\Run-Tests.ps1" %*
pause
