from mcp.filesystem import resolve_safe

TOOL = {
    "name": "search_files",
    "description": "Find files whose name matches a substring, under a directory relative to the project root.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Case-insensitive substring to match in file names"},
            "path": {"type": "string", "description": "Directory to search under (default: project root)"},
        },
        "required": ["pattern"],
    },
}


def call(arguments: dict) -> str:
    root = resolve_safe(arguments.get("path", "."))
    pattern = arguments["pattern"].lower()
    matches = sorted(
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and pattern in p.name.lower()
    )
    return "\n".join(matches) if matches else "(no matches)"
