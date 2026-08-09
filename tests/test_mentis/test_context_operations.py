"""
Tests for RuntimeContext's runtime operations: model tracking, event
logging, AI memory, system status, and hardware refresh.

These operations don't require a full startup() (no disk I/O needed for
most of them), so most tests here use the plain `context` fixture rather
than `started_context` — only get_system_status()'s hardware/uptime
fields and refresh_hardware() specifically need hardware detection
mocked, which is done inline per-test rather than via full startup.
"""

from unittest.mock import MagicMock

import pytest

from Mentis.context import ContextEventType

pytestmark = pytest.mark.mentis


class TestLoadUnloadModel:
    def test_load_model_returns_true_and_registers(self, context):
        result = context.load_model("mercury", metadata={"pid": 123})
        assert result is True
        assert "mercury" in context.loaded_models
        assert context.loaded_models["mercury"]["metadata"] == {"pid": 123}

    def test_load_model_logs_event(self, context):
        context.load_model("mercury")
        assert any(e.event_type == ContextEventType.MODEL_LOADED for e in context.events)

    def test_unload_model_removes_and_returns_true(self, context):
        context.load_model("mercury")
        result = context.unload_model("mercury")
        assert result is True
        assert "mercury" not in context.loaded_models

    def test_unload_model_returns_false_when_not_loaded(self, context):
        assert context.unload_model("never_loaded") is False

    def test_unload_model_logs_event_only_when_present(self, context):
        context.unload_model("never_loaded")
        assert not any(e.event_type == ContextEventType.MODEL_UNLOADED for e in context.events)

        context.load_model("mercury")
        context.unload_model("mercury")
        assert any(e.event_type == ContextEventType.MODEL_UNLOADED for e in context.events)


class TestRecordInference:
    def test_increments_counters(self, context):
        context.record_inference("mercury", tokens_processed=100, latency_ms=50.0)
        context.record_inference("mercury", tokens_processed=50, latency_ms=25.0)

        assert context.total_inference_runs == 2
        assert context.total_tokens_processed == 150

    def test_logs_event(self, context):
        context.record_inference("mercury", tokens_processed=10, latency_ms=1.0)
        assert any(e.event_type == ContextEventType.INFERENCE_RUN for e in context.events)


class TestLogEvent:
    def test_appends_event(self, context):
        context.log_event(ContextEventType.WARNING, "something happened")
        assert len(context.events) == 1
        assert context.events[0].message == "something happened"

    def test_enforces_max_events_memory(self, context):
        context.max_events_memory = 3
        for i in range(5):
            context.log_event(ContextEventType.WARNING, f"event {i}")

        assert len(context.events) == 3
        messages = [e.message for e in context.events]
        assert messages == ["event 2", "event 3", "event 4"]

    def test_metadata_defaults_to_empty_dict(self, context):
        context.log_event(ContextEventType.WARNING, "msg")
        assert context.events[0].metadata == {}


class TestAiMemoryDelegation:
    def test_update_ai_memory_adds_message(self, context):
        context.update_ai_memory("user", "hello")
        assert len(context.ai_memory.conversation_history) == 1

    def test_get_ai_context_returns_recent_messages(self, context):
        for i in range(3):
            context.update_ai_memory("user", f"m{i}")

        result = context.get_ai_context(num_messages=2)

        assert len(result) == 2


class TestGetActiveSessions:
    def test_empty_when_no_sessions(self, context):
        assert context.get_active_sessions() == {}

    def test_reports_session_details(self, context):
        from Faber.session import create_session

        class FakeProcess:
            pid = 999

            def poll(self):
                return None

        create_session("test-session", FakeProcess(), "test", {"note": "hi"})

        result = context.get_active_sessions()

        assert "test-session" in result
        entry = result["test-session"]
        assert entry["type"] == "test"
        assert entry["running"] is True
        assert entry["pid"] == 999
        assert entry["metadata"] == {"note": "hi"}


