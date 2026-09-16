"""
Tests for Janus/main.py's main() - argument parsing, --root handling,
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

    def test_mcp_tools_dispatches_without_context_init(self, monkeypatch):
        """mcp tools is a read-only config query - like status/doctor it
        must never construct RuntimeContext (avoids the interactive host
        prompt for a command that only reads mcp/*.json)."""
        monkeypatch.setattr("sys.argv", ["janus", "mcp", "tools", "Mercury"])
        with patch("Janus.main.handle_mcp_tools") as mock_tools, \
             patch("Mentis.context.RuntimeContext") as mock_ctx:
            result = main.main()

        mock_tools.assert_called_once_with(["Mercury"])
        mock_ctx.assert_not_called()
        assert result == 0

    def test_list_dispatches_without_context_init(self, monkeypatch):
        """list is a read-only query against the Ollama server - like
        status/doctor it must never construct RuntimeContext."""
        monkeypatch.setattr("sys.argv", ["janus", "list"])
        with patch("Janus.main.handle_list") as mock_list, \
             patch("Mentis.context.RuntimeContext") as mock_ctx:
            result = main.main()

        mock_list.assert_called_once_with([])
        mock_ctx.assert_not_called()
        assert result == 0

    def test_mcp_launch_still_uses_context_path(self, monkeypatch):
        """Other mcp actions keep the full runtime initialization."""
        monkeypatch.setattr("sys.argv", ["janus", "mcp", "launch", "mercury"])
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Janus.main.handle_mcp") as mock_mcp:
            result = main.main()

        mock_mcp.assert_called_once_with(["launch", "mercury"])
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

    def test_pull_dispatches_to_handle_pull(self, monkeypatch):
        result, handler = self._run_with_mocked_context(
            monkeypatch, ["janus", "pull", "qwen2.5:0.5b"], "handle_pull")
        handler.assert_called_once_with(["qwen2.5:0.5b"])
        assert result == 0

    def test_remove_dispatches_to_handle_remove(self, monkeypatch):
        result, handler = self._run_with_mocked_context(
            monkeypatch, ["janus", "remove", "mercury"], "handle_remove")
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
        errors and continues without a context rather than aborting -
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


class TestMainEventBusLifecycle:
    """main() owns the Mercurius bus: initialize on startup, publish
    STARTUP/SHUTDOWN, and always shut the bus down via the finally block."""

    def _run_main(self, monkeypatch, argv, handler_name="handle_start", handler_side_effect=None):
        monkeypatch.setattr("sys.argv", argv)
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Janus.main.initialize_bus") as mock_init, \
             patch("Janus.main.publish_event") as mock_publish, \
             patch("Janus.main.shutdown_bus") as mock_shutdown, \
             patch(f"Janus.main.{handler_name}", side_effect=handler_side_effect):
            result = main.main()

        return result, mock_init, mock_publish, mock_shutdown

    def test_initializes_bus_and_publishes_startup_and_shutdown(self, monkeypatch):
        result, mock_init, mock_publish, mock_shutdown = self._run_main(
            monkeypatch, ["janus", "start", "mercury"])

        assert result == 0
        mock_init.assert_called_once_with()
        mock_shutdown.assert_called_once_with()
        published_types = [call.args[0] for call in mock_publish.call_args_list]
        assert main.EventType.STARTUP in published_types
        assert main.EventType.SHUTDOWN in published_types

    def test_bus_shutdown_still_runs_when_handler_raises(self, monkeypatch):
        result, mock_init, mock_publish, mock_shutdown = self._run_main(
            monkeypatch, ["janus", "start", "mercury"],
            handler_side_effect=ValueError("weird"))

        assert result == 1
        mock_shutdown.assert_called_once_with()
        published_types = [call.args[0] for call in mock_publish.call_args_list]
        assert main.EventType.SHUTDOWN in published_types

    def test_no_shutdown_event_when_bus_never_started(self, monkeypatch):
        """If context/bus init fails, SHUTDOWN must not be published -
        subscribers expect STARTUP/SHUTDOWN pairs (review finding)."""
        monkeypatch.setattr("sys.argv", ["janus", "start", "mercury"])

        with patch("Mentis.context.RuntimeContext", side_effect=RuntimeError("boom")), \
             patch("Janus.main.initialize_bus"), \
             patch("Janus.main.publish_event") as mock_publish, \
             patch("Janus.main.shutdown_bus") as mock_shutdown, \
             patch("Janus.main.handle_start"):
            result = main.main()

        assert result == 0  # continues without context per existing contract
        mock_publish.assert_not_called()
        mock_shutdown.assert_not_called()

    def test_bus_not_initialized_when_context_startup_fails(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["janus", "start", "mercury"])
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = False

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Janus.main.initialize_bus") as mock_init, \
             patch("Janus.main.publish_event") as mock_publish, \
             patch("Janus.main.shutdown_bus") as mock_shutdown:
            result = main.main()

        assert result == 1
        mock_init.assert_not_called()
        mock_publish.assert_not_called()
        mock_shutdown.assert_not_called()

    def test_status_and_doctor_do_not_touch_the_bus(self, monkeypatch):
        for command in ("status", "doctor"):
            monkeypatch.setattr("sys.argv", ["janus", command])

            with patch(f"Janus.main.handle_{command}"), \
                 patch("Janus.main.initialize_bus") as mock_init, \
                 patch("Janus.main.publish_event") as mock_publish, \
                 patch("Janus.main.shutdown_bus") as mock_shutdown:
                assert main.main() == 0

            mock_init.assert_not_called()
            mock_publish.assert_not_called()
            mock_shutdown.assert_not_called()