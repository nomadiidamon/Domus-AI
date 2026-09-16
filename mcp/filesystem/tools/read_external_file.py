from pathlib import Path

from mcp.confirmation import require_user_approval

# Unlike every other filesystem tool, this one reads OUTSIDE the project
# root. The 'confirm' argument in a tools/call request comes from the
# model, so it proves nothing - approval is obtained from the human
# running Domus-AI at call time (see mcp/confirmation.py).

# Marker for the ToolServer host: invoking this tool warrants a
# TOOL_CONFIRMATION_REQUIRED bus event so subscribers can watch for it.
REQUIRES_CONFIRMATION = True

TOOL = {
    "name": "read_external_file",
    "description": (
        "Read a text file OUTSIDE the project root, by absolute path. "
        "The human running the runtime is asked to approve each read."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute path to the file"},
            "max_chars": {"type": "integer", "description": "Optional cap on returned characters"},
        },
        "required": ["path"],
    },
}


def call(arguments: dict) -> str:
    path = Path(arguments["path"]).expanduser()
    if not path.is_absolute():
        raise ValueError(f"external reads require an absolute path: {arguments['path']}")
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {arguments['path']}")

    require_user_approval(
        "read a file outside the project root", str(path)
    )

    content = path.read_text(errors="replace")
    max_chars = arguments.get("max_chars")
    if max_chars is not None:
        content = content[: int(max_chars)]
    return content
