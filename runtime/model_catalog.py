# ---------------------------------------------------------------------------
# To add new categories
# ---------------------------------------------------------------------------
# 1.) Add the new category key to KNOWN_CATEGORIES
    # KNOWN_CATEGORIES = [ '...' , '...' , 'coding']

# 2.) Add the new category key to each tier entry that supports it in MODEL_DATABASE
    # 'coding': ['qwen2.5-coder:7b']

# 3.) Add the field to the ModelRecommendation dataclass in hardware.py
    # coding_models: List[str]

# 4.) Add to ModelRecommender.recommend() in hardware.py
    # coding_models=get_category(tier, 'coding_models'),

# 5.) Add to print_hardware_report() in hardware.py
    # if recommendation.coding_models:
        #print(f"Coding:       {', '.join(recommendation.coding_models)}")


"""
model_catalog.py - Model recommendation database for Local AI Runtime.

Defines what models are appropriate per hardware tier, accelerator type,
and capability category. Add new categories here without touching hardware.py.

Category keys per tier entry:
  models   — best general-purpose models for balanced use
  thinking — chain-of-thought / extended reasoning (/think mode)
  tools    — native function/tool-call support
  vision   — multimodal image + text understanding
  quantization — recommended quantization level for this tier
  batch_size   — safe concurrent request count
  context      — practical max context window in tokens
  performance  — human-readable speed description
"""

from typing import Dict, List
from runtime.hardware import AcceleratorType, ModelSize, ModelRecommendation


# ---------------------------------------------------------------------------
# Type alias for a single tier entry
# ---------------------------------------------------------------------------
TierEntry = Dict[str, object]
TierMap   = Dict[ModelSize, TierEntry]


# ---------------------------------------------------------------------------
# MODEL DATABASE
# Outer key: AcceleratorType
# Inner key: ModelSize (memory tier)
# ---------------------------------------------------------------------------

