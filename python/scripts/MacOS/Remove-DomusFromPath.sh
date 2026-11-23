#!/bin/zsh
# Remove-DomusFromPath - removes the Domus-AI scripts PATH entry from
# ~/.zshrc (the block added by Add-DomusToPath.sh).
set -euo pipefail

RC_FILE="$HOME/.zshrc"
MARKER="# Domus-AI scripts"

if [[ ! -f "$RC_FILE" ]] || ! grep -qF "$MARKER" "$RC_FILE"; then
    echo "[OK] Nothing to remove - no Domus-AI entry found in $RC_FILE"
    exit 0
fi

# Delete the marker line and the export line that follows it.
sed -i '' "/# Domus-AI scripts/,+1d" "$RC_FILE"
echo "[OK] Removed Domus-AI PATH entry from $RC_FILE"
echo "Open a new terminal (or 'source ~/.zshrc') for it to take effect."
