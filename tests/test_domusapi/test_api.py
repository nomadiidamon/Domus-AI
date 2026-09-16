"""
Tests for DomusAPI/__init__.py - the stable top-level wrapper.

Every wrapper delegates to a subsystem; these tests mock the subsystem
functions and assert DomusAPI passes arguments through, returns values,
and raises errors (never sys.exit / print-and-swallow - that's the CLI's
job, pinned explicitly below).
"""

from unittest.mock import MagicMock, patch

import pytest

import DomusAPI

pytestmark = pytest.mark.domusapi


class TestInitShutdown:
    def test_init_starts_context_and_bus_and_binds_faber(self):
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx) as mock_ctx_cls, \
             patch("Faber.models.set_context") as mock_set_context, \
             patch("Mercurius.initialize_bus") as mock_bus:
            result = DomusAPI.init()

        assert result is fake_ctx
        fake_ctx.startup.assert_called_once()
        assert fake_ctx.startup.call_args[1]["non_interactive"] is True
        mock_set_context.assert_called_once_with(fake_ctx)
        mock_bus.assert_called_once_with()

    def test_init_is_idempotent(self):
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx) as mock_ctx_cls, \
             patch("Faber.models.set_context"), \
             patch("Mercurius.initialize_bus"):
            first = DomusAPI.init()
            second = DomusAPI.init()

        assert first is second
        assert mock_ctx_cls.call_count == 1

    def test_init_raises_when_context_startup_fails(self):
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = False

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Mercurius.initialize_bus"):
            with pytest.raises(RuntimeError, match="startup failed"):
                DomusAPI.init()

    def test_shutdown_releases_everything(self):
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Mercurius.initialize_bus"):
            DomusAPI.init()

        with patch("Mercurius.shutdown_bus") as mock_shutdown_bus, \
             patch("Faber.models.set_context") as mock_set_context:
            DomusAPI.shutdown()

        fake_ctx.shutdown.assert_called_once()
        mock_shutdown_bus.assert_called_once()
        # Context shuts down BEFORE the bus so Mentis' final events drain
        ctx_order = fake_ctx.shutdown.call_args
        assert DomusAPI._context is None

    def test_shutdown_without_init_does_not_raise(self):
        with patch("Mercurius.shutdown_bus"):
            DomusAPI.shutdown()  # must not raise

    def test_failed_init_leaves_no_partial_state(self):
        """If any init step fails, module state must stay clean so a retry
        starts from scratch (review finding: partial init leaked _context)."""
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = True

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Mercurius.initialize_bus", side_effect=RuntimeError("bus broke")), \
             patch("Mercurius.shutdown_bus") as mock_shutdown_bus:
            with pytest.raises(RuntimeError, match="bus broke"):
                DomusAPI.init()

        assert DomusAPI._context is None
        mock_shutdown_bus.assert_called_once()

    def test_failed_context_startup_raises_and_stays_clean(self):
        fake_ctx = MagicMock()
        fake_ctx.startup.return_value = False

        with patch("Mentis.context.RuntimeContext", return_value=fake_ctx), \
             patch("Faber.models.set_context"), \
             patch("Mercurius.initialize_bus"), \
             patch("Mercurius.shutdown_bus"):
            with pytest.raises(RuntimeError, match="startup failed"):
                DomusAPI.init()

        assert DomusAPI._context is None


class TestHardwareAndModels:
    def test_detect_hardware_delegates(self):
        with patch("Hestia.hardware.detect_hardware", return_value="profile") as mock_detect:
            assert DomusAPI.detect_hardware() == "profile"
        mock_detect.assert_called_once_with()

    def test_start_model_starts_ollama_first(self):
        with patch("Faber.ollama_service.start_ollama") as mock_ollama, \
             patch("Faber.models.start_model", return_value="session") as mock_start:
            result = DomusAPI.start_model("mercury")

        assert result == "session"
        mock_ollama.assert_called_once_with()
        mock_start.assert_called_once_with("mercury")

    def test_stop_model_returns_result(self):
        with patch("Faber.models.stop_model", return_value=True) as mock_stop:
            assert DomusAPI.stop_model("mercury") is True
        mock_stop.assert_called_once_with("mercury")

    @pytest.mark.parametrize("wrapper,faber_name", [
        ("pull_model", "pull_model"),
        ("build_model", "build_model"),
        ("remove_model", "remove_model"),
    ])
    def test_model_commands_delegate(self, wrapper, faber_name):
        with patch(f"Faber.models.{faber_name}") as mock_fn:
            getattr(DomusAPI, wrapper)("mercury")
        mock_fn.assert_called_once_with("mercury")

    def test_list_models_returns_parsed_list(self):
        models = [{"name": "mercury:latest", "id": "abc", "size": "4.7 GB", "modified": "today"}]
        with patch("Faber.models.list_models", return_value=models):
            assert DomusAPI.list_models() == models

    def test_status_returns_session_snapshot(self):
        with patch("Faber.session.get_status", return_value=[{"name": "mercury"}]) as mock_status:
            assert DomusAPI.status() == [{"name": "mercury"}]
        mock_status.assert_called_once_with()


