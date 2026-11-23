"""
Tests for Custos/mcp.py - MCPManager.

Covers config loading (servers.json + profiles/*.json), enable/disable,
get_tools, and allow_tool - including malformed config, missing profiles,
and wildcard allowlists. All tests use the tmp_path-backed mcp_dir fixture,
never the repo's real mcp/ directory.
"""

import json

import pytest

from Custos.mcp import MCPConfigError, MCPManager, ProfileNotFoundError

pytestmark = pytest.mark.custos


class TestServersLoading:
    def test_loads_servers_from_config(self, manager):
        servers = manager.servers
        assert set(servers) == {"filesystem", "git"}
        assert servers["filesystem"]["transport"] == "stdio"

    def test_missing_servers_json_raises(self, tmp_path):
        manager = MCPManager(mcp_dir=tmp_path / "nonexistent")
        with pytest.raises(MCPConfigError, match="servers.json not found"):
            _ = manager.servers

    def test_malformed_servers_json_raises(self, tmp_path):
        mcp = tmp_path / "mcp"
        mcp.mkdir()
        (mcp / "servers.json").write_text("{not json")
        manager = MCPManager(mcp_dir=mcp)
        with pytest.raises(MCPConfigError, match="Invalid JSON"):
            _ = manager.servers

    def test_servers_json_without_servers_key_raises(self, tmp_path):
        mcp = tmp_path / "mcp"
        mcp.mkdir()
        (mcp / "servers.json").write_text(json.dumps({"unexpected": {}}))
        manager = MCPManager(mcp_dir=mcp)
        with pytest.raises(MCPConfigError, match="top-level 'servers'"):
            _ = manager.servers


class TestProfileLoading:
    def test_missing_profile_raises(self, manager):
        with pytest.raises(ProfileNotFoundError, match="No MCP profile"):
            manager.get_tools("nonexistent-model")

    def test_profile_lookup_is_case_insensitive(self, manager):
        tools = manager.get_tools("mercury")
        assert "filesystem" in tools

    def test_malformed_profile_raises(self, mcp_dir):
        (mcp_dir / "profiles" / "Broken.json").write_text("{oops")
        with pytest.raises(MCPConfigError, match="Invalid JSON"):
            manager = MCPManager(mcp_dir=mcp_dir)
            manager.get_tools("broken")


class TestEnable:
    def test_enable_declared_server_succeeds(self, manager):
        assert manager.enable("mercury", "filesystem") is True

    def test_enable_undeclared_server_refused(self, manager):
        # Minerva's profile only declares filesystem
        assert manager.enable("minerva", "git") is False

    def test_enable_unknown_server_raises(self, manager):
        with pytest.raises(MCPConfigError, match="Unknown MCP server"):
            manager.enable("mercury", "does-not-exist")

    def test_disable_roundtrip(self, manager):
        manager.enable("mercury", "git")
        assert manager.disable("mercury", "git") is True
        assert manager.disable("mercury", "git") is False


class TestGetTools:
    def test_defaults_to_all_profile_servers(self, manager):
        tools = manager.get_tools("mercury")
        assert set(tools) == {"filesystem", "git"}
        assert tools["filesystem"] == ["read_file", "list_directory"]

    def test_after_enable_only_enabled_servers_returned(self, manager):
        manager.enable("mercury", "filesystem")
        tools = manager.get_tools("mercury")
        assert set(tools) == {"filesystem"}

    def test_disable_removes_from_tools(self, manager):
        manager.enable("mercury", "filesystem")
        manager.enable("mercury", "git")
        manager.disable("mercury", "git")
        assert set(manager.get_tools("mercury")) == {"filesystem"}

    def test_server_without_allowlist_yields_empty_list(self, mcp_dir):
        (mcp_dir / "profiles" / "Sparse.json").write_text(json.dumps({
            "model": "Sparse",
            "servers": ["git"],
            "allowed_tools": {},
        }))
        manager = MCPManager(mcp_dir=mcp_dir)
        assert manager.get_tools("sparse") == {"git": []}


class TestAllowTool:
    def test_allows_listed_tool(self, manager):
        assert manager.allow_tool("read_file", "mercury") is True

    def test_denies_unlisted_tool(self, manager):
        assert manager.allow_tool("delete_everything", "minerva") is False

    def test_wildcard_allows_any_tool_on_that_server(self, manager):
        # Mercury's profile grants git: ["*"]
        assert manager.allow_tool("git_push", "mercury") is True

    def test_denies_tool_when_server_not_enabled(self, manager):
        # Enable only filesystem - git's wildcard no longer applies
        manager.enable("mercury", "filesystem")
        assert manager.allow_tool("git_push", "mercury") is False
        assert manager.allow_tool("read_file", "mercury") is True

    def test_unknown_model_raises(self, manager):
        with pytest.raises(ProfileNotFoundError):
            manager.allow_tool("read_file", "ghost")
