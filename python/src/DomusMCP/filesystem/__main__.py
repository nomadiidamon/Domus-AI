"""Filesystem MCP server package - one module per tool."""

from DomusMCP.server import run_server

if __name__ == "__main__":
    run_server("domus-filesystem", "DomusMCP.filesystem.tools")
