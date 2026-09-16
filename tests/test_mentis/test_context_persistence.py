"""
Tests for RuntimeContext state persistence: _save_state() -> disk ->
_load_saved_state() on a fresh context pointed at the same host.

Both sides use the isolated host_project_dir fixture so nothing is
written outside tmp_path, and hardware detection is mocked via the
started_context fixture.
"""

import pytest

from Hestia.types import ModelSize
from Mentis.context import RuntimeContext

pytestmark = pytest.mark.mentis


class TestPersistenceRoundTrip:
    def _start_fresh(self, monkeypatch, host_project_dir, fake_hardware_profile, fake_model_recommendation):
        """Start a new RuntimeContext on the same host as a previous one."""
        from unittest.mock import MagicMock

        monkeypatch.setattr(
            "Mentis.context.HardwareDetector",
            lambda: MagicMock(detect=MagicMock(return_value=fake_hardware_profile)),
        )
        monkeypatch.setattr(
            "Mentis.context.ModelRecommender",
            lambda profile: MagicMock(recommend=MagicMock(return_value=fake_model_recommendation)),
        )
        ctx = RuntimeContext(project_name="TestProject")
        assert ctx.startup(suggested_host=host_project_dir, non_interactive=True)
        return ctx

    def test_config_round_trip(self, started_context, host_project_dir, monkeypatch,
                               fake_hardware_profile, fake_model_recommendation):
        started_context.config.default_model = "custom:9b"
        started_context.config.timeout_seconds = 42
        started_context.config.model_size_preference = ModelSize.LARGE
        started_context._save_state()

        ctx2 = self._start_fresh(monkeypatch, host_project_dir,
                                 fake_hardware_profile, fake_model_recommendation)

        assert ctx2.config.default_model == "custom:9b"
        assert ctx2.config.timeout_seconds == 42
        assert ctx2.config.model_size_preference is ModelSize.LARGE

    def test_ai_memory_round_trip(self, started_context, host_project_dir, monkeypatch,
                                  fake_hardware_profile, fake_model_recommendation):
        started_context.ai_memory.add_message("user", "hello")
        started_context.ai_memory.learned_preferences["theme"] = "dark"
        started_context.ai_memory.system_instructions = "be terse"
        started_context._save_state()

        ctx2 = self._start_fresh(monkeypatch, host_project_dir,
                                 fake_hardware_profile, fake_model_recommendation)

        assert ctx2.ai_memory.conversation_history[0]["content"] == "hello"
        assert ctx2.ai_memory.learned_preferences["theme"] == "dark"
        assert ctx2.ai_memory.system_instructions == "be terse"

    def test_unknown_config_keys_are_ignored(self, started_context, host_project_dir, monkeypatch,
                                             fake_hardware_profile, fake_model_recommendation):
        started_context._restore_config({"future_field": 123, "timeout_seconds": 7})

        assert started_context.config.timeout_seconds == 7
        assert not hasattr(started_context.config, "future_field")

    def test_missing_saved_files_keep_defaults(self, started_context):
        # Fresh host has no saved state - startup already ran, values are defaults
        assert started_context.config.default_model == "mistral:7b"
        assert started_context.ai_memory.conversation_history == []

    def test_corrupt_config_file_degrades_gracefully(self, started_context, host_project_dir,
                                                     monkeypatch, fake_hardware_profile,
                                                     fake_model_recommendation):
        started_context.config_dir.mkdir(parents=True, exist_ok=True)
        (started_context.config_dir / "config.json").write_text("{ not json")

        ctx2 = self._start_fresh(monkeypatch, host_project_dir,
                                 fake_hardware_profile, fake_model_recommendation)

        assert ctx2.config.default_model == "mistral:7b"  # defaults kept, no crash
