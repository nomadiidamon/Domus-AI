#!/bin/zsh
# Janus - Domus-AI CLI launcher (macOS).
# Prefers the installed `janus` console script; falls back to python -m Janus.
# Add this directory to your PATH to run `Janus <command>` from anywhere.
set -euo pipefail

if command -v janus >/dev/null 2>&1; then
    exec janus "$@"
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
exec python -m Janus "$@"
