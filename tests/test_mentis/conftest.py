"""Shared fixtures for Mentis (runtime context/state) tests."""

from unittest.mock import MagicMock

import pytest

from Hestia.hardware import HardwareProfile, ModelRecommendation
from Hestia.types import AcceleratorType, ModelSize


@pytest.fixture
def fake_hardware_profile():
    return HardwareProfile(
        cpu_count=8, cpu_cores_physical=4, cpu_cores_logical=8,
        cpu_frequency_ghz=3.0, cpu_brand="Test CPU",
        ram_total_gb=16.0, ram_available_gb=8.0,
        gpus=[], total_vram_gb=0.0,
        platform_name="Linux", platform_version="test", python_version="3.12",
        primary_accelerator=AcceleratorType.NONE,
        available_for_models_gb=5.6,
    )


@pytest.fixture
def fake_model_recommendation():
    return ModelRecommendation(
        model_size=ModelSize.SMALL,
        recommended_models=["test-model:1b"],
        thinking_models=[],
        tool_models=[],
        vision_models=[],
        max_context_tokens=8192,
        quantization_level="q4_k_m",
        batch_size=1,
        estimated_performance="fast",
        reasoning="test reasoning",
    )


@pytest.fixture
def context():
    """
    A plain, freshly-constructed RuntimeContext. Per its own docstring,
    construction is side-effect-free (no disk I/O), so this fixture
    needs no filesystem isolation — only startup()/shutdown() touch disk.
    """
    from Mentis.context import RuntimeContext
    return RuntimeContext(project_name="TestProject")


@pytest.fixture
def started_context(context, host_project_dir, fake_hardware_profile, fake_model_recommendation, monkeypatch):
    """
    A RuntimeContext that has been through startup() against an isolated
    host_project_dir, with hardware detection mocked out so tests don't
    depend on (or get slowed down by) real hardware probing.
    """
    monkeypatch.setattr(
        "Mentis.context.HardwareDetector",
        lambda: MagicMock(detect=MagicMock(return_value=fake_hardware_profile)),
    )
    monkeypatch.setattr(
        "Mentis.context.ModelRecommender",
        lambda profile: MagicMock(recommend=MagicMock(return_value=fake_model_recommendation)),
    )

    ok = context.startup(suggested_host=host_project_dir, non_interactive=True)
    assert ok, "fixture setup: startup() unexpectedly failed"
    return context