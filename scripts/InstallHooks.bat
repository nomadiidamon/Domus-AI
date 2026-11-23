@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT="
for /f "delims=" %%R in ('git -C "%SCRIPT_DIR%.." rev-parse --show-toplevel 2^>nul') do set "REPO_ROOT=%%R"

if not defined REPO_ROOT (
    echo ERROR: Could not locate the Git repository.
    if /I not "%1"=="nopause" pause
    exit /b 1
)

pushd "%REPO_ROOT%"
set "HOOKS_DIR="
for /f "delims=" %%H in ('git rev-parse --git-path hooks 2^>nul') do set "HOOKS_DIR=%%H"

if not defined HOOKS_DIR (
    echo ERROR: Could not locate the Git hooks directory.
    popd
    if /I not "%1"=="nopause" pause
    exit /b 1
)

set "INSTALL_FAILED=0"
set "HOOK_COUNT=0"
if not exist "%HOOKS_DIR%\pre-commit.d" mkdir "%HOOKS_DIR%\pre-commit.d"

echo Installing pre-commit dispatcher...
copy /Y "%SCRIPT_DIR%hooks\pre-commit" "%HOOKS_DIR%\pre-commit" >nul
if errorlevel 1 (
    echo [FAILED] Could not install pre-commit dispatcher.
    set "INSTALL_FAILED=1"
) else (
    echo [OK] Installed pre-commit dispatcher.
)

for %%F in ("%SCRIPT_DIR%hooks\pre-commit.d\*") do (
    if exist "%%~fF" (
        copy /Y "%%~fF" "%HOOKS_DIR%\pre-commit.d\%%~nxF" >nul
        if errorlevel 1 (
            echo [FAILED] Could not install %%~nxF.
            set "INSTALL_FAILED=1"
        ) else (
            echo [OK] Installed %%~nxF.
            set /a HOOK_COUNT+=1
        )
    )
)

if "%HOOK_COUNT%"=="0" (
    echo ERROR: No pre-commit child hooks were found.
    set "INSTALL_FAILED=1"
)

popd
if "%INSTALL_FAILED%"=="0" (
    echo All pre-commit hooks are installed.
) else (
    echo ERROR: One or more hooks failed to install.
)

if /I not "%1"=="nopause" pause
if "%INSTALL_FAILED%"=="0" exit /b 0
exit /b 1