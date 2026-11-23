"""
Lares.permissions - agent-scoped view over Custos's MCP permissions.

Custos.MCPManager is the actual source of truth for what a model may do
(reads mcp/servers.json and mcp/profiles/<Model>.json). This module does
not duplicate or override any of that - it's a thin, agent-shaped
convenience wrapper so Lares.Agent and its callers ask "may this agent
use this tool" without reaching into Custos directly or juggling model
name strings. It also folds in one extra agent-level gate that Custos
has no concept of: AgentProfile.supports_tool_calls (see Lares.profiles)
- a model whose base has no tool-calling grammar at all should never be
offered tools in the first place, independent of what its MCP profile
permits.
"""

from typing import TYPE_CHECKING, Dict, List, Optional

from Custos.mcp import MCPConfigError, MCPManager, ProfileNotFoundError

if TYPE_CHECKING:
    from Lares.profiles import AgentProfile

__all__ = ["AgentPermissions"]


class AgentPermissions:
    """
    Permission surface for one agent (one model + its AgentProfile).

    Args:
        model: The model name (matches an mcp/profiles/<Model>.json file,
               via profile.effective_mcp_profile_name()).
        profile: The agent's AgentProfile (see Lares.profiles.get_profile).
        manager: Optional MCPManager to use instead of a fresh one -
                 mainly for tests; a fresh MCPManager is cheap (it just
                 lazily reads JSON files) so sharing one isn't required.

    @todo: Try to integrate this as a sub-class of mcp.py's Permission class 
    """

    def __init__(self, model: str, profile: "AgentProfile",
                 manager: Optional[MCPManager] = None):
        self.model = model
        self.profile = profile
        self._manager = manager or MCPManager()

    @property
    def manager(self) -> MCPManager:
        return self._manager

    def has_mcp_profile(self) -> bool:
        """Whether mcp/profiles/<...>.json exists for this agent at all."""
        try:
            self._manager.get_tools(self.profile.effective_mcp_profile_name())
            return True
        except ProfileNotFoundError:
            return False

    def tools_allowed(self) -> bool:
        """
        Whether this agent should be offered tools at all. False if the
        model's base can't do native tool calls (AgentProfile.
        supports_tool_calls), or if it has no MCP profile, independent
        of whether any individual server/tool is granted.
        """
        if not self.profile.supports_tool_calls:
            return False
        return self.has_mcp_profile()

    def get_tools(self) -> Dict[str, List[str]]:
        """
        The tool allowlist for this agent, keyed by MCP server name - see
        Custos.MCPManager.get_tools. Returns {} (not an error) if tools
        aren't allowed for this agent at all (see tools_allowed), or if
        the profile is missing - callers that need to distinguish "no
        profile" from "profile grants nothing" should use
        has_mcp_profile()/tools_allowed() directly.
        """
        if not self.tools_allowed():
            return {}
        try:
            return self._manager.get_tools(self.profile.effective_mcp_profile_name())
        except (ProfileNotFoundError, MCPConfigError):
            return {}

    def allow_tool(self, tool_name: str) -> bool:
        """Whether this agent may call `tool_name` right now."""
        if not self.profile.supports_tool_calls:
            return False
        try:
            return self._manager.allow_tool(
                tool_name, self.profile.effective_mcp_profile_name()
            )
        except MCPConfigError:
            return False

    def get_server_config(self, server: str) -> Dict[str, object]:
        """Pass-through to MCPManager.get_server_config, for launching an
        MCP server the agent is permitted to use."""
        return self._manager.get_server_config(server)