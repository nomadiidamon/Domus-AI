# Hestia: Hardware and Recommendations

The hearth of Domus-AI. Hestia detects host hardware and maps its available memory and primary accelerator to model recommendations. These functions are exported from `Hestia`; the lower-level catalog is in `Hestia.model_catalog`.

## Public API

- `detect_hardware() -> HardwareProfile` runs detection and returns CPU, RAM, GPU, platform, Python, primary-accelerator, and estimated model-memory information.
- `recommend_model(profile) -> ModelRecommendation` returns a recommendation for a detected profile.
- `HardwareDetector.detect()` is the class-based detector; `get_profile()` returns its most recent result or `None` before detection.
- `ModelRecommender(profile).recommend()` builds the recommendation from the catalog.
- `print_hardware_report(profile, recommendation=None)` prints a human-readable report. If no recommendation is passed, it reports hardware only.
- `get_system_summary() -> dict` returns a compact hardware summary.

`HardwareProfile.to_dict()` serializes GPU and accelerator enum values for JSON output. `GPUInfo` and `ModelRecommendation` are dataclasses.

## Recommendation data

`ModelRecommendation` contains the selected `model_size`, general-purpose `recommended_models`, `thinking_models`, `tool_models`, `vision_models`, `max_context_tokens`, `quantization_level`, `batch_size`, `estimated_performance`, and a `reasoning` explanation. The catalog is an advisory lookup, not a check that a model exists in Ollama or will fit with every runtime setting.

`Hestia.model_catalog.MODEL_DATABASE` groups these values by `AcceleratorType` and `ModelSize`. `get_tier(accelerator, size)` resolves a tier with a fallback, and `get_category(tier, name)` reads a catalog category.

## Types and detection coverage

`AcceleratorType` values are `NONE`, `NVIDIA_CUDA`, `NVIDIA_MPS`, `AMD_ROCM`, `INTEL_ONEAPI`, `APPLE_METAL`, and `QUALCOMM_HEXAGON`.

`ModelSize` values are `TINY`, `SMALL`, `MEDIUM`, `LARGE`, and `XLARGE`.

Detection collects CPU and RAM via `psutil` and probes supported GPU/platform interfaces where available. Some platforms cannot report free VRAM, and optional or unavailable device interfaces can result in partial GPU information; consult `HardwareProfile.gpus` and `available_for_models_gb` rather than assuming every field is a direct device measurement.

## Example

```python
from Hestia import detect_hardware, recommend_model, print_hardware_report

profile = detect_hardware()
recommendation = recommend_model(profile)
print_hardware_report(profile, recommendation)
```