"""
Tests for Faber/ollama_service.py

start_ollama/stop_ollama shell out to `ollama serve` via subprocess.Popen.
We never want a real test run to actually spawn (or expect) an ollama
binary, so subprocess.Popen is mocked in every test here.
"""

from unittest.mock import patch

import pytest

from Faber.ollama_service import start_ollama, stop_ollama
from Faber.session import get_session

pytestmark = pytest.mark.faber


class TestStartOllama:
    def test_spawns_ollama_serve_and_creates_session(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            result = start_ollama()

        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == ["ollama", "serve"]
        assert result is fake_process
        assert get_session("ollama_server") is not None

    def test_second_call_does_not_spawn_a_new_process(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            start_ollama()
            start_ollama()

        # Only the first call should have spawned a process.
        assert mock_popen.call_count == 1

    def test_second_call_returns_the_session_not_the_process(self, fake_process):
        """
        NOTE: pins a real asymmetry in the current implementation rather
        than an idealized one. start_ollama()'s "already running" branch
        returns get_session(...) directly (a Session object), while the
        "just started it" branch returns the raw subprocess.Popen object.
        Callers checking e.g. `.pid` on the result will get different
        attribute access depending on whether ollama was already running.
        If this is unintentional, the fix belongs in ollama_service.py,
        not here - this test exists so a future fix shows up as an
        intentional, visible change to this assertion instead of a
        silent behavior change.
        """
        from Faber.session import Session

        with patch("subprocess.Popen", return_value=fake_process):
            first = start_ollama()
            second = start_ollama()

        assert first is fake_process
        assert isinstance(second, Session)
        assert second.process is fake_process


class TestStopOllama:
    def test_stop_ollama_terminates_running_session(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            start_ollama()

        result = stop_ollama()

        assert result is True
        assert fake_process.terminated is True
        assert get_session("ollama_server") is None

    def test_stop_ollama_returns_false_when_not_running(self):
        assert stop_ollama() is False