class TestMessaging:
    def test_ask_returns_reply_text(self):
        fake_response = MagicMock()
        fake_response.content = "the answer"

        with patch("Faber.messaging.generate", return_value=fake_response) as mock_gen:
            result = DomusAPI.ask("mercury", "a question", system="be terse")

        assert result == "the answer"
        _, kwargs = mock_gen.call_args
        assert mock_gen.call_args[0][:2] == ("mercury", "a question")
        assert kwargs["system"] == "be terse"

    def test_chat_accepts_plain_dicts(self):
        from Faber.messaging import Message

        fake_response = MagicMock()
        fake_response.content = "reply"

        with patch("Faber.messaging.chat", return_value=fake_response) as mock_chat:
            result = DomusAPI.chat("mercury", [{"role": "user", "content": "hi"}])

        assert result == "reply"
        sent = mock_chat.call_args[0][1]
        assert sent == [Message("user", "hi")]

    def test_messaging_errors_propagate(self):
        with patch("Faber.messaging.generate", side_effect=RuntimeError("server down")):
            with pytest.raises(RuntimeError, match="server down"):
                DomusAPI.ask("mercury", "anything")


class TestMcp:
    def test_get_mcp_tools_delegates(self):
        with patch("Custos.mcp.MCPManager") as mock_mgr_cls:
            mock_mgr_cls.return_value.get_tools.return_value = {"filesystem": ["read_file"]}
            assert DomusAPI.get_mcp_tools("mercury") == {"filesystem": ["read_file"]}

    def test_allow_mcp_tool_delegates(self):
        with patch("Custos.mcp.MCPManager") as mock_mgr_cls:
            mock_mgr_cls.return_value.allow_tool.return_value = False
            assert DomusAPI.allow_mcp_tool("git_push", "minerva") is False
            mock_mgr_cls.return_value.allow_tool.assert_called_once_with("git_push", "minerva")


class TestEvents:
    def test_subscribe_initializes_bus_if_needed(self):
        with patch("Mercurius.get_bus", return_value=None), \
             patch("Mercurius.initialize_bus") as mock_init:
            bus = MagicMock()
            mock_init.return_value = bus
            DomusAPI.subscribe("event_type", "callback")

        bus.subscribe.assert_called_once_with("event_type", "callback")

    def test_subscribe_uses_running_bus(self):
        bus = MagicMock()
        with patch("Mercurius.get_bus", return_value=bus), \
             patch("Mercurius.initialize_bus") as mock_init:
            DomusAPI.subscribe("event_type", "callback")

        mock_init.assert_not_called()
        bus.subscribe.assert_called_once()

    def test_publish_delegates_to_module_helper(self):
        with patch("Mercurius.publish_event") as mock_publish:
            DomusAPI.publish("etype", payload={"k": "v"})
        mock_publish.assert_called_once_with("etype", source="domusapi", payload={"k": "v"})


class TestLibrarySafety:
    """DomusAPI must behave like a library: no exits, no prints."""

    def test_no_wrapper_calls_sys_exit(self):
        import inspect

        for name in DomusAPI.__all__:
            fn = getattr(DomusAPI, name)
            if callable(fn):
                source = inspect.getsource(fn)
                assert "sys.exit" not in source, f"{name} must not call sys.exit"

    def test_no_wrapper_prints(self):
        import inspect

        for name in DomusAPI.__all__:
            fn = getattr(DomusAPI, name)
            if callable(fn):
                source = inspect.getsource(fn)
                assert "print(" not in source, f"{name} must not print"
