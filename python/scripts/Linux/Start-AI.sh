#!/usr/bin/env bash
# Starts a model (Ollama server first if needed). Usage: Start-AI.sh [model]  (default: mercury)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."
PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
exec "$PYTHON" -m Janus start "${1:-mercury}"
