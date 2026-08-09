"""
Tests for Janus/main.py's main() — argument parsing, --root handling,
and command dispatch. All handlers and RuntimeContext are mocked so
these tests exercise only main()'s own parsing/dispatch logic.
"""

from unittest.mock import patch, MagicMock

import pytest

from Janus import main

pytestmark = pytest.mark.janus


class TestMainNoArgs:
    def test_prints_help_and_returns_0(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["janus"])
        result = main.main()
        assert result == 0
        assert "USAGE" in capsys.readouterr().out


class TestMainHelpCommand:
    @pytest.mark.parametrize("flag", ["help", "-h", "--help"])
    def test_help_variants_return_0(self, monkeypatch, flag):
        monkeypatch.setattr("sys.argv", ["janus", flag])
        assert main.main() == 0


class TestMainStatusAndDoctor:
    def test_status_dispatches_without_context_init(self, monkeypatch):
        """status/doctor are handled before the RuntimeContext block, so
        RuntimeContext must never be constructed for these commands."""
        monkeypatch.setattr("sys.argv", ["janus", "status"])
        with patch("Janus.main.handle_status") as mock_status, \
             patch("Mentis.context.RuntimeContext") as mock_ctx:
            result = main.main()

        mock_status.assert_called_once()
        mock_ctx.assert_not_called()
        assert result == 0

    def test_doctor_dispatches_without_context_init(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "doctor"])
        with patch("Janus.main.handle_doctor") as mock_doctor, \
             patch("Mentis.context.RuntimeContext") as mock_ctx:
            result = main.main()

        mock_doctor.assert_called_once()
        mock_ctx.assert_not_called()
        assert result == 0


class TestMainRootFlag:
    def test_root_flag_is_stripped_from_args_passed_to_handler(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "--root", "/some/path", "start", "mercury"])

        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Janus.main.handle_start") as mock_handle_start:
            main.main()

        mock_handle_start.assert_called_once_with(["mercury"])

    def test_root_flag_without_path_returns_1(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "--root"])
        assert main.main() == 1

    def test_suggested_root_passed_to_context_startup(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "--root", "/some/path", "start", "mercury"])

        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Janus.main.handle_start"):
            main.main()

        _, kwargs = fake_ctx.startup.call_args
        from pathlib import Path
        assert kwargs["suggested_host"] == Path("/some/path")


class TestMainCommandDispatch:
    def _run_with_mocked_context(self, monkeypatch, argv, handler_name):
        monkeypatch.setattr("sys.argv", argv)
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch(f"Janus.main.{handler_name}") as mock_handler:
            result = main.main()

        return result, mock_handler

    def test_start_dispatches_to_handle_start(self, monkeypatch):
        result, handler = self._run_with_mocked_context(
            monkeypatch, ["janus", "start", "mercury"], "handle_start")
        handler.assert_called_once_with(["mercury"])
        assert result == 0

    def test_stop_dispatches_to_handle_stop(self, monkeypatch):
        result, handler = self._run_with_mocked_context(
            monkeypatch, ["janus", "stop"], "handle_stop")
        handler.assert_called_once_with([])
        assert result == 0

    def test_build_dispatches_to_handle_build(self, monkeypatch):
        result, handler = self._run_with_mocked_context(
            monkeypatch, ["janus", "build", "mercury"], "handle_build")
        handler.assert_called_once_with(["mercury"])
        assert result == 0

    def test_mcp_dispatches_to_handle_mcp(self, monkeypatch):
        result, handler = self._run_with_mocked_context(
            monkeypatch, ["janus", "mcp", "launch", "mercury"], "handle_mcp")
        handler.assert_called_once_with(["launch", "mercury"])
        assert result == 0

    def test_unknown_command_returns_1(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "frobnicate"])
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"):
            result = main.main()

        assert result == 1

    def test_returns_1_when_context_startup_fails(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "start", "mercury"])
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = False

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"):
            result = main.main()

        assert result == 1

    def test_continues_without_context_if_context_init_raises(self, monkeypatch):
        """
        main() deliberately swallows RuntimeContext construction/startup
        errors and continues without a context rather than aborting —
        pin that resilience behavior.
        """
        monkeypatch.setattr("sys.argv", ["janus", "build", "mercury"])

        with patch("Mentis.context.RuntimeContext", side_effect=RuntimeError("boom")), \
             patch("Janus.main.handle_build") as mock_handle_build:
            result = main.main()

        mock_handle_build.assert_called_once_with(["mercury"])
        assert result == 0

    def test_keyboard_interrupt_returns_1(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "build", "mercury"])
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Janus.main.handle_build", side_effect=KeyboardInterrupt):
            result = main.main()

        assert result == 1

    def test_unexpected_exception_in_handler_returns_1(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "build", "mercury"])
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Janus.main.handle_build", side_effect=ValueError("weird")):
            result = main.main()

        assert result == 1