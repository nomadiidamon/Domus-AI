# Reads all configuration files - models.json, ollama.env, claude.json, and runtime.json.
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from utils import load_json

logger = logging.getLogger(__name__)

# Store loaded configurations
_config_cache = {
    "models": None,
    "claude": None,
    "runtime": None,
    "ollama_env": None
}

def _get_config_dir() -> Path:
    """Get the config directory path."""
    # Config should be relative to project root
    try:
        from .paths import find_root
        return find_root() / "config"
    except Exception:
        # Fallback: look for config directory relative to this file
        current = Path(__file__).parent.parent
        config_dir = current / "config"
        if config_dir.exists():
            return config_dir
        raise RuntimeError("Could not find config directory")

def load_env() -> bool:
    """
    Load environment variables from ollama.env file.
    
    Returns:
        True if successfully loaded, False otherwise
    """
    try:
        config_dir = _get_config_dir()
        env_file = config_dir / "ollama.env"
        
        if not env_file.exists():
            logger.warning(f"ollama.env not found at {env_file}")
            return False
        
        load_dotenv(str(env_file))
        logger.info(f"Loaded environment from {env_file}")
        _config_cache["ollama_env"] = True
        return True
        
    except Exception as e:
        logger.error(f"Error loading environment: {e}")
        return False

def load_models_config() -> Dict[str, Any]:
    """
    Load models configuration from models.json.
    
    Returns:
        Dictionary of model configurations
    """
    if _config_cache["models"] is not None:
        return _config_cache["models"]

    try:
        config_dir = _get_config_dir()
    except Exception as e:
        logger.error(f"Error loading models config: {e}")
        return {}

    models_file = config_dir / "models.json"
    models = load_json(models_file, default={}, logger=logger)

    if models:
        logger.info(f"Loaded {len(models)} model configurations")
        _config_cache["models"] = models

    return models

def load_claude_config() -> Dict[str, Any]:
    """
    Load Claude configuration from claude.json.
    
    Returns:
        Dictionary of Claude configurations
    """
    if _config_cache["claude"] is not None:
        return _config_cache["claude"]

    try:
        config_dir = _get_config_dir()
    except Exception as e:
        logger.error(f"Error loading Claude config: {e}")
        return {}

    claude_file = config_dir / "claude.json"
    config = load_json(claude_file, default={}, logger=logger)

    if config:
        logger.info("Loaded Claude configuration")
        _config_cache["claude"] = config

    return config

def load_runtime_config() -> Dict[str, Any]:
    """
    Load runtime configuration from runtime.json.
    
    Returns:
        Dictionary of runtime configurations
    """
    if _config_cache["runtime"] is not None:
        return _config_cache["runtime"]

    try:
        config_dir = _get_config_dir()
    except Exception as e:
        logger.error(f"Error loading runtime config: {e}")
        return {}

    runtime_file = config_dir / "runtime.json"
    config = load_json(runtime_file, default={}, logger=logger)

    if config:
        logger.info("Loaded runtime configuration")
        _config_cache["runtime"] = config

    return config

def get_model_config(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Model configuration or None if not found
    """
    models = load_models_config()
    return models.get(model_name)

def get_env(key: str, default: str = "") -> str:
    """
    Get environment variable with optional default.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)

def load_all_config() -> bool:
    """
    Load all configuration files.
    
    Returns:
        True if all critical configs loaded, False otherwise
    """
    logger.info("Loading all configuration files...")
    
    env_loaded = load_env()
    models_loaded = load_models_config()
    claude_loaded = load_claude_config()
    runtime_loaded = load_runtime_config()
    
    # Environment is loaded if file exists (it's optional)
    # Models config should exist
    if not models_loaded:
        logger.warning("No models configured")
    
    logger.info("Configuration loading complete")
    return bool(models_loaded or claude_loaded or runtime_loaded)

# Auto-load configuration when module is imported
try:
    load_all_config()
except Exception as e:
    logger.warning(f"Error during automatic config load: {e}")