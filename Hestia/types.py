from dataclasses import dataclass
from enum import Enum
from typing import List


class AcceleratorType(Enum):
    NONE = "none"
    NVIDIA_CUDA = "nvidia_cuda"
    NVIDIA_MPS = "nvidia_mps"
    AMD_ROCM = "amd_rocm"
    INTEL_ONEAPI = "intel_oneapi"
    APPLE_METAL = "apple_metal"
    QUALCOMM_HEXAGON = "qualcomm_hexagon"


class ModelSize(Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"