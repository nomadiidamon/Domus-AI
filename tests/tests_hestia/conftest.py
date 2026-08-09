"""Shared fixtures for Hestia (hardware detection / model catalog) tests."""

import pytest

from Hestia.hardware import GPUInfo, HardwareProfile
from Hestia.types import AcceleratorType, ModelSize


@pytest.fixture
def sample_gpu():
    """A single well-formed NVIDIA GPUInfo, useful wherever a GPU is needed."""
    return GPUInfo(
        index=0,
        name="Test GPU 3000",
        accelerator=AcceleratorType.NVIDIA_CUDA,
        total_memory_gb=8.0,
        free_memory_gb=6.0,
        compute_capability="8.6",
        driver_version="550.00",
        is_available=True,
    )


@pytest.fixture
def cpu_only_profile():
    """A HardwareProfile representing a machine with no GPU at all."""
    return HardwareProfile(
        cpu_count=8,
        cpu_cores_physical=4,
        cpu_cores_logical=8,
        cpu_frequency_ghz=3.2,
        cpu_brand="Test CPU",
        ram_total_gb=16.0,
        ram_available_gb=8.0,
        gpus=[],
        total_vram_gb=0.0,
        platform_name="Linux",
        platform_version="test",
        python_version="3.12.0",
        primary_accelerator=AcceleratorType.NONE,
        available_for_models_gb=5.6,
    )


@pytest.fixture
def nvidia_profile(sample_gpu):
    """A HardwareProfile representing a machine with one NVIDIA GPU."""
    return HardwareProfile(
        cpu_count=16,
        cpu_cores_physical=8,
        cpu_cores_logical=16,
        cpu_frequency_ghz=3.8,
        cpu_brand="Test CPU Pro",
        ram_total_gb=32.0,
        ram_available_gb=24.0,
        gpus=[sample_gpu],
        total_vram_gb=8.0,
        platform_name="Linux",
        platform_version="test",
        python_version="3.12.0",
        primary_accelerator=AcceleratorType.NVIDIA_CUDA,
        available_for_models_gb=4.8,
    )