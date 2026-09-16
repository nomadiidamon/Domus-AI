from mcp.git import run_git

TOOL = {
    "name": "git_add",
    "description": "Stage files for commit.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Paths to stage (use ['.'] for everything)",
            },
        },
        "required": ["paths"],
    },
}


def call(arguments: dict) -> str:
    paths = arguments["paths"]
    run_git("add", *paths)
    return f"staged {len(paths)} path(s)"
