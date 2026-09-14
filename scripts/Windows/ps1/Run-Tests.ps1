# Runs the full Domus-AI test suite via the cross-platform scripts/run_tests.py runner.
& python "$PSScriptRoot\..\..\run_tests.py" @args
exit $LASTEXITCODE
