"""Fetch MCP server package - one module per tool."""

from DomusMCP.server import run_server

if __name__ == "__main__":
    run_server("domus-fetch", "DomusMCP.fetch.tools")
