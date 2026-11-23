"""
Tests for Lares/permissions.py - AgentPermissions.

AgentPermissions wraps Custos.MCPManager for one agent, and adds the one
gate Custos has no concept of: AgentProfile.supports_tool_calls. Tests
run against the tmp_path-backed mcp_dir/manager fixtures (see
conftest.py), never the repo's real mcp/ directory.
"""

import pytest

from Custos.mcp import MCPManager
from Lares.permissions import AgentPermissions
from Lares.profiles import AgentProfile

pytestmark = pytest.mark.lares


def _permissions(model, manager, **profile_kwargs):
    profile = AgentProfile(name=model, **profile_kwargs)
    return AgentPermissions(model, profile, manager=manager)


class TestHasMcpProfile:
    def test_true_for_a_model_with_a_profile_file(self, manager):
        perms = _permissions("ToolModel", manager)
        assert perms.has_mcp_profile() is True

    def test_false_for_a_model_with_no_profile_file(self, manager):
        perms = _permissions("NoSuchModel", manager)
        assert perms.has_mcp_profile() is False


class TestToolsAllowed:
    def test_true_when_supported_and_profile_exists(self, manager):
        perms = _permissions("ToolModel", manager, supports_tool_calls=True)
        assert perms.tools_allowed() is True

    def test_false_when_model_has_no_native_tool_call_support(self, manager):
        # Even though ToolModel has a valid MCP profile, a profile that
        # declares supports_tool_calls=False must still refuse - this is
        # exactly the Vulcan/Minerva case (no native tool-call grammar).
        perms = _permissions("ToolModel", manager, supports_tool_calls=False)
        assert perms.tools_allowed() is False

    def test_false_when_no_mcp_profile_exists(self, manager):
        perms = _permissions("NoSuchModel", manager, supports_tool_calls=True)
        assert perms.tools_allowed() is False


class TestGetTools:
    def test_returns_allowed_tools_for_permitted_agent(self, manager):
        perms = _permissions("ToolModel", manager, supports_tool_calls=True)
        tools = perms.get_tools()
        assert tools.get("filesystem") == ["read_file", "list_directory"]

    def test_empty_dict_when_tools_not_allowed_at_all(self, manager):
        perms = _permissions("ToolModel", manager, supports_tool_calls=False)
        assert perms.get_tools() == {}

    def test_empty_dict_when_no_profile_rather_than_raising(self, manager):
        perms = _permissions("NoSuchModel", manager, supports_tool_calls=True)
        # Must degrade gracefully, not raise ProfileNotFoundError - Agent
        # callers rely on this to mean "no tools for this turn", not a
        # fatal error that would kill the chat session.
        assert perms.get_tools() == {}


class TestAllowTool:
    def test_true_for_a_permitted_tool(self, manager):
        perms = _permissions("ToolModel", manager, supports_tool_calls=True)
        assert perms.allow_tool("read_file") is True

    def test_false_for_an_unlisted_tool(self, manager):
        perms = _permissions("ToolModel", manager, supports_tool_calls=True)
        assert perms.allow_tool("write_file") is False

    def test_false_when_model_has_no_native_tool_call_support(self, manager):
        # The profile-level gate must short-circuit before even asking
        # Custos - a tool-incapable model is denied every tool,
        # regardless of what its (potentially borrowed/stale) MCP
        # profile would otherwise allow.
        perms = _permissions("ToolModel", manager, supports_tool_calls=False)
        assert perms.allow_tool("read_file") is False


class TestEffectiveMcpProfileNameIsHonored:
    def test_permissions_use_the_profiles_effective_name_not_agent_name(self, manager):
        # The agent's own name doesn't have to match an MCP profile file -
        # mcp_profile_name lets one agent borrow another's permissions.
        profile = AgentProfile(
            name="SomeOtherAgentName",
            supports_tool_calls=True,
            mcp_profile_name="ToolModel",
        )
        perms = AgentPermissions("SomeOtherAgentName", profile, manager=manager)
        assert perms.has_mcp_profile() is True
        assert perms.get_tools().get("filesystem") == ["read_file", "list_directory"]


class TestGetServerConfig:
    def test_passes_through_to_manager(self, manager):
        perms = _permissions("ToolModel", manager, supports_tool_calls=True)
        config = perms.get_server_config("filesystem")
        assert config["command"] == "npx"


class TestDefaultManagerConstruction:
    def test_omitting_manager_builds_a_real_mcpmanager(self):
        # No mcp_dir override here - just confirms AgentPermissions
        # doesn't require a manager to be passed in explicitly.
        profile = AgentProfile(name="Whatever")
        perms = AgentPermissions("Whatever", profile)
        assert isinstance(perms.manager, MCPManager)