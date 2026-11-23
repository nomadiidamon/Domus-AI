"""
Shared fixtures for Lares (agents) tests.

Mirrors tests/test_custos/conftest.py's approach: every test that needs
MCP config runs against a throwaway mcp/ directory built in tmp_path,
never the repo's real mcp/.
"""

import json

import pytest


@pytest.fixture
def mcp_dir(tmp_path):
    """A tmp mcp/ tree with servers.json and profiles/ populated for a
    couple of test models - mirrors the shape of the real project's
    mcp/servers.json and mcp/profiles/*.json."""
    mcp = tmp_path / "mcp"
    profiles = mcp / "profiles"
    profiles.mkdir(parents=True)

    (mcp / "servers.json").write_text(json.dumps({
        "servers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
                "env": {},
                "transport": "stdio",
                "description": "test fs server",
            },
        }
    }))

    (profiles / "ToolModel.json").write_text(json.dumps({
        "model": "ToolModel",
        "servers": ["filesystem"],
        "allowed_tools": {
            "filesystem": ["read_file", "list_directory"],
        },
    }))

    (profiles / "NoFsModel.json").write_text(json.dumps({
        "model": "NoFsModel",
        "servers": [],
        "allowed_tools": {},
    }))

    return mcp


@pytest.fixture
def manager(mcp_dir):
    from Custos.mcp import MCPManager
    return MCPManager(mcp_dir=mcp_dir)