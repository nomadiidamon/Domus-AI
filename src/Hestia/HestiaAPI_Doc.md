# Hestia-API: General Runtime

The hearth of Domus-AI: hardware and system detection plus model recommendation - the fine-grained capability API that DomusAPI wraps.

## Hardware detection (`Hestia.hardware`)
- `detect_hardware() -> HardwareProfile` - CPU, RAM, GPUs (via psutil / nvidia-ml-py), platform info, primary accelerator, memory available for models
- `HardwareDetector` - class form; `detect()` runs full detection, `get_profile()` returns the last result
- `HardwareProfile` (`.to_dict()`), `GPUInfo` dataclasses
- `print_hardware_report(profile, recommendation=None)` - human-readable report (used by `janus status`)

## Model recommendation
- `ModelRecommender(profile).recommend() -> ModelRecommendation` - picks a model size tier, recommended models per category (thinking/coding/tool-use/vision), quantization, batch size, and performance estimate
- `recommend_model(profile)` - function convenience wrapper
- `get_system_summary() -> dict`

## Catalog and types
- `Hestia.model_catalog`: `MODEL_DATABASE` (per-accelerator, per-size model lists by category), `get_tier(accelerator, size)` with tier fallback, `get_category(tier, name)`
- `Hestia.types`: `AcceleratorType` (NONE, NVIDIA_CUDA, APPLE_METAL, etc.), `ModelSize` (TINY/SMALL/MEDIUM/LARGE/XLARGE)