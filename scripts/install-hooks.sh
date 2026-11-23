#!/bin/sh

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel) || {
    echo "ERROR: Could not locate the Git repository." >&2
    exit 1
}
HOOKS_DIR=$(git -C "$REPO_ROOT" rev-parse --git-path hooks) || {
    echo "ERROR: Could not locate the Git hooks directory." >&2
    exit 1
}
case "$HOOKS_DIR" in
    /*) ;;
    *) HOOKS_DIR="$REPO_ROOT/$HOOKS_DIR" ;;
esac

SOURCE_DIR="$REPO_ROOT/scripts/hooks"
CHILD_SOURCE_DIR="$SOURCE_DIR/pre-commit.d"
CHILD_TARGET_DIR="$HOOKS_DIR/pre-commit.d"

if [ ! -f "$SOURCE_DIR/pre-commit" ] || [ ! -d "$CHILD_SOURCE_DIR" ]; then
    echo "ERROR: Pre-commit hook sources are missing." >&2
    exit 1
fi

mkdir -p "$CHILD_TARGET_DIR"
cp "$SOURCE_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

HOOK_COUNT=0
for hook in "$CHILD_SOURCE_DIR"/*; do
    [ -f "$hook" ] || continue
    cp "$hook" "$CHILD_TARGET_DIR/$(basename "$hook")"
    chmod +x "$CHILD_TARGET_DIR/$(basename "$hook")"
    echo "Installed $(basename "$hook")"
    HOOK_COUNT=$((HOOK_COUNT + 1))
done

if [ "$HOOK_COUNT" -eq 0 ]; then
    echo "ERROR: No pre-commit child hooks were found." >&2
    exit 1
fi

echo "Installed pre-commit dispatcher and $HOOK_COUNT child hooks to $HOOKS_DIR."
