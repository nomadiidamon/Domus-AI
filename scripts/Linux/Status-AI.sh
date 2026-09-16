#!/usr/bin/env bash
# Shows status of running models and hardware.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."
PYTHON="python3"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
exec "$PYTHON" -m Janus status
