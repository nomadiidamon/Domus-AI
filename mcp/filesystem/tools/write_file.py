from mcp.filesystem import resolve_safe

TOOL = {
    "name": "write_file",
    "description": "Write text content to a file relative to the project root (creates parents).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to project root"},
            "content": {"type": "string", "description": "Text content to write"},
        },
        "required": ["path", "content"],
    },
}


def call(arguments: dict) -> str:
    path = resolve_safe(arguments["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(arguments["content"])
    return f"wrote {len(arguments['content'])} characters to {arguments['path']}"
