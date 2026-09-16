from mcp.git import run_git

TOOL = {
    "name": "git_diff",
    "description": "Show a diff. Defaults to unstaged changes; pass staged=true for --staged, or ref to diff against a ref.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "Diff staged changes"},
            "ref": {"type": "string", "description": "Diff working tree against this ref"},
            "path": {"type": "string", "description": "Limit the diff to one path"},
        },
        "required": [],
    },
}


def call(arguments: dict) -> str:
    args = ["diff"]
    if arguments.get("staged"):
        args.append("--staged")
    if arguments.get("ref"):
        args.append(arguments["ref"])
    if arguments.get("path"):
        args += ["--", arguments["path"]]
    return run_git(*args) or "(no changes)"
