from mcp.git import run_git

TOOL = {
    "name": "git_commit",
    "description": "Commit staged changes with a message.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message"},
        },
        "required": ["message"],
    },
}


def call(arguments: dict) -> str:
    return run_git("commit", "-m", arguments["message"])
