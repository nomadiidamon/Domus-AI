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

    def test_publishes_model_loaded_event_on_success(self):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main.start_model"), \
             patch("Janus.main.publish_event") as mock_publish:
            main.handle_start(["mercury"])
        mock_publish.assert_called_once_with(
            main.EventType.MODEL_LOADED,
            source="janus",
            payload={"model": "mercury"},
        )

    def test_no_event_published_when_start_fails(self):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main.start_model", side_effect=RuntimeError("boom")), \
             patch("Janus.main.publish_event") as mock_publish:
            with pytest.raises(SystemExit):
                main.handle_start(["mercury"])
        mock_publish.assert_not_called()


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

    def test_publishes_model_unloaded_event_on_successful_stop(self):
        with patch("Janus.main.stop_model", return_value=True), \
             patch("Janus.main.publish_event") as mock_publish:
            main.handle_stop(["mercury"])
        mock_publish.assert_called_once_with(
            main.EventType.MODEL_UNLOADED,
            source="janus",
            payload={"model": "mercury"},
        )

    def test_no_event_published_when_model_not_running(self):
        with patch("Janus.main.stop_model", return_value=False), \
             patch("Janus.main.publish_event") as mock_publish:
            main.handle_stop(["mercury"])
        mock_publish.assert_not_called()


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


class TestHandlePull:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_pull([])
        assert exc_info.value.code == 1

    def test_calls_pull_model(self):
        with patch("Janus.main.pull_model") as mock_pull:
            main.handle_pull(["qwen2.5:0.5b"])
        mock_pull.assert_called_once_with("qwen2.5:0.5b")

    def test_exits_1_on_exception(self):
        with patch("Janus.main.pull_model", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_pull(["mercury"])
        assert exc_info.value.code == 1


class TestHandleList:
    def test_prints_models(self, capsys):
        models = [{"name": "mercury:latest", "id": "abc", "size": "4.7 GB", "modified": "3 days ago"}]
        with patch("Janus.main.list_models", return_value=models):
            main.handle_list([])
        captured = capsys.readouterr()
        assert "mercury:latest" in captured.out
        assert "4.7 GB" in captured.out

    def test_prints_hint_when_no_models(self, capsys):
        with patch("Janus.main.list_models", return_value=[]):
            main.handle_list([])
        assert "No models installed" in capsys.readouterr().out

    def test_exits_1_on_exception(self):
        with patch("Janus.main.list_models", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_list([])
        assert exc_info.value.code == 1


class TestHandleRemove:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_remove([])
        assert exc_info.value.code == 1

    def test_calls_remove_model(self):
        with patch("Janus.main.remove_model") as mock_remove:
            main.handle_remove(["mercury"])
        mock_remove.assert_called_once_with("mercury")

    def test_exits_1_on_exception(self):
        with patch("Janus.main.remove_model", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_remove(["mercury"])
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

    def test_dispatches_tools_action(self):
        with patch("Janus.main.handle_mcp_tools") as mock_tools:
            main.handle_mcp(["tools", "Mercury"])
        mock_tools.assert_called_once_with(["Mercury"])

    def test_unknown_action_prints_warning_without_raising(self, capsys):
        main.handle_mcp(["frobnicate"])
        captured = capsys.readouterr()
        assert "not yet fully implemented" in captured.out


class TestHandleMcpTools:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_mcp_tools([])
        assert exc_info.value.code == 1

    def test_prints_tools_grouped_by_server(self, capsys):
        fake_manager = MagicMock()
        fake_manager.get_tools.return_value = {
            "filesystem": ["read_file", "list_directory"],
            "git": ["*"],
        }
        with patch("Custos.mcp.MCPManager", return_value=fake_manager):
            main.handle_mcp_tools(["mercury"])

        captured = capsys.readouterr()
        assert "mercury" in captured.out
        assert "filesystem: read_file, list_directory" in captured.out
        assert "git: *" in captured.out

    def test_prints_none_when_profile_has_no_tools(self, capsys):
        fake_manager = MagicMock()
        fake_manager.get_tools.return_value = {}
        with patch("Custos.mcp.MCPManager", return_value=fake_manager):
            main.handle_mcp_tools(["mercury"])
        assert "none" in capsys.readouterr().out

    def test_exits_1_on_manager_error(self):
        with patch("Custos.mcp.MCPManager", side_effect=RuntimeError("bad config")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_mcp_tools(["mercury"])
        assert exc_info.value.code == 1


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