"""
Shared fixtures for Custos (MCP/security) tests.

Every test runs against a throwaway mcp/ directory built in tmp_path -
never the repo's real mcp/ - so tests are hermetic and can't be broken
by (or break) real configuration.
"""

import json

import pytest


@pytest.fixture
def mcp_dir(tmp_path):
    """A tmp mcp/ tree with servers.json and profiles/ populated."""
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
            "git": {
                "command": "uvx",
                "args": ["mcp-server-git"],
                "env": {},
                "transport": "stdio",
                "description": "test git server",
            },
        }
    }))

    (profiles / "Mercury.json").write_text(json.dumps({
        "model": "Mercury",
        "servers": ["filesystem", "git"],
        "allowed_tools": {
            "filesystem": ["read_file", "list_directory"],
            "git": ["*"],
        },
    }))

    (profiles / "Minerva.json").write_text(json.dumps({
        "model": "Minerva",
        "servers": ["filesystem"],
        "allowed_tools": {
            "filesystem": ["read_file"],
        },
    }))

    return mcp


@pytest.fixture
def manager(mcp_dir):
    from Custos.mcp import MCPManager
    return MCPManager(mcp_dir=mcp_dir)
