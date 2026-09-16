#!/usr/bin/env bash
# Removes a model from Ollama. Usage: Remove-AI.sh <model>
set -euo pipefail
if [ $# -lt 1 ]; then
    echo "Usage: Remove-AI.sh <model>" >&2
    exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."
PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
exec "$PYTHON" -m Janus remove "$1"
