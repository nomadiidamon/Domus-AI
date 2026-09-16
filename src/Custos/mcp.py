"""
Custos.mcp - MCP server and tool-permission management.

Reads two config files (both resolved relative to the Domus-AI project
root via Janus.paths.get_mcp_path() unless overridden):

  mcp/servers.json
      {
        "servers": {
          "<serverName>": {
            "command": str, "args": [str], "env": {str: str},
            "transport": "stdio" | "sse", "description": str
          }
        }
      }

  mcp/profiles/<Model>.json   (one per model)
      {
        "model": str,
        "servers": ["<serverName>", ...],
        "allowed_tools": { "<serverName>": ["<tool>", ...] | ["*"] }
      }

MCPManager answers three questions for the rest of the runtime:
  - enable(agent, server):  may this agent use this MCP server?
  - get_tools(model):       which tools does this model's profile grant?
  - allow_tool(tool, model): is this specific tool call permitted?

Full sandboxing/approval workflows are intentionally out of scope for
now - Permission/Approval below are scaffolding placeholders for that
future work.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MCPConfigError(RuntimeError):
    """Raised when servers.json or a profile file is missing or malformed."""


class ProfileNotFoundError(MCPConfigError):
    """Raised when no profile file exists for the requested model."""


@dataclass
class Permission:
    """Scaffolding for a future approval/sandboxing workflow.

    Not enforced yet - MCPManager.allow_tool is the current gate."""
    tool: str
    server: str
    model: str
    requires_approval: bool = False
    granted: bool = False


@dataclass
class Approval:
    """Scaffolding record of a granted/denied permission request."""
    permission: Permission
    approved: bool
    reason: str = ""


def _default_mcp_dir() -> Path:
    from Janus.paths import get_mcp_path
    return get_mcp_path()


class MCPManager:
    """
    Manages MCP server definitions and per-model tool permissions.

    Args:
        mcp_dir: Directory containing servers.json and profiles/.
                 Defaults to the repo's mcp/ directory.
    """

    def __init__(self, mcp_dir: Optional[Path] = None):
        self._mcp_dir = Path(mcp_dir) if mcp_dir is not None else _default_mcp_dir()
        self._servers: Optional[Dict[str, Any]] = None
        self._profiles: Dict[str, Dict[str, Any]] = {}
        # agent/model name -> set of servers explicitly enabled this session
        self._enabled: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------
    @property
    def servers(self) -> Dict[str, Any]:
        """Loaded servers.json contents, cached."""
        if self._servers is None:
            path = self._mcp_dir / "servers.json"
            if not path.is_file():
                raise MCPConfigError(f"MCP servers.json not found at {path}")
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                raise MCPConfigError(f"Invalid JSON in {path}: {e}") from e
            if not isinstance(data, dict) or not isinstance(data.get("servers"), dict):
                raise MCPConfigError(
                    f"{path} must contain a top-level 'servers' object"
                )
            self._servers = data["servers"]
        return self._servers

    def _load_profile(self, model: str) -> Dict[str, Any]:
        """Read and cache mcp/profiles/<Model>.json (case-insensitive)."""
        key = model.lower()
        if key in self._profiles:
            return self._profiles[key]

        profiles_dir = self._mcp_dir / "profiles"
        target = None
        if profiles_dir.is_dir():
            for candidate in profiles_dir.glob("*.json"):
                if candidate.stem.lower() == key:
                    target = candidate
                    break

        if target is None:
            raise ProfileNotFoundError(
                f"No MCP profile found for model '{model}' in {profiles_dir}"
            )

        try:
            profile = json.loads(target.read_text())
        except json.JSONDecodeError as e:
            raise MCPConfigError(f"Invalid JSON in {target}: {e}") from e

        if not isinstance(profile.get("servers", []), list):
            raise MCPConfigError(f"{target}: 'servers' must be a list")
        if not isinstance(profile.get("allowed_tools", {}), dict):
            raise MCPConfigError(f"{target}: 'allowed_tools' must be an object")

        profile.setdefault("servers", [])
        profile.setdefault("allowed_tools", {})
        self._profiles[key] = profile
        return profile

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enable(self, agent: str, server: str) -> bool:
        """
        Enable an MCP server for an agent/model.

        The server must exist in servers.json and be listed in the
        agent's profile. Returns True on success.
        """
        if server not in self.servers:
            raise MCPConfigError(f"Unknown MCP server '{server}'")

        profile = self._load_profile(agent)
        if server not in profile["servers"]:
            logger.warning(
                "Server '%s' is not declared in %s's profile - refusing to enable",
                server, agent,
            )
            return False

        self._enabled.setdefault(agent.lower(), set()).add(server)
        logger.info("Enabled MCP server '%s' for agent '%s'", server, agent)
        return True

    def disable(self, agent: str, server: str) -> bool:
        """Disable a previously enabled server for an agent."""
        enabled = self._enabled.get(agent.lower(), set())
        if server in enabled:
            enabled.discard(server)
            return True
        return False

    def get_tools(self, model: str) -> Dict[str, List[str]]:
        """
        Return the tool allowlist for a model, keyed by server.

        Covers servers explicitly enabled via enable(); if none have been
        enabled yet, falls back to all servers declared in the profile
        (permissive default until the runtime starts calling enable()).
        """
        profile = self._load_profile(model)
        enabled = self._enabled.get(model.lower())
        declared = profile["servers"]
        active = [s for s in declared if enabled is None or s in enabled]

        tools: Dict[str, List[str]] = {}
        for server in active:
            allowed = profile["allowed_tools"].get(server, [])
            tools[server] = list(allowed)
        return tools

    def allow_tool(self, tool: str, model: str) -> bool:
        """Return True if the model's profile permits this tool call."""
        for server, tools in self.get_tools(model).items():
            if "*" in tools or tool in tools:
                return True
        return False