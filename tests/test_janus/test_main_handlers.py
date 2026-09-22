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


class TestHandleAsk:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_ask([])
        assert exc_info.value.code == 1
 
    def test_exits_1_when_no_prompt_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_ask(["mercury"])
        assert exc_info.value.code == 1
 
    def test_starts_ollama_then_generates(self):
        mock_response = MagicMock(content="Hello there!")
        with patch("Janus.main.start_ollama") as mock_start_ollama, \
             patch("Janus.main.generate", return_value=mock_response) as mock_generate:
            main.handle_ask(["mercury", "hi", "there"])
 
        mock_start_ollama.assert_called_once()
        mock_generate.assert_called_once_with("mercury", "hi there")
 
    def test_prints_reply_content(self, capsys):
        mock_response = MagicMock(content="42")
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main.generate", return_value=mock_response):
            main.handle_ask(["mercury", "What is the answer?"])
        assert "42" in capsys.readouterr().out
 
    def test_exits_1_on_runtime_error(self):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main.generate", side_effect=RuntimeError("unreachable")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_ask(["mercury", "hi"])
        assert exc_info.value.code == 1
 
    def test_exits_1_on_unexpected_exception(self):
        with patch("Janus.main.start_ollama", side_effect=ValueError("weird")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_ask(["mercury", "hi"])
        assert exc_info.value.code == 1
 
 
class TestHandleChat:
    def test_exits_1_when_no_model_given(self):
        with pytest.raises(SystemExit) as exc_info:
            main.handle_chat([])
        assert exc_info.value.code == 1
 
    def test_exits_1_when_ollama_fails_to_start(self):
        with patch("Janus.main.start_ollama", side_effect=RuntimeError("no ollama")):
            with pytest.raises(SystemExit) as exc_info:
                main.handle_chat(["mercury"])
        assert exc_info.value.code == 1
 
    def test_immediate_eof_ends_gracefully(self, capsys):
        """Ctrl+D on the very first prompt should end the chat, not crash."""
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=EOFError):
            main.handle_chat(["mercury"])
        assert "Chat ended" in capsys.readouterr().out
 
    def test_exit_keyword_ends_chat_without_calling_model(self):
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=["exit"]), \
             patch("Janus.main.chat_with_model") as mock_chat:
            main.handle_chat(["mercury"])
        mock_chat.assert_not_called()
 
    def test_sends_user_message_and_prints_reply(self, capsys):
        mock_response = MagicMock()
        mock_response.content = "Hi! How can I help?"
        mock_response.message.role = "assistant"
        mock_response.message.content = "Hi! How can I help?"
 
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=["hello", "quit"]), \
             patch("Janus.main.chat_with_model", return_value=mock_response) as mock_chat:
            main.handle_chat(["mercury"])
 
        mock_chat.assert_called_once()
        called_model, called_history = mock_chat.call_args[0]
        assert called_model == "mercury"
        assert called_history[0].role == "user"
        assert called_history[0].content == "hello"
        assert "Hi! How can I help?" in capsys.readouterr().out
 
    def test_keyboard_interrupt_ends_gracefully(self, capsys):
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=KeyboardInterrupt):
            main.handle_chat(["mercury"])
        assert "Chat ended" in capsys.readouterr().out
 
    def test_blank_input_is_skipped(self):
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=["   ", "quit"]), \
             patch("Janus.main.chat_with_model") as mock_chat:
            main.handle_chat(["mercury"])
        mock_chat.assert_not_called()
 
    def test_chat_error_does_not_end_session_and_drops_turn(self):
        """A failed turn should print an error, drop the unanswered message
        from history, and keep the loop going rather than crashing."""
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=["hello", "quit"]), \
             patch("Janus.main.chat_with_model", side_effect=RuntimeError("boom")) as mock_chat:
            main.handle_chat(["mercury"])
        mock_chat.assert_called_once()

    def test_warns_when_no_context_bound(self, capsys):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=None), \
             patch("builtins.input", side_effect=["quit"]):
            main.handle_chat(["mercury"])
        assert "will not be saved to memory" in capsys.readouterr().out
 
    def test_no_warning_when_context_bound(self, capsys):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=MagicMock()), \
             patch("builtins.input", side_effect=["quit"]):
            main.handle_chat(["mercury"])
        assert "will not be saved to memory" not in capsys.readouterr().out
 
    def test_records_exactly_one_turn_per_message_no_duplication(self):
        """Regression test for the duplicate-recording bug: sending the
        full growing history to chat_with_model each turn must not cause
        earlier turns to be re-recorded into AIMemory. A 2-turn chat must
        record exactly 4 entries (2 user + 2 assistant), not 6+."""
        def fake_chat(model, history, record=True):
            resp = MagicMock()
            resp.content = "reply"
            resp.message.role = "assistant"
            resp.message.content = "reply"
            return resp
 
        fake_ctx = MagicMock()
        recorded = []
        fake_ctx.update_ai_memory.side_effect = (
            lambda role, content, metadata=None: recorded.append((role, content))
        )
 
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=fake_ctx), \
             patch("Janus.main.chat_with_model", side_effect=fake_chat), \
             patch("builtins.input", side_effect=["hi", "again", "quit"]):
            main.handle_chat(["mercury"])
 
        assert recorded == [
            ("user", "hi"),
            ("assistant", "reply"),
            ("user", "again"),
            ("assistant", "reply"),
        ]
 
    def test_records_reply_with_model_metadata(self):
        mock_response = MagicMock()
        mock_response.content = "hi"
        mock_response.message.role = "assistant"
        mock_response.message.content = "hi"
        fake_ctx = MagicMock()
 
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=fake_ctx), \
             patch("Janus.main.chat_with_model", return_value=mock_response), \
             patch("builtins.input", side_effect=["hello", "quit"]):
            main.handle_chat(["mercury"])
 
        fake_ctx.update_ai_memory.assert_any_call(
            "assistant", "hi", metadata={"model": "mercury"})
 
    def test_failed_turn_is_not_recorded(self):
        fake_ctx = MagicMock()
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=fake_ctx), \
             patch("Janus.main.chat_with_model", side_effect=RuntimeError("boom")), \
             patch("builtins.input", side_effect=["hello", "quit"]):
            main.handle_chat(["mercury"])
        fake_ctx.update_ai_memory.assert_not_called()
 
    def test_help_prompt_mentioned_on_start(self, capsys):
        with patch("Janus.main.start_ollama"), \
             patch("builtins.input", side_effect=["quit"]):
            main.handle_chat(["mercury"])
        assert "/help" in capsys.readouterr().out
 
 
