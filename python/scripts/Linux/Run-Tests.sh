#!/usr/bin/env bash
# Runs the full Domus-AI test suite via the cross-platform scripts/run_tests.py runner.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"

"$PYTHON" "$SCRIPT_DIR/../run_tests.py" "$@"
