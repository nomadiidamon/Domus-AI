@echo off
REM Adds the Domus-AI scripts\Windows\bat directory to the user PATH.
powershell.exe -NoProfile -Command "$d = '%~dp0'; $d = $d.TrimEnd('\'); $p = [Environment]::GetEnvironmentVariable('Path','User'); $e = @(($p -split ';') | Where-Object { $_ -ne '' }); if ($e -contains $d) { Write-Host \"[OK] Already on user PATH: $d\" } else { [Environment]::SetEnvironmentVariable('Path', (($e + $d) -join ';'), 'User'); Write-Host \"[OK] Added to user PATH: $d\" }; Write-Host 'Open a NEW terminal for it to take effect.'"
exit /b %errorlevel%
