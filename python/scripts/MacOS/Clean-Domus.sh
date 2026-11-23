#!/usr/bin/env bash
# Uninstalls Domus-AI and removes build/Python artifacts via scripts/clean_domus.py.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"

"$PYTHON" "$SCRIPT_DIR/../clean_domus.py" "$@"
