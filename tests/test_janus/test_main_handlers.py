"""
Tests for Janus/main.py's individual command handlers (handle_start,
handle_stop, handle_status, handle_build, handle_doctor, handle_mcp,
handle_mcp_launch).

Every handler is tested by mocking the functions it calls into (Faber,
Janus.doctor, Hestia) rather than letting any of them run for real -
this suite is about main.py's own argument-parsing/exit-code/output
logic, not re-testing Faber or doctor (already covered in their own
modules).
"""

from unittest.mock import patch, MagicMock

import pytest

from Janus import main

pytestmark = pytest.mark.janus


class TestHandleStart:
    def test_exits_1_when_no_model_given(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_start([])
        assert exc_info.value.code == 1

    def test_starts_ollama_then_model(self):
        with patch("Janus.main.start_ollama") as mock_start_ollama, \
             patch("Janus.main.start_model") as mock_start_model:
            main.handle_start(["mercury"])

        mock_start_ollama.assert_called_once()
        mock_start_model.assert_called_once_with("mercury")

    def test_exits_1_on_runtime_error(self):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main.start_model", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_start(["mercury"])
        assert exc_info.value.code == 1

    def test_exits_1_on_unexpected_exception(self):
        with patch("Janus.main.start_ollama", side_effect=ValueError("weird")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_start(["mercury"])
        assert exc_info.value.code == 1

    def test_prints_success_message(self, capsys):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main.start_model"):
            main.handle_start(["mercury"])
        captured = capsys.readouterr()
        assert "mercury" in captured.out
        assert "running" in captured.out


class TestHandleStop:
    def test_stops_specific_model_when_given(self):
        with patch("Janus.main.stop_model", return_value=True) as mock_stop:
            main.handle_stop(["mercury"])
        mock_stop.assert_called_once_with("mercury")

    def test_prints_warning_when_specific_model_not_running(self, capsys):
        with patch("Janus.main.stop_model", return_value=False):
            main.handle_stop(["mercury"])
        captured = capsys.readouterr()
        assert "not running" in captured.out

    def test_stops_all_sessions_and_ollama_when_no_args(self):
        with patch("Janus.main.get_all_sessions", return_value={"a": None, "b": None}), \
             patch("Janus.main.stop_session") as mock_stop_session, \
             patch("Janus.main.stop_ollama") as mock_stop_ollama:
            main.handle_stop([])

        assert mock_stop_session.call_count == 2
        mock_stop_ollama.assert_called_once()

    def test_exits_1_on_exception(self):
        with patch("Janus.main.stop_model", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_stop(["mercury"])
        assert exc_info.value.code == 1


class TestHandleStatus:
    def test_prints_no_active_sessions_when_empty(self, capsys):
        with patch("Janus.main.get_status", return_value=[]), \
             patch("Hestia.hardware.detect_hardware", return_value=MagicMock()), \
             patch("Hestia.hardware.recommend_model", return_value=MagicMock()), \
             patch("Hestia.hardware.print_hardware_report"):
            main.handle_status()
        captured = capsys.readouterr()
        assert "No active sessions" in captured.out

    def test_prints_session_details_when_present(self, capsys):
        sessions = [{
            "name": "mercury", "type": "model", "running": True,
            "pid": 123, "started": "2026-01-01T00:00:00",
        }]
        with patch("Janus.main.get_status", return_value=sessions), \
             patch("Hestia.hardware.detect_hardware", return_value=MagicMock()), \
             patch("Hestia.hardware.recommend_model", return_value=MagicMock()), \
             patch("Hestia.hardware.print_hardware_report"):
            main.handle_status()
        captured = capsys.readouterr()
        assert "mercury" in captured.out
        assert "RUNNING" in captured.out

    def test_does_not_raise_when_hardware_report_fails(self):
        with patch("Janus.main.get_status", return_value=[]), \
             patch("Hestia.hardware.detect_hardware", side_effect=RuntimeError("boom")):
            main.handle_status()  # must not raise


class TestHandleBuild:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_build([])
        assert exc_info.value.code == 1

    def test_calls_build_model(self):
        with patch("Janus.main.build_model") as mock_build:
            main.handle_build(["mercury"])
        mock_build.assert_called_once_with("mercury")

    def test_exits_1_on_exception(self):
        with patch("Janus.main.build_model", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_build(["mercury"])
        assert exc_info.value.code == 1


class TestHandleDoctor:
    def test_prints_success_when_diagnostic_passes(self, capsys):
        with patch("Janus.main.full_diagnostic", return_value=True):
            main.handle_doctor()
        captured = capsys.readouterr()
        assert "All checks passed" in captured.out

    def test_prints_failure_when_diagnostic_fails(self, capsys):
        with patch("Janus.main.full_diagnostic", return_value=False):
            main.handle_doctor()
        captured = capsys.readouterr()
        assert "Some checks failed" in captured.out

    def test_exits_1_on_exception(self):
        with patch("Janus.main.full_diagnostic", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_doctor()
        assert exc_info.value.code == 1


class TestHandleMcp:
    def test_exits_1_when_no_action_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_mcp([])
        assert exc_info.value.code == 1

    def test_dispatches_launch_action(self):
        with patch("Janus.main.handle_mcp_launch") as mock_launch:
            main.handle_mcp(["launch", "mercury"])
        mock_launch.assert_called_once_with(["mercury"])

    def test_unknown_action_prints_warning_without_raising(self, capsys):
        main.handle_mcp(["frobnicate"])
        captured = capsys.readouterr()
        assert "not yet fully implemented" in captured.out


class TestHandleMcpLaunch:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_mcp_launch([])
        assert exc_info.value.code == 1

    def test_launches_claude_with_model(self):
        fake_process = MagicMock(pid=42)
        with patch("Faber.claude_service.ollama_launch_claude", return_value=fake_process) as mock_launch:
            main.handle_mcp_launch(["mercury"])
        mock_launch.assert_called_once_with("mercury", auto_yes=False)

    def test_passes_auto_yes_flag(self):
        fake_process = MagicMock(pid=42)
        with patch("Faber.claude_service.ollama_launch_claude", return_value=fake_process) as mock_launch:
            main.handle_mcp_launch(["mercury", "--yes"])
        mock_launch.assert_called_once_with("mercury", auto_yes=True)

    def test_exits_1_on_runtime_error(self):
        with patch("Faber.claude_service.ollama_launch_claude", side_effect=RuntimeError("not installed")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_mcp_launch(["mercury"])
        assert exc_info.value.code == 1


class TestPrintHelp:
    def test_mentions_all_top_level_commands(self, capsys):
        main.print_help()
        captured = capsys.readouterr()
        for command in ["start", "stop", "status", "build", "doctor", "mcp", "help"]:
            assert command in captured.out