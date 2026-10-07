"""Git MCP server - local git operations scoped to the host project root."""

import os
import subprocess
from pathlib import Path


def run_git(*args: str) -> str:
    """Run a git command in the host project root and return its output."""
    cwd = Path(os.environ.get("LOCAL_AI_RUNTIME_HOST", Path.cwd())).resolve()
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()
