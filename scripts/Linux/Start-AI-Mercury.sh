#!/usr/bin/env bash
# Starts the Mercury model via the generic Start-AI script.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/Start-AI.sh" mercury
