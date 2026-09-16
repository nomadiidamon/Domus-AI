from mcp.filesystem import resolve_safe

TOOL = {
    "name": "list_directory",
    "description": "List entries in a directory relative to the project root (dirs end with /).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: project root)"},
        },
        "required": [],
    },
}


def call(arguments: dict) -> str:
    path = resolve_safe(arguments.get("path", "."))
    if not path.is_dir():
        raise NotADirectoryError(f"no such directory: {arguments.get('path', '.')}")
    entries = sorted(
        entry.name + ("/" if entry.is_dir() else "")
        for entry in path.iterdir()
    )
    return "\n".join(entries)
