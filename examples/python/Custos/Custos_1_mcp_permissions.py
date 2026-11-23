"""
@example Custos_1_mcp_permissions.py

Inspect an MCP profile before exposing tools to an agent.
"""

from Custos import MCPManager


def main() -> None:
    manager = MCPManager()
    model = "Mercury"

    # Reading profile permissions does not launch an MCP server.
    for server, allowed_tools in manager.get_tools(model).items():
        print(f"{server}: {allowed_tools}")

    # Check the exact tool name again when dispatching a tool call.
    print(manager.allow_tool("list_directory", model))


if __name__ == "__main__":
    main()