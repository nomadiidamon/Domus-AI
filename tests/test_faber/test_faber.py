"""
Tests for Faber/__init__.py - confirms the package's public re-exports
stay intact. This is cheap insurance against a refactor inside session.py
/ models.py / ollama_service.py / claude_service.py accidentally
renaming something that __init__.py (and therefore `from Faber import X`
callers elsewhere in the codebase) depends on.
"""

import pytest

import Faber

pytestmark = pytest.mark.faber

EXPECTED_EXPORTS = [
    "Session",
    "create_session",
    "get_session",
    "get_session_by_pid",
    "get_all_sessions",
    "get_status",
    "stop_session",
    "remove_session",
    "start_ollama",
    "stop_ollama",
    "start_model",
    "stop_model",
    "pull_model",
    "build_model",
    "list_models",
    "remove_model",
    "set_context",
    "ollama_launch_claude",
    "stop_claude",
]


class TestFaberPackageExports:
    def test_all_matches_expected_exports(self):
        assert set(Faber.__all__) == set(EXPECTED_EXPORTS)

    @pytest.mark.parametrize("name", EXPECTED_EXPORTS)
    def test_each_export_is_accessible_on_package(self, name):
        assert hasattr(Faber, name)