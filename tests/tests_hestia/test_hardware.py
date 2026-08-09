"""
Tests for Hestia/hardware.py

hardware.py talks to real hardware (psutil, nvidia-ml-py, subprocess
calls to rocm-smi/system_profiler/wmic). None of that is safe or
reliable to hit in a unit test, so every GPU-vendor-specific detector is
tested by mocking its subprocess/library call rather than by running it
for real. detect_hardware() end-to-end is exercised too, but only
against whatever real hardware happens to be running the tests, so its
assertions are limited to structural invariants (types, non-negative
numbers) rather than specific values.
"""

import json
import subprocess
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from Hestia.hardware import (
    GPUInfo,
    HardwareProfile,
    HardwareDetector,
    ModelRecommendation,
    ModelRecommender,
    detect_hardware,
    recommend_model,
    get_system_summary,
)
from Hestia.types import AcceleratorType, ModelSize

pytestmark = pytest.mark.hestia


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
class TestGPUInfo:
    def test_defaults(self):
        gpu = GPUInfo(
            index=0, name="X", accelerator=AcceleratorType.NVIDIA_CUDA,
            total_memory_gb=8.0, free_memory_gb=4.0,
        )
        assert gpu.compute_capability is None
        assert gpu.driver_version is None
        assert gpu.is_available is True


class TestHardwareProfileToDict:
    def test_to_dict_serializes_top_level_accelerator_to_string(self, nvidia_profile):
        data = nvidia_profile.to_dict()
        assert data["primary_accelerator"] == "nvidia_cuda"
        assert isinstance(data["gpus"], list)

    @pytest.mark.xfail(
        reason="known bug: HardwareProfile.to_dict() converts the top-level "
               "primary_accelerator enum to .value but not each GPUInfo's "
               "own .accelerator enum, so the per-GPU field stays an "
               "AcceleratorType instance instead of a string. Fix in "
               "hardware.py's to_dict(), not here.",
        strict=True,
    )
    def test_to_dict_serializes_per_gpu_accelerator_to_string(self, nvidia_profile):
        data = nvidia_profile.to_dict()
        assert data["gpus"][0]["accelerator"] == "nvidia_cuda"

    @pytest.mark.xfail(
        reason="known bug: per-GPU accelerator enum isn't converted by "
               "to_dict(), so the resulting dict isn't actually "
               "JSON-serializable despite the docstring's promise. See "
               "test_to_dict_serializes_per_gpu_accelerator_to_string.",
        strict=True,
    )
    def test_to_dict_is_json_serializable(self, nvidia_profile):
        data = nvidia_profile.to_dict()
        json.dumps(data)  # must not raise

    def test_to_dict_cpu_only(self, cpu_only_profile):
        data = cpu_only_profile.to_dict()
        assert data["gpus"] == []
        assert data["primary_accelerator"] == "none"


# ---------------------------------------------------------------------------
# HardwareDetector._detect_nvidia_gpus
# ---------------------------------------------------------------------------
class TestDetectNvidiaGpus:
    def test_no_pynvml_installed_returns_empty_list(self):
        detector = HardwareDetector()
        with patch.dict("sys.modules", {"pynvml": None}):
            result = detector._detect_nvidia_gpus()
        assert result == []

    def test_parses_single_gpu(self):
        detector = HardwareDetector()

        fake_pynvml = MagicMock()
        fake_pynvml.nvmlSystemGetDriverVersion.return_value = "550.00"
        fake_pynvml.nvmlDeviceGetCount.return_value = 1
        fake_handle = MagicMock()
        fake_pynvml.nvmlDeviceGetHandleByIndex.return_value = fake_handle
        fake_pynvml.nvmlDeviceGetName.return_value = "Test NVIDIA GPU"
        fake_mem = MagicMock()
        fake_mem.total = 8 * (1024 ** 3)
        fake_mem.free = 6 * (1024 ** 3)
        fake_pynvml.nvmlDeviceGetMemoryInfo.return_value = fake_mem
        fake_pynvml.nvmlDeviceGetCudaComputeCapability.return_value = (8, 6)

        with patch.dict("sys.modules", {"pynvml": fake_pynvml}):
            result = detector._detect_nvidia_gpus()

        assert len(result) == 1
        gpu = result[0]
        assert gpu.name == "Test NVIDIA GPU"
        assert gpu.accelerator == AcceleratorType.NVIDIA_CUDA
        assert gpu.total_memory_gb == pytest.approx(8.0)
        assert gpu.free_memory_gb == pytest.approx(6.0)
        assert gpu.compute_capability == "8.6"
        assert gpu.driver_version == "550.00"

    def test_nvml_exception_returns_empty_list_not_raise(self):
        detector = HardwareDetector()
        fake_pynvml = MagicMock()
        fake_pynvml.nvmlInit.side_effect = RuntimeError("no driver")

        with patch.dict("sys.modules", {"pynvml": fake_pynvml}):
            result = detector._detect_nvidia_gpus()

        assert result == []


