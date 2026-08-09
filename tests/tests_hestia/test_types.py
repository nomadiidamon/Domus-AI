"""Tests for Hestia/types.py - AcceleratorType and ModelSize enums."""

import pytest

from Hestia.types import AcceleratorType, ModelSize

pytestmark = pytest.mark.hestia


class TestAcceleratorType:
    @pytest.mark.parametrize(
        "member,value",
        [
            (AcceleratorType.NONE, "none"),
            (AcceleratorType.NVIDIA_CUDA, "nvidia_cuda"),
            (AcceleratorType.NVIDIA_MPS, "nvidia_mps"),
            (AcceleratorType.AMD_ROCM, "amd_rocm"),
            (AcceleratorType.INTEL_ONEAPI, "intel_oneapi"),
            (AcceleratorType.APPLE_METAL, "apple_metal"),
            (AcceleratorType.QUALCOMM_HEXAGON, "qualcomm_hexagon"),
        ],
    )
    def test_values(self, member, value):
        """
        Pin the string values since they're used as MODEL_DATABASE keys
        (indirectly via the enum) and could appear in serialized JSON -
        changing them silently would be a breaking change.
        """
        assert member.value == value

    def test_members_are_unique(self):
        values = [m.value for m in AcceleratorType]
        assert len(values) == len(set(values))


class TestModelSize:
    @pytest.mark.parametrize(
        "member,value",
        [
            (ModelSize.TINY, "tiny"),
            (ModelSize.SMALL, "small"),
            (ModelSize.MEDIUM, "medium"),
            (ModelSize.LARGE, "large"),
            (ModelSize.XLARGE, "xlarge"),
        ],
    )
    def test_values(self, member, value):
        assert member.value == value

    def test_members_are_unique(self):
        values = [m.value for m in ModelSize]
        assert len(values) == len(set(values))