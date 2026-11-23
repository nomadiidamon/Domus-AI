"""
Custos - Security, permissions, and MCP subsystem for Domus-AI.

The security guard of Domus-AI: permissions, trusts, approvals, and
sandboxing. Also home to the Model Context Protocol (MCP) Manager that
agents must go through to perform actions or gain access to any systems.

MCPManager reads mcp/servers.json and mcp/profiles/<Model>.json to gate
which MCP servers and tools each model may use. Permission/Approval are
scaffolding for a future approval workflow and are not enforced yet.
"""

from .mcp import (
    Approval,
    MCPConfigError,
    MCPManager,
    Permission,
    ProfileNotFoundError,
    filter_tools_for_model,
    mcp_tools_to_ollama_tools,
)
from .mcp_client import MCPClient, MCPClientError

__all__ = [
    "Approval",
    "MCPClient",
    "MCPClientError",
    "MCPConfigError",
    "MCPManager",
    "Permission",
    "ProfileNotFoundError",
    "filter_tools_for_model",
    "mcp_tools_to_ollama_tools",
]