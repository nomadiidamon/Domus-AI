"""Tests for Faber/claude_service.py — launching Claude Code via Ollama."""

from unittest.mock import patch

import pytest

from Faber.claude_service import ollama_launch_claude, stop_claude, CLAUDE_SESSION_NAME
from Faber.session import get_session

pytestmark = pytest.mark.faber


class TestOllamaLaunchClaude:
    def test_raises_on_empty_model(self):
        with pytest.raises(ValueError):
            ollama_launch_claude("")

    def test_raises_on_non_string_model(self):
        with pytest.raises(ValueError):
            ollama_launch_claude(None)

    def test_builds_expected_command(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            ollama_launch_claude("mercury")

        args, kwargs = mock_popen.call_args
        assert args[0] == ["ollama", "launch", "claude", "--model", "mercury"]

    def test_appends_yes_flag_when_auto_yes(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            ollama_launch_claude("mercury", auto_yes=True)

        args, kwargs = mock_popen.call_args
        assert args[0][-1] == "--yes"

    def test_creates_session_with_expected_name_and_metadata(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            ollama_launch_claude("mercury")

        session = get_session(CLAUDE_SESSION_NAME)
        assert session is not None
        assert session.metadata == {
            "provider": "ollama",
            "integration": "claude",
            "model": "mercury",
        }

    def test_returns_existing_process_if_already_running(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            first = ollama_launch_claude("mercury")
            second = ollama_launch_claude("mercury")

        assert mock_popen.call_count == 1
        assert first is second

    def test_raises_runtime_error_when_ollama_not_installed(self):
        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="Ollama is not installed"):
                ollama_launch_claude("mercury")


class TestStopClaude:
    def test_stop_claude_terminates_session(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            ollama_launch_claude("mercury")

        result = stop_claude()

        assert result is True
        assert fake_process.terminated is True
        assert get_session(CLAUDE_SESSION_NAME) is None

    def test_stop_claude_returns_false_when_not_running(self):
        assert stop_claude() is False