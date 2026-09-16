from mcp.git import run_git

TOOL = {
    "name": "git_status",
    "description": "Show working tree status (short format).",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}


def call(arguments: dict) -> str:
    return run_git("status", "--short", "--branch") or "(clean working tree)"
