"""
Hestia - Hardware detection and model recommendation subsystem.

Provides:
- Hardware profiling (CPU, GPU, memory, accelerator detection)
- Model size/tier recommendations based on detected hardware
"""

from .hardware import (
    HardwareProfile,
    HardwareDetector,
    ModelRecommender,
    ModelRecommendation,
    AcceleratorType,
    ModelSize,
    detect_hardware,
    recommend_model,
    print_hardware_report,
)

__all__ = [
    "HardwareProfile",
    "HardwareDetector",
    "ModelRecommender",
    "ModelRecommendation",
    "AcceleratorType",
    "ModelSize",
    "detect_hardware",
    "recommend_model",
    "print_hardware_report",
]