class TestHandleChatSlashCommands:
    """Slash-commands typed inside the chat REPL, dispatched via
    _handle_chat_slash_command. Each is exercised through handle_chat's
    input loop so the routing (starts-with-'/') is covered too."""
 
    def _run_chat(self, inputs, ctx=None):
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=ctx), \
             patch("builtins.input", side_effect=inputs):
            main.handle_chat(["mercury"])
 
    def test_help_prints_command_list_without_context(self, capsys):
        """/help must work even with no context bound."""
        self._run_chat(["/help", "quit"], ctx=None)
        out = capsys.readouterr().out
        assert "/save" in out and "/note" in out and "/remember" in out
        assert "/condense" in out and "/history" in out
 
    def test_unbound_context_warns_for_memory_commands(self, capsys):
        self._run_chat(["/note hello", "quit"], ctx=None)
        assert "memory commands are unavailable" in capsys.readouterr().out
 
    def test_note_stores_conversation_note(self):
        fake_ctx = MagicMock()
        self._run_chat(["/note remember this detail", "quit"], ctx=fake_ctx)
        fake_ctx.store_conversation_note.assert_called_once_with("remember this detail")
 
    def test_note_without_text_prints_usage_and_does_not_call(self, capsys):
        fake_ctx = MagicMock()
        self._run_chat(["/note", "quit"], ctx=fake_ctx)
        fake_ctx.store_conversation_note.assert_not_called()
        assert "Usage: /note" in capsys.readouterr().out
 
    def test_remember_parses_key_value(self):
        fake_ctx = MagicMock()
        self._run_chat(["/remember favorite_lang=python", "quit"], ctx=fake_ctx)
        fake_ctx.remember_user_fact.assert_called_once_with("favorite_lang", "python")
 
    def test_remember_trims_whitespace_around_key_and_value(self):
        fake_ctx = MagicMock()
        self._run_chat(["/remember   name = Ada ", "quit"], ctx=fake_ctx)
        fake_ctx.remember_user_fact.assert_called_once_with("name", "Ada")
 
    def test_remember_without_equals_prints_usage(self, capsys):
        fake_ctx = MagicMock()
        self._run_chat(["/remember not-valid", "quit"], ctx=fake_ctx)
        fake_ctx.remember_user_fact.assert_not_called()
        assert "Usage: /remember" in capsys.readouterr().out
 
    def test_remember_with_empty_key_prints_usage(self, capsys):
        fake_ctx = MagicMock()
        self._run_chat(["/remember =value", "quit"], ctx=fake_ctx)
        fake_ctx.remember_user_fact.assert_not_called()
        assert "Usage: /remember" in capsys.readouterr().out
 
    def test_condense_default_keep_recent(self):
        fake_ctx = MagicMock()
        fake_ctx.condense_conversation.return_value = {"kind": "condensed_conversation"}
        self._run_chat(["/condense", "quit"], ctx=fake_ctx)
        fake_ctx.condense_conversation.assert_called_once_with(keep_recent=10)
 
    def test_condense_with_explicit_number(self):
        fake_ctx = MagicMock()
        fake_ctx.condense_conversation.return_value = {"kind": "condensed_conversation"}
        self._run_chat(["/condense 3", "quit"], ctx=fake_ctx)
        fake_ctx.condense_conversation.assert_called_once_with(keep_recent=3)
 
    def test_condense_with_invalid_number_prints_usage(self, capsys):
        fake_ctx = MagicMock()
        self._run_chat(["/condense notanumber", "quit"], ctx=fake_ctx)
        fake_ctx.condense_conversation.assert_not_called()
        assert "Usage: /condense" in capsys.readouterr().out
 
    def test_condense_prints_message_when_nothing_to_condense(self, capsys):
        fake_ctx = MagicMock()
        fake_ctx.condense_conversation.return_value = None
        self._run_chat(["/condense", "quit"], ctx=fake_ctx)
        assert "Nothing to condense" in capsys.readouterr().out
 
    def test_history_default_count(self):
        fake_ctx = MagicMock()
        fake_ctx.get_ai_context.return_value = []
        self._run_chat(["/history", "quit"], ctx=fake_ctx)
        fake_ctx.get_ai_context.assert_called_once_with(num_messages=10)
 
    def test_history_with_explicit_number(self):
        fake_ctx = MagicMock()
        fake_ctx.get_ai_context.return_value = []
        self._run_chat(["/history 5", "quit"], ctx=fake_ctx)
        fake_ctx.get_ai_context.assert_called_once_with(num_messages=5)
 
    def test_history_prints_entries(self, capsys):
        fake_ctx = MagicMock()
        fake_ctx.get_ai_context.return_value = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        self._run_chat(["/history", "quit"], ctx=fake_ctx)
        out = capsys.readouterr().out
        assert "hello" in out and "hi there" in out
 
    def test_history_prints_placeholder_when_empty(self, capsys):
        fake_ctx = MagicMock()
        fake_ctx.get_ai_context.return_value = []
        self._run_chat(["/history", "quit"], ctx=fake_ctx)
        assert "no recorded history" in capsys.readouterr().out
 
    def test_save_calls_shutdown_and_reopens_context(self):
        fake_ctx = MagicMock()
        self._run_chat(["/save", "quit"], ctx=fake_ctx)
        fake_ctx.shutdown.assert_called_once_with()
        # is_running must be restored so the chat loop can keep going
        assert fake_ctx.is_running is True
 
    def test_save_prints_confirmation(self, capsys):
        fake_ctx = MagicMock()
        self._run_chat(["/save", "quit"], ctx=fake_ctx)
        assert "Saved to disk" in capsys.readouterr().out
 
    def test_unknown_slash_command_prints_error(self, capsys):
        fake_ctx = MagicMock()
        self._run_chat(["/bogus", "quit"], ctx=fake_ctx)
        assert "Unknown command: /bogus" in capsys.readouterr().out
 
    def test_slash_command_does_not_reach_chat_with_model(self):
        fake_ctx = MagicMock()
        with patch("Janus.main.start_ollama"), \
             patch("Janus.main._get_context", return_value=fake_ctx), \
             patch("Janus.main.chat_with_model") as mock_chat, \
             patch("builtins.input", side_effect=["/note hi", "quit"]):
            main.handle_chat(["mercury"])
        mock_chat.assert_not_called()
 
 
