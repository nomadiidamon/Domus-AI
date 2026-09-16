#!/bin/zsh
# Add-DomusToPath - adds this repo's scripts/MacOS directory to PATH
# (persistently via ~/.zshrc) so `Janus <command>` works from anywhere.
# Resolves its own location, so it works no matter where it's invoked from.
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${0:A}")" && pwd)"
RC_FILE="$HOME/.zshrc"
MARKER="# Domus-AI scripts"

if [[ ! -f "$SCRIPT_DIR/Janus.sh" ]]; then
    echo "[X] Cannot locate Janus.sh next to this script ($SCRIPT_DIR) - is the repo intact?"
    exit 1
fi

if [[ ":$PATH:" == *":$SCRIPT_DIR:"* ]]; then
    echo "[OK] Already on PATH for this session: $SCRIPT_DIR"
elif grep -qF "$SCRIPT_DIR" "$RC_FILE" 2>/dev/null; then
    echo "[OK] Already persisted in $RC_FILE"
else
    {
        echo ""
        echo "$MARKER"
        echo "export PATH=\"\$PATH:$SCRIPT_DIR\""
    } >> "$RC_FILE"
    echo "[OK] Added to $RC_FILE"
fi

echo ""
echo "To use it in this shell right now:"
echo "  export PATH=\"\$PATH:$SCRIPT_DIR\""
echo "Then:  Janus list"
echo ""
echo "Note: the PATH entry points at this repo's current location."
echo "If you move the repo, rerun this script from the new location"
echo "(or run scripts/MacOS/Remove-DomusFromPath.sh first)."
