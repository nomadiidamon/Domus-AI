@echo off
REM Runs the full Domus-AI test suite via scripts\run_tests.py.
REM Forwards any extra arguments to pytest.
pushd "%~dp0..\.."
python scripts\run_tests.py %*
set EXITCODE=%errorlevel%
popd
exit /b %EXITCODE%
