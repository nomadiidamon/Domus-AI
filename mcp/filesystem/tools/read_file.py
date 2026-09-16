from mcp.filesystem import resolve_safe

TOOL = {
    "name": "read_file",
    "description": "Read the contents of a text file relative to the project root.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to project root"},
            "max_chars": {"type": "integer", "description": "Optional cap on returned characters"},
        },
        "required": ["path"],
    },
}


def call(arguments: dict) -> str:
    path = resolve_safe(arguments["path"])
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {arguments['path']}")
    content = path.read_text(errors="replace")
    max_chars = arguments.get("max_chars")
    if max_chars is not None:
        content = content[: int(max_chars)]
    return content
