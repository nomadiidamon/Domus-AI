"""
Janus - Configuration, paths, dependency checking, diagnostics, and
install/lifecycle management for Domus-AI.

Provides:
- paths: repo root / host project root resolution, working directories
- config: loading config/*.json and .env
- dependencies: declarative dependency checking (Python packages, system
  commands, directories, env vars)
- doctor: full diagnostic checks (dependencies, models, MCP, ollama server)
- installer: first-run install / auto-repair flow
"""

from .paths import find_root, get_host_project_root, get_ai_runtime_dir
from .config import load_models_config, load_runtime_config, load_claude_config
from .dependencies import DependencyChecker
from .doctor import full_diagnostic
from .installer import run_install

__all__ = [
    "find_root",
    "get_host_project_root",
    "get_ai_runtime_dir",
    "load_models_config",
    "load_runtime_config",
    "load_claude_config",
    "DependencyChecker",
    "full_diagnostic",
    "run_install",
]