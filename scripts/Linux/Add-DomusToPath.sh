#!/usr/bin/env bash
# Add-DomusToPath - adds this repo's scripts/Linux directory to PATH
# (persistently via ~/.bashrc) so `Janus <command>` works from anywhere.
# Resolves its own location, so it works no matter where it's invoked from.
set -euo pipefail

# Resolve symlinks so the real repo path ends up on PATH, not a link's dir.
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
RC_FILE="$HOME/.bashrc"
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
echo "(or run scripts/Linux/Remove-DomusFromPath.sh first)."
