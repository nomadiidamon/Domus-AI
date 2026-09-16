from mcp.git import run_git

TOOL = {
    "name": "git_log",
    "description": "Show recent commit history (one line per commit).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "description": "Number of commits (default 10)"},
        },
        "required": [],
    },
}


def call(arguments: dict) -> str:
    count = int(arguments.get("count", 10))
    return run_git("log", "--oneline", f"-{count}")
