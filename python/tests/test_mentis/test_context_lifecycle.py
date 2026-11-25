"""
Tests for RuntimeContext's lifecycle: construction, startup(), shutdown().

startup()/shutdown() touch disk (via Janus.paths' host-project directories)
and run real hardware detection unless mocked, so every test here uses
the isolated host_project_dir fixture and (for startup/shutdown tests)
mocks hardware detection via the started_context fixture in conftest.py.
"""

import pytest

from Mentis.context import RuntimeContext, RuntimeMode

pytestmark = pytest.mark.mentis


class TestConstruction:
    def test_construction_is_side_effect_free(self, tmp_path, monkeypatch):
        """
        Per RuntimeContext.__init__'s own docstring, constructing it must
        NOT touch disk or resolve real directories. We assert this by
        making LOCAL_AI_RUNTIME_HOST point somewhere that doesn't exist -
        if construction tried to resolve/create it, this would raise.
        """
        monkeypatch.setenv("LOCAL_AI_RUNTIME_HOST", str(tmp_path / "does_not_exist"))
        ctx = RuntimeContext(project_name="Test")  # must not raise
        assert ctx.is_running is False
        assert ctx.project_dir is None
        assert ctx.working_dir is None

    def test_default_project_name(self):
        ctx = RuntimeContext()
        assert ctx.project_name == "DefaultProject"

    def test_custom_project_name_and_mode(self):
        ctx = RuntimeContext(project_name="Custom", mode=RuntimeMode.PRODUCTION)
        assert ctx.project_name == "Custom"
        assert ctx.mode == RuntimeMode.PRODUCTION

    def test_default_mode_is_development(self):
        ctx = RuntimeContext()
        assert ctx.mode == RuntimeMode.DEVELOPMENT

    def test_config_uses_project_name(self):
        ctx = RuntimeContext(project_name="Custom")
        assert ctx.config.name == "Custom"

    def test_starts_with_empty_state(self):
        ctx = RuntimeContext()
        assert ctx.loaded_models == {}
        assert ctx.events == []
        assert ctx.total_inference_runs == 0
        assert ctx.total_tokens_processed == 0
        assert ctx.hardware_profile is None
        assert ctx.model_recommendation is None


class TestStartup:
    def test_startup_returns_true_on_success(self, started_context):
        assert started_context.is_running is True

    def test_startup_resolves_directories(self, started_context, host_project_dir):
        assert started_context.project_dir == host_project_dir
        assert started_context.working_dir == host_project_dir / ".ai-runtime"
        assert started_context.cache_dir is not None
        assert started_context.logs_dir is not None

    def test_startup_creates_directories_on_disk(self, started_context):
        assert started_context.cache_dir.exists()
        assert started_context.logs_dir.exists()
        assert started_context.models_dir.exists()
        assert started_context.memory_dir.exists()
        assert started_context.config_dir.exists()

    def test_runtime_log_collects_multiple_subsystem_categories(self, started_context):
        from utils import get_log_category, livy

        get_log_category("Janus.main").info("janus runtime check")
        get_log_category("Faber.models").info("faber runtime check")
        assert livy.log_file.parent == started_context.logs_dir
        text = livy.log_file.read_text()
        assert "[Mentis] Runtime context startup complete" in text
        assert "[Janus] janus runtime check" in text
        assert "[Faber] faber runtime check" in text

    def test_logging_failure_does_not_start_context(self, context, host_project_dir, monkeypatch):
        def fail_logging():
            raise RuntimeError("log unavailable")

        monkeypatch.setattr(context, "_setup_logging", fail_logging)
        assert not context.startup(suggested_host=host_project_dir, non_interactive=True)
        assert not context.is_running

    def test_startup_sets_hardware_profile(self, started_context, fake_hardware_profile):
        assert started_context.hardware_profile is fake_hardware_profile

    def test_startup_sets_model_recommendation(self, started_context, fake_model_recommendation):
        assert started_context.model_recommendation is fake_model_recommendation

    def test_startup_passes_recommendation_weight(
        self, host_project_dir, fake_hardware_profile, fake_model_recommendation, monkeypatch,
    ):
        from unittest.mock import MagicMock
        from Hestia.models import ModelRecommendationWeight
        from Mentis.context import RuntimeContext

        weight = ModelRecommendationWeight(
            max_memory_gb=6, max_parameters_billions=8,
            include_capabilities={"tools"}, exclude_capabilities={"vision"},
            include_families={"qwen3"},
        )
        monkeypatch.setattr(
            "Mentis.context.HardwareDetector",
            lambda: MagicMock(detect=MagicMock(return_value=fake_hardware_profile)),
        )
        recommender = MagicMock(return_value=MagicMock(
            recommend=MagicMock(return_value=fake_model_recommendation),
        ))
        monkeypatch.setattr("Mentis.context.ModelRecommender", recommender)
        context = RuntimeContext(recommendation_weight=weight)

        assert context.startup(suggested_host=host_project_dir, non_interactive=True)
        recommender.assert_called_once_with(fake_hardware_profile, weight=weight)
        assert context.model_recommendation is fake_model_recommendation

    def test_startup_records_startup_event(self, started_context):
        from Mentis.context import ContextEventType
        assert any(e.event_type == ContextEventType.STARTUP for e in started_context.events)

    def test_startup_sets_startup_time(self, started_context):
        assert started_context.startup_time is not None

    def test_startup_returns_false_on_invalid_host(self, context, monkeypatch, tmp_path):
        """
        initialize_host() raises RuntimeError for a nonexistent
        non-interactive path - startup() should catch that and return
        False rather than propagating.
        """
        nonexistent = tmp_path / "does_not_exist_at_all"
        result = context.startup(suggested_host=nonexistent, non_interactive=True)
        assert result is False
        assert context.is_running is False


class TestShutdown:
    def test_shutdown_returns_true(self, started_context):
        assert started_context.shutdown() is True

    def test_shutdown_sets_is_running_false(self, started_context):
        started_context.shutdown()
        assert started_context.is_running is False

    def test_shutdown_sets_shutdown_time(self, started_context):
        started_context.shutdown()
        assert started_context.shutdown_time is not None

    def test_shutdown_unloads_all_models(self, started_context):
        started_context.load_model("model-a")
        started_context.load_model("model-b")

        started_context.shutdown()

        assert started_context.loaded_models == {}

    def test_shutdown_writes_state_to_disk(self, started_context):
        started_context.shutdown()

        assert (started_context.config_dir / "config.json").exists()
        assert (started_context.memory_dir / "ai_memory.json").exists()
        assert (started_context.logs_dir / "events.json").exists()

    def test_shutdown_records_shutdown_event(self, started_context):
        from Mentis.context import ContextEventType
        started_context.shutdown()
        assert any(e.event_type == ContextEventType.SHUTDOWN for e in started_context.events)