# ---------------------------------------------------------------------------
# HardwareDetector._detect_amd_gpus
# ---------------------------------------------------------------------------
class TestDetectAmdGpus:
    def test_rocm_smi_not_found_returns_empty_list(self):
        detector = HardwareDetector()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = detector._detect_amd_gpus()
        assert result == []

    def test_rocm_smi_nonzero_exit_returns_empty_list(self):
        detector = HardwareDetector()
        fake_result = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=fake_result):
            result = detector._detect_amd_gpus()
        assert result == []

    def test_parses_rocm_smi_json(self):
        detector = HardwareDetector()
        payload = {
            "card0": {
                "VRAM Total Memory (B)": str(16 * 1024 ** 3),
                "VRAM Total Used Memory (B)": str(4 * 1024 ** 3),
            }
        }
        meminfo_result = MagicMock(returncode=0, stdout=json.dumps(payload))

        with patch("subprocess.run", return_value=meminfo_result), \
             patch.object(detector, "_get_amd_gpu_name", return_value="Test AMD GPU"):
            result = detector._detect_amd_gpus()

        assert len(result) == 1
        gpu = result[0]
        assert gpu.name == "Test AMD GPU"
        assert gpu.accelerator == AcceleratorType.AMD_ROCM
        assert gpu.total_memory_gb == pytest.approx(16.0)
        assert gpu.free_memory_gb == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# HardwareDetector._detect_apple_gpus
# ---------------------------------------------------------------------------
class TestDetectAppleGpus:
    def test_skipped_on_non_darwin(self):
        detector = HardwareDetector()
        with patch("platform.system", return_value="Linux"):
            result = detector._detect_apple_gpus()
        assert result == []

    def test_parses_system_profiler_json_on_darwin(self):
        detector = HardwareDetector()
        payload = {
            "SPDisplaysDataType": [
                {"sppci_model": "Apple M-Test", "spdisplays_vram_shared": "16 GB"}
            ]
        }
        fake_result = MagicMock(returncode=0, stdout=json.dumps(payload))

        with patch("platform.system", return_value="Darwin"), \
             patch("subprocess.run", return_value=fake_result):
            result = detector._detect_apple_gpus()

        assert len(result) == 1
        assert result[0].name == "Apple M-Test"
        assert result[0].total_memory_gb == pytest.approx(16.0)
        assert result[0].accelerator == AcceleratorType.APPLE_METAL

    def test_parse_apple_vram_mb(self):
        detector = HardwareDetector()
        assert detector._parse_apple_vram("1536 MB") == pytest.approx(1536 / 1024)

    def test_parse_apple_vram_gb(self):
        detector = HardwareDetector()
        assert detector._parse_apple_vram("8 GB") == pytest.approx(8.0)

    def test_parse_apple_vram_garbage_returns_zero(self):
        detector = HardwareDetector()
        assert detector._parse_apple_vram("not a size") == 0.0


# ---------------------------------------------------------------------------
# _determine_primary_accelerator
# ---------------------------------------------------------------------------
class TestDeterminePrimaryAccelerator:
    def test_no_gpus_returns_none(self):
        detector = HardwareDetector()
        assert detector._determine_primary_accelerator([]) == AcceleratorType.NONE

    def test_prefers_nvidia_over_amd(self):
        detector = HardwareDetector()
        nvidia = GPUInfo(0, "n", AcceleratorType.NVIDIA_CUDA, 8, 8)
        amd = GPUInfo(1, "a", AcceleratorType.AMD_ROCM, 8, 8)
        result = detector._determine_primary_accelerator([amd, nvidia])
        assert result == AcceleratorType.NVIDIA_CUDA

    def test_prefers_amd_over_intel_and_apple(self):
        detector = HardwareDetector()
        amd = GPUInfo(0, "a", AcceleratorType.AMD_ROCM, 8, 8)
        intel = GPUInfo(1, "i", AcceleratorType.INTEL_ONEAPI, 8, 8)
        apple = GPUInfo(2, "m", AcceleratorType.APPLE_METAL, 8, 8)
        result = detector._determine_primary_accelerator([intel, apple, amd])
        assert result == AcceleratorType.AMD_ROCM


