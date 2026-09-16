"""Fetch MCP server package - one module per tool."""

from mcp.server import run_server

if __name__ == "__main__":
    run_server("domus-fetch", "mcp.fetch.tools")
