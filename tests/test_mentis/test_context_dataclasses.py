"""Tests for the small dataclasses in Mentis/context.py."""

import pytest

from Mentis.context import ContextEvent, ContextEventType, AIMemory, ProjectConfig
from Hestia.types import ModelSize

pytestmark = pytest.mark.mentis


class TestContextEvent:
    def test_to_dict_converts_enum_and_carries_fields(self):
        event = ContextEvent(
            timestamp="2026-01-01T00:00:00",
            event_type=ContextEventType.STARTUP,
            message="started",
            metadata={"k": "v"},
        )
        data = event.to_dict()
        assert data == {
            "timestamp": "2026-01-01T00:00:00",
            "event_type": "startup",
            "message": "started",
            "metadata": {"k": "v"},
        }

    def test_metadata_defaults_to_empty_dict(self):
        event = ContextEvent(timestamp="t", event_type=ContextEventType.ERROR, message="m")
        assert event.metadata == {}


class TestAIMemory:
    def test_add_message_appends_entry_with_expected_shape(self):
        memory = AIMemory()
        memory.add_message("user", "hello", {"source": "test"})

        assert len(memory.conversation_history) == 1
        entry = memory.conversation_history[0]
        assert entry["role"] == "user"
        assert entry["content"] == "hello"
        assert entry["metadata"] == {"source": "test"}
        assert "timestamp" in entry

    def test_add_message_metadata_defaults_to_empty_dict(self):
        memory = AIMemory()
        memory.add_message("user", "hi")
        assert memory.conversation_history[0]["metadata"] == {}

    def test_add_message_enforces_memory_limit(self):
        memory = AIMemory(memory_limit_entries=3)
        for i in range(5):
            memory.add_message("user", f"message {i}")

        assert len(memory.conversation_history) == 3
        # Oldest messages should have been dropped, newest retained.
        contents = [m["content"] for m in memory.conversation_history]
        assert contents == ["message 2", "message 3", "message 4"]

    def test_get_recent_context_returns_last_n_messages(self):
        memory = AIMemory()
        for i in range(5):
            memory.add_message("user", f"m{i}")

        recent = memory.get_recent_context(num_messages=2)

        assert len(recent) == 2
        assert recent[-1]["content"] == "m4"

    def test_get_recent_context_empty_when_no_history(self):
        memory = AIMemory()
        assert memory.get_recent_context() == []

    def test_clear_history_empties_conversation(self):
        memory = AIMemory()
        memory.add_message("user", "hi")
        memory.clear_history()
        assert memory.conversation_history == []

    def test_to_dict_excludes_memory_limit_entries(self):
        """
        to_dict() intentionally omits memory_limit_entries (an internal
        tuning knob, not conversational state) - pin that omission so a
        future edit adding/removing dict keys is a visible, deliberate
        change.
        """
        memory = AIMemory()
        data = memory.to_dict()
        assert set(data.keys()) == {
            "conversation_history", "learned_preferences",
            "system_instructions", "context_window_size",
        }


class TestProjectConfig:
    def test_defaults(self):
        config = ProjectConfig(name="MyProject")
        assert config.version == "0.0.1"
        assert config.default_model == "mistral:7b"
        assert config.model_size_preference == ModelSize.SMALL
        assert config.enable_safety_checks is True
        assert config.custom_settings == {}

    def test_to_dict_converts_model_size_enum(self):
        config = ProjectConfig(name="MyProject", model_size_preference=ModelSize.LARGE)
        data = config.to_dict()
        assert data["model_size_preference"] == "large"

    def test_to_dict_includes_all_fields(self):
        config = ProjectConfig(name="MyProject")
        data = config.to_dict()
        assert data["name"] == "MyProject"
        assert "created_at" in data
        assert "custom_settings" in data

    def test_each_instance_gets_independent_custom_settings(self):
        """Guards against a shared-mutable-default bug (dict as class default)."""
        a = ProjectConfig(name="A")
        b = ProjectConfig(name="B")
        a.custom_settings["only_on_a"] = True
        assert "only_on_a" not in b.custom_settings