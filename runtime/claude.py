# Handles the Claude Code integration.
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def ollama_launch_claude(model: str, auto_yes: bool = False) -> Optional[subprocess.Popen]:
    """
    Launch Claude Code with a specified Ollama model.
    
    Uses the Ollama integration: `ollama launch claude --model <model>`
    See: https://docs.ollama.com/integrations/claude-code
    
    Args:
        model: Name of the Ollama model to use (e.g., 'qwen3.5', 'gemma4:cloud')
        auto_yes: If True, skip selectors and prompts (useful for CI/automation)
        
    Returns:
        Process handle if launched, None if command fails
        
    Raises:
        ValueError: If model name is invalid
        RuntimeError: If Ollama launch command fails
    """
    if not model or not isinstance(model, str):
        raise ValueError(f"Model must be a non-empty string, got: {model}")
    
    try:
        logger.info(f"Launching Claude Code with model: {model}")
        
        # Build command: ollama launch claude --model <model> [--yes]
        command = ["ollama", "launch", "claude", "--model", model]
        
        if auto_yes:
            command.append("--yes")
            logger.debug("Auto-yes mode enabled (will skip prompts)")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.debug(f"Claude Code process started with PID: {process.pid}")
        logger.info(f"Claude Code is launching - you can interact with it now")
        return process
        
    except FileNotFoundError:
        logger.error("Ollama not found in PATH. Please install Ollama: https://ollama.ai")
        raise RuntimeError(
            "Ollama is not installed or not in PATH. "
            "Please install it from https://ollama.ai and try again."
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Ollama launch claude failed: {e.stderr}")
        raise RuntimeError(f"Failed to launch Claude Code: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error launching Claude Code: {e}")
        raise