MODEL_DATABASE: Dict[AcceleratorType, TierMap] = {

    # ==========================================================================
    # NVIDIA CUDA
    # Fast VRAM access — highest quality quant per tier
    # ==========================================================================
    AcceleratorType.NVIDIA_CUDA: {

        ModelSize.TINY: {
            # <2 GB — ultra-constrained, phone/edge-class VRAM
            'models':      ['qwen3:0.6b', 'llama3.2:1b', 'deepseek-r1:1.5b', 'smollm2:1.7b'],
            'thinking':    ['deepseek-r1:1.5b', 'qwen3:0.6b'],
            'tools':       ['qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'],
            'vision':      [],  # No reliable sub-2 GB vision models on Ollama
            'quantization': 'q8_0',
            'batch_size':   4,
            'context':      8192,
            'performance':  'Fast (tiny model)',
        },

        ModelSize.SMALL: {
            # 2–4 GB — entry-level discrete GPU or shared VRAM laptop
            'models':      ['qwen3:1.7b', 'llama3.2:3b', 'phi4-mini:3.8b', 'granite3.3:2b'],
            'thinking':    ['qwen3:1.7b', 'deepseek-r1:1.5b'],
            'tools':       ['qwen3:1.7b', 'llama3.2:3b', 'granite3.1-dense:2b', 'xlam:1b'],
            'vision':      ['llama3.2-vision:3b', 'moondream:1.8b', 'minicpm-v:3b'],
            'quantization': 'q6_k',
            'batch_size':   4,
            'context':      16384,
            'performance':  'Fast',
        },

        ModelSize.MEDIUM: {
            # 4–12 GB — GTX 1080 / RTX 3060 / RX 6700 XT class
            'models':      ['qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'mistral-nemo:12b', 'qwen2.5:7b'],
            'thinking':    ['qwen3:8b', 'deepseek-r1:8b', 'cogito:8b', 'exaone-deep:7.8b'],
            'tools':       ['qwen3:8b', 'llama3.1:8b', 'qwen2.5:7b', 'hermes3:8b',
                            'mistral:7b', 'xlam:8b', 'functionary:7b', 'granite3.1-dense:8b'],
            'vision':      ['llava:7b', 'llava:13b', 'llama3.2-vision:11b', 'qwen2.5vl:7b',
                            'minicpm-v:8b', 'moondream:1.8b', 'bakllava:7b'],
            'quantization': 'q4_k_m',
            'batch_size':   2,
            'context':      32768,
            'performance':  'Fast',
        },

        ModelSize.LARGE: {
            # 12–40 GB — RTX 3090 / RTX 4090 / A100 40 GB class
            'models':      ['qwen3:14b', 'qwen3:32b', 'qwen2.5:32b',
                            'deepseek-r1:14b', 'command-r:35b'],
            'thinking':    ['qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'deepseek-r1:32b',
                            'qwq:32b', 'cogito:14b', 'cogito:32b',
                            'phi4-reasoning:14b', 'exaone-deep:32b'],
            'tools':       ['qwen3:14b', 'qwen3:32b', 'command-r:35b', 'qwen2.5:32b',
                            'hermes3:8b', 'aya-expanse:32b', 'functionary:7b', 'xlam:7b'],
            'vision':      ['llava:34b', 'qwen2.5vl:14b', 'qwen2.5vl:32b',
                            'llama3.2-vision:11b', 'minicpm-v:8b', 'gemma3:27b',
                            'mistral-small3.1:22b'],
            'quantization': 'q4_k_m',
            'batch_size':   2,
            'context':      32768,
            'performance':  'Moderate',
        },

        ModelSize.XLARGE: {
            # 40+ GB — A100 80 GB / H100 / multi-GPU NVLink
            'models':      ['llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b',
                            'deepseek-r1:70b', 'command-r-plus:104b'],
            'thinking':    ['deepseek-r1:70b', 'qwen3:30b-a3b', 'cogito:70b',
                            'qwq:32b', 'exaone-deep:32b'],
            'tools':       ['llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b',
                            'hermes3:70b', 'command-r-plus:104b',
                            'firefunction-v2:70b', 'functionary:70b'],
            'vision':      ['llava:34b', 'qwen2.5vl:72b', 'llama3.2-vision:90b',
                            'mistral-small3.1:22b', 'gemma3:27b'],
            'quantization': 'q4_k_m',
            'batch_size':   4,
            'context':      131072,
            'performance':  'Fast (large model)',
        },
    },

    # ==========================================================================
    # AMD ROCm
    # Slightly less efficient memory bandwidth than CUDA; drop quant one step
    # ==========================================================================
    AcceleratorType.AMD_ROCM: {

        ModelSize.TINY: {
            'models':      ['qwen3:0.6b', 'llama3.2:1b', 'deepseek-r1:1.5b'],
            'thinking':    ['deepseek-r1:1.5b', 'qwen3:0.6b'],
            'tools':       ['qwen3:0.6b', 'llama3.2:1b'],
            'vision':      [],
            'quantization': 'q8_0',
            'batch_size':   2,
            'context':      8192,
            'performance':  'Moderate (tiny model)',
        },

        ModelSize.SMALL: {
            'models':      ['qwen3:1.7b', 'llama3.2:3b', 'phi4-mini:3.8b'],
            'thinking':    ['qwen3:1.7b', 'deepseek-r1:1.5b'],
            'tools':       ['qwen3:1.7b', 'llama3.2:3b', 'xlam:1b'],
            'vision':      ['llama3.2-vision:3b', 'moondream:1.8b', 'minicpm-v:3b'],
            'quantization': 'q5_k_m',
            'batch_size':   2,
            'context':      16384,
            'performance':  'Moderate',
        },

        ModelSize.MEDIUM: {
            'models':      ['qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'qwen2.5:7b'],
            'thinking':    ['qwen3:8b', 'deepseek-r1:8b', 'cogito:8b'],
            'tools':       ['qwen3:8b', 'llama3.1:8b', 'qwen2.5:7b',
                            'hermes3:8b', 'mistral:7b', 'granite3.1-dense:8b'],
            'vision':      ['llava:7b', 'llama3.2-vision:11b', 'qwen2.5vl:7b',
                            'minicpm-v:8b', 'moondream:1.8b'],
            'quantization': 'q4_k_m',
            'batch_size':   2,
            'context':      32768,
            'performance':  'Moderate',
        },

        ModelSize.LARGE: {
            'models':      ['qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'command-r:35b'],
            'thinking':    ['qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'deepseek-r1:32b',
                            'qwq:32b', 'cogito:14b', 'phi4-reasoning:14b'],
            'tools':       ['qwen3:14b', 'qwen3:32b', 'command-r:35b',
                            'qwen2.5:32b', 'aya-expanse:32b'],
            'vision':      ['qwen2.5vl:14b', 'qwen2.5vl:32b', 'llava:34b',
                            'gemma3:27b', 'mistral-small3.1:22b'],
            'quantization': 'q3_k_m',
            'batch_size':   1,
            'context':      32768,
            'performance':  'Slow',
        },

        ModelSize.XLARGE: {
            'models':      ['llama3.3:70b', 'qwen2.5:72b', 'deepseek-r1:70b'],
            'thinking':    ['deepseek-r1:70b', 'qwen3:30b-a3b', 'cogito:70b'],
            'tools':       ['llama3.3:70b', 'qwen2.5:72b', 'hermes3:70b',
                            'firefunction-v2:70b'],
            'vision':      ['qwen2.5vl:72b', 'llama3.2-vision:90b', 'llava:34b'],
            'quantization': 'q3_k_m',
            'batch_size':   2,
            'context':      65536,
            'performance':  'Moderate (large model)',
        },
    },

    # ==========================================================================
    # Intel Arc / Xe (OneAPI)
    # Typically 8–16 GB on Arc A770/B580; lower throughput than NVIDIA/AMD
    # ==========================================================================
    AcceleratorType.INTEL_ONEAPI: {

        ModelSize.TINY: {
            'models':      ['qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'],
            'thinking':    ['deepseek-r1:1.5b', 'qwen3:0.6b'],
            'tools':       ['qwen3:0.6b', 'llama3.2:1b'],
            'vision':      [],
            'quantization': 'q8_0',
            'batch_size':   2,
            'context':      8192,
            'performance':  'Moderate (tiny model)',
        },

        ModelSize.SMALL: {
            'models':      ['qwen3:1.7b', 'llama3.2:3b', 'granite3.3:2b'],
            'thinking':    ['qwen3:1.7b', 'deepseek-r1:1.5b'],
            'tools':       ['qwen3:1.7b', 'llama3.2:3b', 'granite3.1-dense:2b'],
            'vision':      ['moondream:1.8b', 'minicpm-v:3b'],
            'quantization': 'q5_k_m',
            'batch_size':   2,
            'context':      8192,
            'performance':  'Moderate',
        },

        ModelSize.MEDIUM: {
            'models':      ['qwen3:8b', 'llama3.1:8b', 'mistral:7b'],
            'thinking':    ['qwen3:8b', 'deepseek-r1:8b'],
            'tools':       ['qwen3:8b', 'llama3.1:8b', 'mistral:7b',
                            'granite3.1-dense:8b', 'hermes3:8b'],
            'vision':      ['llava:7b', 'qwen2.5vl:7b', 'minicpm-v:8b', 'moondream:1.8b'],
            'quantization': 'q4_k_m',
            'batch_size':   1,
            'context':      16384,
            'performance':  'Slow',
        },

        ModelSize.LARGE: {
            'models':      ['qwen3:14b', 'qwen2.5:14b', 'phi4-reasoning:14b'],
            'thinking':    ['qwen3:14b', 'deepseek-r1:14b', 'phi4-reasoning:14b', 'cogito:14b'],
            'tools':       ['qwen3:14b', 'qwen2.5:14b', 'hermes3:8b'],
            'vision':      ['qwen2.5vl:14b', 'gemma3:12b', 'mistral-small3.1:22b'],
            'quantization': 'q3_k_m',
            'batch_size':   1,
            'context':      16384,
            'performance':  'Slow',
        },

        # XLARGE unrealistic for Arc — fallback to LARGE handled in ModelRecommender
    },

    # ==========================================================================
    # Apple Metal (Apple Silicon — unified memory)
    # M1/M2/M3/M4 share RAM with GPU; 16–192 GB depending on config
    # Metal is highly optimised for Ollama via llama.cpp
    # ==========================================================================
    AcceleratorType.APPLE_METAL: {

        ModelSize.TINY: {
            'models':      ['qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'],
            'thinking':    ['deepseek-r1:1.5b', 'qwen3:0.6b'],
            'tools':       ['qwen3:0.6b', 'llama3.2:1b'],
            'vision':      [],
            'quantization': 'q8_0',
            'batch_size':   4,
            'context':      8192,
            'performance':  'Fast (tiny model)',
        },

        ModelSize.SMALL: {
            'models':      ['qwen3:1.7b', 'llama3.2:3b', 'phi4-mini:3.8b'],
            'thinking':    ['qwen3:1.7b', 'deepseek-r1:1.5b'],
            'tools':       ['qwen3:1.7b', 'llama3.2:3b', 'granite3.1-dense:2b'],
            'vision':      ['llama3.2-vision:3b', 'moondream:1.8b', 'minicpm-v:3b'],
            'quantization': 'q6_k',
            'batch_size':   4,
            'context':      16384,
            'performance':  'Fast',
        },

        ModelSize.MEDIUM: {
            'models':      ['qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'mistral-nemo:12b'],
            'thinking':    ['qwen3:8b', 'deepseek-r1:8b', 'cogito:8b', 'exaone-deep:7.8b'],
            'tools':       ['qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'qwen2.5:7b',
                            'hermes3:8b', 'granite3.1-dense:8b'],
            'vision':      ['llava:7b', 'llama3.2-vision:11b', 'qwen2.5vl:7b',
                            'minicpm-v:8b', 'gemma3:12b', 'moondream:1.8b'],
            'quantization': 'q4_k_m',
            'batch_size':   2,
            'context':      32768,
            'performance':  'Fast',
        },

        ModelSize.LARGE: {
            # M2 Max / M3 Pro 36–48 GB unified memory
            'models':      ['qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'command-r:35b'],
            'thinking':    ['qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'deepseek-r1:32b',
                            'qwq:32b', 'cogito:14b', 'phi4-reasoning:14b', 'exaone-deep:32b'],
            'tools':       ['qwen3:14b', 'qwen3:32b', 'command-r:35b', 'qwen2.5:32b',
                            'aya-expanse:32b', 'hermes3:8b'],
            'vision':      ['llava:34b', 'qwen2.5vl:14b', 'qwen2.5vl:32b',
                            'llama3.2-vision:11b', 'gemma3:27b', 'mistral-small3.1:22b'],
            'quantization': 'q4_k_m',
            'batch_size':   2,
            'context':      65536,
            'performance':  'Fast (Apple Silicon advantage)',
        },

        ModelSize.XLARGE: {
            # M2 Ultra / M3 Max / M4 Max 64–192 GB unified memory
            'models':      ['llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b', 'deepseek-r1:70b'],
            'thinking':    ['deepseek-r1:70b', 'qwen3:30b-a3b', 'cogito:70b',
                            'qwq:32b', 'exaone-deep:32b'],
            'tools':       ['llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b',
                            'hermes3:70b', 'command-r-plus:104b', 'firefunction-v2:70b'],
            'vision':      ['llava:34b', 'qwen2.5vl:72b', 'llama3.2-vision:90b',
                            'gemma3:27b', 'mistral-small3.1:22b'],
            'quantization': 'q4_k_m',
            'batch_size':   4,
            'context':      131072,
            'performance':  'Fast (Apple Silicon advantage)',
        },
    },

    # ==========================================================================
    # CPU only — no GPU
    # ==========================================================================
    AcceleratorType.NONE: {

        ModelSize.TINY: {
            'models':      ['qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'],
            'thinking':    ['deepseek-r1:1.5b', 'qwen3:0.6b'],
            'tools':       ['qwen3:0.6b', 'llama3.2:1b'],
            'vision':      ['moondream:1.8b'],
            'quantization': 'q8_0',
            'batch_size':   1,
            'context':      4096,
            'performance':  'Slow (CPU only)',
        },

        ModelSize.SMALL: {
            'models':      ['qwen3:1.7b', 'llama3.2:3b'],
            'thinking':    ['qwen3:1.7b', 'deepseek-r1:1.5b'],
            'tools':       ['qwen3:1.7b', 'llama3.2:3b'],
            'vision':      ['moondream:1.8b', 'minicpm-v:3b'],
            'quantization': 'q4_k_m',
            'batch_size':   1,
            'context':      8192,
            'performance':  'Very Slow (CPU only)',
        },

        ModelSize.MEDIUM: {
            'models':      ['qwen3:8b', 'mistral:7b', 'llama3.1:8b'],
            'thinking':    ['qwen3:8b', 'deepseek-r1:8b'],
            'tools':       ['qwen3:8b', 'mistral:7b', 'llama3.1:8b'],
            'vision':      ['llava:7b', 'qwen2.5vl:7b', 'minicpm-v:8b'],
            'quantization': 'q4_k_m',
            'batch_size':   1,
            'context':      8192,
            'performance':  'Very Slow (CPU only)',
        },

        # LARGE / XLARGE on CPU-only is impractical — fallback handled in ModelRecommender
    },
}


# ---------------------------------------------------------------------------
# Helpers — consumed by ModelRecommender in hardware.py
# ---------------------------------------------------------------------------

# All categories present in any tier entry. Add new ones here as they are added
# to the database so get_category() degrades gracefully for old entries.
KNOWN_CATEGORIES: List[str] = ['models', 'thinking', 'tools', 'vision']

# Tier fallback order when the exact tier has no entry for an accelerator
TIER_FALLBACK_ORDER: List[ModelSize] = [
    ModelSize.LARGE,
    ModelSize.MEDIUM,
    ModelSize.SMALL,
    ModelSize.TINY,
]


def get_tier(accelerator: AcceleratorType, size: ModelSize) -> TierEntry:
    """
    Return the tier entry for an accelerator + memory size combination.

    Walks down TIER_FALLBACK_ORDER if the exact size is missing, then
    falls back to CPU MEDIUM as a last resort.

    Args:
        accelerator: The detected primary accelerator.
        size:        The memory-based model size tier.

    Returns:
        TierEntry dict ready for ModelRecommendation construction.
    """
    db = MODEL_DATABASE.get(accelerator, {})
    entry = db.get(size)

    if entry is None:
        for fallback in TIER_FALLBACK_ORDER:
            entry = db.get(fallback)
            if entry is not None:
                break

    if entry is None:
        entry = MODEL_DATABASE[AcceleratorType.NONE][ModelSize.MEDIUM]

    return entry


def get_category(tier: TierEntry, category: str) -> List[str]:
    """
    Safely retrieve a model list for a given category from a tier entry.

    Returns an empty list if the category is not present, so callers never
    need to guard against missing keys when new categories are added.

    Args:
        tier:     A tier entry dict from MODEL_DATABASE.
        category: Category name, e.g. 'vision', 'tools', 'thinking'.

    Returns:
        List of model name strings.
    """
    return tier.get(category, [])