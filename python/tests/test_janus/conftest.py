"""Shared fixtures for Janus (CLI, config, paths, dependencies, doctor, installer) tests."""

import sys

import pytest


@pytest.fixture(autouse=True)
def _reset_janus_paths_host_cache():
    """
    Janus.paths keeps a module-level _host_project_root cache separate
    from the LOCAL_AI_RUNTIME_HOST env var (set_host_project_root() sets
    it directly, bypassing the env var). Reset it around every Janus
    test so a set_host_project_root() call in one test can't leak into
    another test that expects to resolve the host root fresh.
    """
    def _clear():
        if "Janus.paths" in sys.modules:
            sys.modules["Janus.paths"]._host_project_root = None

    _clear()
    yield
    _clear()