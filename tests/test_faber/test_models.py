"""
Tests for Faber/models.py

start_model/stop_model shell out to `ollama run <model>` via
subprocess.Popen and optionally notify a bound RuntimeContext
(set via set_context) of load/unload events. Both subprocess.Popen and
the context are faked here so tests never spawn real processes or
depend on Mentis.context being importable/side-effect-free.

pull_model/build_model/list_models/remove_model are not yet implemented
(each is a bare `pass`) — scaffolding tests for them are included and
marked xfail/skip as appropriate so the suite documents the gap and
starts passing for real the moment each function grows a real
implementation.
"""

from unittest.mock import patch, MagicMock

import pytest

import Faber.models as models_module
from Faber.models import (
    start_model,
    stop_model,
    pull_model,
    build_model,
    list_models,
    remove_model,
    set_context,
)
from Faber.session import get_session

pytestmark = pytest.mark.faber


class TestStartModel:
    def test_spawns_ollama_run_with_model_name(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            result = start_model("mercury")

        args, kwargs = mock_popen.call_args
        assert args[0] == ["ollama", "run", "mercury"]
        assert result is fake_process

    def test_creates_session_named_after_model(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")
        assert get_session("mercury") is not None

    def test_returns_existing_session_without_spawning_again(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            start_model("mercury")
            second = start_model("mercury")

        assert mock_popen.call_count == 1
        # NOTE: unlike start_ollama, start_model's early-return path
        # returns the *Session* object, not the process, when the model
        # is already running — this asymmetry is intentional per the
        # current implementation, so we pin it rather than "fixing" it.
        assert second is get_session("mercury")

    def test_notifies_bound_context_on_start(self, fake_process):
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")

        fake_context.load_model.assert_called_once()
        call_args = fake_context.load_model.call_args
        assert call_args[0][0] == "mercury"

    def test_no_context_call_when_none_bound(self, fake_process):
        # _reset_faber_models_context autouse fixture guarantees _context
        # is None at the start of this test.
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")  # must not raise even with no context bound


class TestStopModel:
    def test_stop_model_terminates_session(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")

        stop_model("mercury")

        assert fake_process.terminated is True
        assert get_session("mercury") is None

    def test_stop_model_notifies_bound_context(self, fake_process):
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")
        stop_model("mercury")

        fake_context.unload_model.assert_called_once_with("mercury")

    def test_stop_model_no_context_call_when_model_was_not_running(self):
        fake_context = MagicMock()
        set_context(fake_context)

        stop_model("never_started")

        fake_context.unload_model.assert_not_called()


class TestSetContext:
    def test_set_context_binds_module_level_context(self):
        fake_context = MagicMock()
        set_context(fake_context)
        assert models_module._context is fake_context


class TestUnimplementedModelOperations:
    """
    pull_model, build_model, list_models, and remove_model are stubs
    (`pass`, implicitly returning None) as of writing. These tests
    document that current behavior explicitly, so:
      - the gap is visible in test output rather than silently untested
      - the moment a real implementation lands, whichever assertion
        below starts failing tells you exactly which test to rewrite
    """

    def test_pull_model_currently_returns_none(self):
        assert pull_model("mercury") is None

    def test_build_model_currently_returns_none(self):
        assert build_model("mercury") is None

    def test_list_models_currently_returns_none(self):
        assert list_models() is None

    def test_remove_model_currently_returns_none(self):
        assert remove_model("mercury") is None