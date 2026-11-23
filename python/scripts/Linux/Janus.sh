#!/usr/bin/env bash
# Janus - Domus-AI CLI launcher.
# Add this directory to PATH to run `janus <command>` from anywhere.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"

PYTHONPATH="$PYTHON_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m Janus "$@"
