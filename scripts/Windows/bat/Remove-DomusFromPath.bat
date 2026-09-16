@echo off
REM Removes the Domus-AI scripts\Windows\bat directory from the user PATH.
setlocal
set "TARGET=%~dp0"
set "TARGET=%TARGET:~0,-1%"

powershell.exe -NoProfile -Command "$d = '%TARGET%'; $p = [Environment]::GetEnvironmentVariable('Path','User'); $e = @(($p -split ';') | Where-Object { $_ -ne '' }); if ($e -notcontains $d) { Write-Host \"[OK] Nothing to remove - not on user PATH: $d\"; exit 0 }; $n = @($e | Where-Object { $_ -ne $d }); [Environment]::SetEnvironmentVariable('Path', ($n -join ';'), 'User'); Write-Host \"[OK] Removed from user PATH: $d\"; Write-Host 'Open a NEW terminal for it to take effect.'"
exit /b %errorlevel%