# ---------------------------------------------------------------------------
# HardwareDetector.detect() end-to-end (real machine, structural checks only)
# ---------------------------------------------------------------------------
class TestDetectEndToEnd:
    def test_detect_hardware_returns_populated_profile(self):
        profile = detect_hardware()

        assert isinstance(profile, HardwareProfile)
        assert profile.cpu_count >= 1
        assert profile.cpu_cores_physical >= 1
        assert profile.cpu_cores_logical >= 1
        assert profile.ram_total_gb >= 0
        assert profile.ram_available_gb >= 0
        assert isinstance(profile.gpus, list)
        assert profile.primary_accelerator in AcceleratorType
        assert profile.available_for_models_gb >= 0

    def test_detector_stores_profile_for_get_profile(self):
        detector = HardwareDetector()
        assert detector.get_profile() is None
        profile = detector.detect()
        assert detector.get_profile() is profile

    def test_available_for_models_capped_by_gpu_free_memory(self):
        """
        When a usable GPU is present, available_for_models_gb should never
        exceed 80% of that GPU's free memory, regardless of how much
        system RAM is available.
        """
        detector = HardwareDetector()
        with patch.object(detector, "_detect_cpu", return_value={
                "physical_cores": 4, "logical_cores": 8,
                "frequency_ghz": 3.0, "brand": "Test",
            }), \
            patch.object(detector, "_detect_ram", return_value={
                "total": 128.0, "available": 100.0,
            }), \
            patch.object(detector, "_detect_gpus", return_value=[
                GPUInfo(0, "Small VRAM GPU", AcceleratorType.NVIDIA_CUDA,
                        total_memory_gb=4.0, free_memory_gb=2.0),
            ]), \
            patch.object(detector, "_detect_platform", return_value={
                "name": "Linux", "version": "test", "python_version": "3.12",
            }):
            profile = detector.detect()

        assert profile.available_for_models_gb == pytest.approx(2.0 * 0.8)


# ---------------------------------------------------------------------------
# ModelRecommender
# ---------------------------------------------------------------------------
class TestModelRecommender:
    @pytest.mark.parametrize(
        "available_gb,expected_size",
        [
            (1.0, ModelSize.TINY),
            (3.0, ModelSize.SMALL),
            (8.0, ModelSize.MEDIUM),
            (20.0, ModelSize.LARGE),
            (64.0, ModelSize.XLARGE),
        ],
    )
    def test_determine_model_size_boundaries(self, cpu_only_profile, available_gb, expected_size):
        cpu_only_profile.available_for_models_gb = available_gb
        recommender = ModelRecommender(cpu_only_profile)
        assert recommender._determine_model_size() == expected_size

    def test_recommend_returns_full_recommendation(self, nvidia_profile):
        recommender = ModelRecommender(nvidia_profile)
        rec = recommender.recommend()

        assert isinstance(rec, ModelRecommendation)
        assert isinstance(rec.recommended_models, list)
        assert isinstance(rec.thinking_models, list)
        assert isinstance(rec.tool_models, list)
        assert isinstance(rec.vision_models, list)
        assert rec.max_context_tokens > 0
        assert rec.quantization_level
        assert rec.batch_size >= 1
        assert nvidia_profile.primary_accelerator.value in rec.reasoning

    def test_recommend_model_convenience_function(self, cpu_only_profile):
        rec = recommend_model(cpu_only_profile)
        assert isinstance(rec, ModelRecommendation)

    def test_reasoning_includes_gpu_details_when_present(self, nvidia_profile):
        recommender = ModelRecommender(nvidia_profile)
        rec = recommender.recommend()
        assert "GPU" in rec.reasoning or nvidia_profile.gpus[0].name in rec.reasoning

    def test_reasoning_omits_gpu_section_when_cpu_only(self, cpu_only_profile):
        recommender = ModelRecommender(cpu_only_profile)
        rec = recommender.recommend()
        assert "GPUs:" not in rec.reasoning


# ---------------------------------------------------------------------------
# get_system_summary
# ---------------------------------------------------------------------------
class TestGetSystemSummary:
    def test_summary_has_hardware_and_recommendation_keys(self):
        summary = get_system_summary()
        assert "hardware" in summary
        assert "recommendation" in summary
        assert isinstance(summary["hardware"], dict)
        assert isinstance(summary["recommendation"], dict)

    @pytest.mark.xfail(
        reason="known bug: ModelRecommendation.model_size (a ModelSize "
               "enum) is never converted to its .value before being "
               "returned from get_system_summary(), the same class of bug "
               "as HardwareProfile.to_dict()'s per-GPU accelerator field. "
               "Fix in hardware.py, not here.",
        strict=True,
    )
    def test_summary_is_json_serializable(self):
        summary = get_system_summary()
        json.dumps(summary)  # must not raise