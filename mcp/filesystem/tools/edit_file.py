from mcp.filesystem import resolve_safe

TOOL = {
    "name": "edit_file",
    "description": (
        "Replace a line range in a text file with new content. "
        "Lines are 1-indexed and inclusive on both ends."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to project root"},
            "start_line": {"type": "integer", "description": "First line to replace (1-indexed)"},
            "end_line": {"type": "integer", "description": "Last line to replace (inclusive)"},
            "content": {"type": "string", "description": "Replacement text for that range"},
        },
        "required": ["path", "start_line", "end_line", "content"],
    },
}


def call(arguments: dict) -> str:
    path = resolve_safe(arguments["path"])
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {arguments['path']}")

    start = int(arguments["start_line"])
    end = int(arguments["end_line"])
    if start < 1:
        raise ValueError("start_line must be >= 1")
    if end < start:
        raise ValueError(f"end_line ({end}) must be >= start_line ({start})")

    lines = path.read_text(errors="replace").splitlines(keepends=True)
    if end > len(lines):
        raise ValueError(
            f"end_line ({end}) beyond end of file ({len(lines)} lines)"
        )

    replacement = arguments["content"]
    if replacement and not replacement.endswith("\n"):
        replacement += "\n"

    lines[start - 1 : end] = [replacement]
    path.write_text("".join(lines))

    return (
        f"replaced lines {start}-{end} of {arguments['path']} "
        f"({end - start + 1} line(s) -> {replacement.count(chr(10))} line(s))"
    )