class TestGetSystemStatus:
    def test_reports_expected_shape(self, context):
        status = context.get_system_status()

        assert set(status.keys()) == {
            "is_running", "mode", "uptime_seconds", "active_sessions",
            "loaded_models", "active_requests", "total_inference_runs",
            "total_tokens_processed", "hardware", "recommendation",
        }

    def test_uptime_none_before_startup(self, context):
        status = context.get_system_status()
        assert status["uptime_seconds"] is None

    def test_hardware_and_recommendation_none_before_detection(self, context):
        status = context.get_system_status()
        assert status["hardware"] is None
        assert status["recommendation"] is None

    def test_reflects_loaded_models(self, context):
        context.load_model("mercury")
        status = context.get_system_status()
        assert status["loaded_models"] == ["mercury"]


class TestGetMemoryUsage:
    def test_empty_dict_when_no_hardware_profile(self, context):
        assert context.get_memory_usage() == {}

    def test_reports_profile_fields_when_present(self, context, fake_hardware_profile):
        context.hardware_profile = fake_hardware_profile
        usage = context.get_memory_usage()

        assert usage["ram_total_gb"] == fake_hardware_profile.ram_total_gb
        assert usage["ram_available_gb"] == fake_hardware_profile.ram_available_gb
        assert usage["vram_total_gb"] == fake_hardware_profile.total_vram_gb


class TestRefreshHardware:
    def test_updates_profile_on_success(self, context, monkeypatch, fake_hardware_profile):
        monkeypatch.setattr(
            "Mentis.context.HardwareDetector",
            lambda: MagicMock(detect=MagicMock(return_value=fake_hardware_profile)),
        )
        monkeypatch.setattr(
            "Mentis.context.ModelRecommender",
            lambda profile: MagicMock(recommend=MagicMock(return_value=MagicMock())),
        )

        result = context.refresh_hardware()

        assert result is True
        assert context.hardware_profile is fake_hardware_profile

    def test_retains_previous_profile_on_detection_failure(self, context, fake_hardware_profile):
        context.hardware_profile = fake_hardware_profile

        # _detect_hardware() swallows exceptions internally and just
        # leaves hardware_profile as whatever it already was (None if
        # never set) — simulate a failed detection by pointing at a
        # HardwareDetector whose .detect() raises, which _detect_hardware
        # catches, so hardware_profile is left untouched by that call.
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "Mentis.context.HardwareDetector",
                lambda: MagicMock(detect=MagicMock(side_effect=RuntimeError("boom"))),
            )
            result = context.refresh_hardware()

        assert result is True  # profile is still the previous non-None one
        assert context.hardware_profile is fake_hardware_profile

    def test_logs_state_changed_event_on_success(self, context, monkeypatch, fake_hardware_profile):
        monkeypatch.setattr(
            "Mentis.context.HardwareDetector",
            lambda: MagicMock(detect=MagicMock(return_value=fake_hardware_profile)),
        )
        monkeypatch.setattr(
            "Mentis.context.ModelRecommender",
            lambda profile: MagicMock(recommend=MagicMock(return_value=MagicMock())),
        )

        context.refresh_hardware()

        assert any(e.event_type == ContextEventType.STATE_CHANGED for e in context.events)


class TestExportState:
    def test_export_state_has_expected_shape(self, context):
        exported = context.export_state()

        assert set(exported.keys()) == {
            "project_name", "mode", "config", "ai_memory",
            "hardware", "status", "events",
        }
        assert exported["project_name"] == context.project_name
        assert exported["mode"] == context.mode.value

    def test_export_state_caps_events_at_100(self, context):
        for i in range(150):
            context.log_event(ContextEventType.WARNING, f"event {i}")

        exported = context.export_state()

        assert len(exported["events"]) == 100
        # Should be the *last* 100, i.e. most recent.
        assert exported["events"][-1]["message"] == "event 149"


class TestGlobalContextSingleton:
    def test_get_context_returns_same_instance_across_calls(self):
        from Mentis.context import get_context
        first = get_context()
        second = get_context()
        assert first is second

    def test_initialize_context_replaces_global_instance(self):
        from Mentis.context import get_context, initialize_context

        first = get_context()
        second = initialize_context(project_name="ReplacedProject")

        assert second is not first
        assert second.project_name == "ReplacedProject"
        assert get_context() is second