"""Git MCP server package - one module per tool."""

from DomusMCP.server import run_server

if __name__ == "__main__":
    run_server("domus-git", "DomusMCP.git.tools")