class TestHandleHistory:
    """handle_history: read-only recall of saved AIMemory. Must never
    prompt to initialize a host project - it either finds an already
    initialized one (via host_marker_exists_at) or reports there's
    nothing to show."""
 
    def test_prints_message_when_no_initialized_project(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main.handle_history([])
        out = capsys.readouterr().out
        assert "No initialized Domus host project" in out
 
    def test_does_not_construct_context_when_no_marker(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("Mentis.context.RuntimeContext") as mock_ctx:
            main.handle_history([])
        mock_ctx.assert_not_called()
 
    def _init_marker(self, tmp_path):
        (tmp_path / ".domus-host-marker").touch()
        (tmp_path / ".domus-AI").mkdir()
 
    def _fake_ctx(self, conversation_history=None, conversation_notes=None, user_memory=None):
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True
        fake_ctx.ai_memory.conversation_history = conversation_history or []
        fake_ctx.ai_memory.conversation_notes = conversation_notes or []
        fake_ctx.ai_memory.user_memory = user_memory or {}
        return fake_ctx
 
    def test_loads_state_non_interactively_when_marker_present(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx()
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history([])
 
        fake_ctx.startup.assert_called_once()
        assert fake_ctx.startup.call_args.kwargs.get("non_interactive") is True
 
    def test_prints_placeholder_when_history_empty(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx()
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history([])
 
        assert "no recorded chat/ask history" in capsys.readouterr().out
 
    def test_prints_recorded_turns(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx(conversation_history=[
            {"timestamp": "t1", "role": "user", "content": "hello"},
            {"timestamp": "t2", "role": "assistant", "content": "hi there",
             "metadata": {"model": "mercury"}},
        ])
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history([])
 
        out = capsys.readouterr().out
        assert "hello" in out
        assert "hi there" in out
        assert "mercury" in out
 
    def test_default_limit_is_20(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        history = [
            {"timestamp": f"t{i}", "role": "user", "content": f"msg{i}"}
            for i in range(30)
        ]
        fake_ctx = self._fake_ctx(conversation_history=history)
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history([])
 
        out = capsys.readouterr().out
        assert "msg0" not in out          # trimmed - outside the last 20
        assert "msg29" in out             # most recent, must be shown
        assert "last 20 of 30" in out
 
    def test_explicit_number_limits_output(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        history = [
            {"timestamp": f"t{i}", "role": "user", "content": f"msg{i}"}
            for i in range(5)
        ]
        fake_ctx = self._fake_ctx(conversation_history=history)
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history(["2"])
 
        out = capsys.readouterr().out
        assert "msg0" not in out
        assert "msg3" in out and "msg4" in out
        assert "last 2 of 5" in out
 
    def test_model_filter_only_shows_matching_turns(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx(conversation_history=[
            {"timestamp": "t1", "role": "assistant", "content": "from mercury",
             "metadata": {"model": "mercury"}},
            {"timestamp": "t2", "role": "assistant", "content": "from venus",
             "metadata": {"model": "venus"}},
        ])
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history(["--model", "mercury"])
 
        out = capsys.readouterr().out
        assert "from mercury" in out
        assert "from venus" not in out
 
    def test_notes_flag_shows_notes_instead_of_history(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx(
            conversation_history=[{"timestamp": "t1", "role": "user", "content": "hidden"}],
            conversation_notes=[{"timestamp": "t2", "kind": "note", "content": "a durable note"}],
        )
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history(["--notes"])
 
        out = capsys.readouterr().out
        assert "a durable note" in out
        assert "hidden" not in out
 
    def test_notes_flag_placeholder_when_empty(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx()
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history(["--notes"])
 
        assert "no notes stored" in capsys.readouterr().out
 
    def test_facts_flag_shows_user_memory(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx(user_memory={
            "favorite_lang": {"value": "python", "updated_at": "t1"},
        })
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history(["--facts"])
 
        out = capsys.readouterr().out
        assert "favorite_lang" in out
        assert "python" in out
 
    def test_facts_flag_placeholder_when_empty(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx()
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history(["--facts"])
 
        assert "no user facts remembered" in capsys.readouterr().out
 
    def test_prints_error_when_startup_fails(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx()
        fake_ctx.startup.return_value = False
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history([])
 
        assert "Could not load saved state" in capsys.readouterr().out
 
    def test_does_not_call_shutdown(self, tmp_path, monkeypatch):
        """history is read-only recall - it must not persist anything
        back to disk (no ctx.shutdown() call)."""
        monkeypatch.chdir(tmp_path)
        self._init_marker(tmp_path)
        fake_ctx = self._fake_ctx()
 
        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx):
            main.handle_history([])
 
        fake_ctx.shutdown.assert_not_called()
 


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