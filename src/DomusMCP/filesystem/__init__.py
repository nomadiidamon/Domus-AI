"""Filesystem MCP server - local file tools scoped to the host project root."""

import os
from pathlib import Path


def resolve_safe(path: str) -> Path:
    """
    Resolve a tool-supplied path against the host project root, refusing
    anything that escapes it. Falls back to cwd when no host is set (e.g.
    standalone use outside the runtime).
    """
    root = Path(os.environ.get("LOCAL_AI_RUNTIME_HOST", Path.cwd())).resolve()
    resolved = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path escapes project root: {path}")
    return resolved
