"""
Custos - Security, permissions, and MCP subsystem for Domus-AI.

The security guard of Domus-AI: permissions, trusts, approvals, and
sandboxing. Also home to the Model Context Protocol (MCP) Manager that
agents must go through to perform actions or gain access to any systems.

MCPManager is currently a stub - enable/get_tools/allow_tool are not yet
implemented. See mcp.py.
"""

from .mcp import MCPManager

__all__ = [
    "MCPManager",
]