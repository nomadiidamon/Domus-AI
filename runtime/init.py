# Makes runtime a package
"""
Local AI Runtime - Unified interface for Ollama and Claude Code integration.

This package provides CLI tools and APIs for managing local AI models
with Ollama and integrating them with Claude Code.
"""

__version__ = "0.1.0"
__author__ = "Local AI Runtime Contributors"

# Import main components for easy access
try:
    from .main import main
    from .ollama import start_ollama, start_model, stop_ollama, stop_model, get_active_processes
    from .config import load_all_config, get_model_config, get_env
    from .doctor import full_diagnostic
    
    __all__ = [
        'main',
        'start_ollama',
        'start_model',
        'stop_ollama',
        'stop_model',
        'get_active_processes',
        'load_all_config',
        'get_model_config',
        'get_env',
        'full_diagnostic',
    ]
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import all components: {e}")