# Handles all the ollama commands. Delegates to models.py for model building and pulling, and to session.py for session management.
import subprocess
import logging
from typing import Optional
import time
from claude import ollama_launch_claude

logger = logging.getLogger(__name__)

# Module-level tracking of processes
_active_processes = {
    "ollama_server": None,
    "models": {}
}

def start_ollama() -> subprocess.Popen:
    """
    Start the Ollama server.
    
    Only one Ollama server should run at a time. If one is already running,
    this function returns the existing process handle.
    
    Returns:
        Process handle for the Ollama server
        
    Raises:
        RuntimeError: If Ollama is not installed or server fails to start
    """
    # Check if already running
    if _active_processes["ollama_server"] is not None:
        logger.warning("Ollama server already running (PID: %d)", 
                      _active_processes["ollama_server"].pid)
        return _active_processes["ollama_server"]
    
    try:
        logger.info("Starting Ollama server...")
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        _active_processes["ollama_server"] = process
        logger.info(f"Ollama server started (PID: {process.pid})")
        
        # Give server time to start
        time.sleep(1)
        return process
        
    except FileNotFoundError:
        logger.error("Ollama not found in PATH...")
        raise RuntimeError(
            "Ollama is not installed or not in PATH. "
            "Please install it from https://ollama.ai and try again."
        )
    except Exception as e:
        logger.error(f"Failed to start Ollama server: {e}")
        raise

def start_model(model: str) -> subprocess.Popen:
    """
    Start running an Ollama model.
    
    This starts a model conversation session. Only one model can be active
    at a time by default (configurable in Ollama settings).
    
    Args:
        model: Name of the model to run (e.g., 'llama2', 'neural-chat')
        
    Returns:
        Process handle for the model
        
    Raises:
        ValueError: If model name is invalid
        RuntimeError: If Ollama server not running or model not found
    """
    if not model or not isinstance(model, str):
        raise ValueError(f"Model name must be a non-empty string, got: {model}")
    
    if model in _active_processes["models"]:
        logger.warning(f"Model {model} already running (PID: {_active_processes['models'][model].pid})")
        return _active_processes["models"][model]
    
    try:
        logger.info(f"Starting model: {model}")
        process = subprocess.Popen(
            ["ollama", "run", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        _active_processes["models"][model] = process
        logger.info(f"Model {model} started (PID: {process.pid})")
        return process
        
    except FileNotFoundError:
        logger.error("Ollama not found in PATH")
        raise RuntimeError("Ollama is not installed or not in PATH")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ollama failed to start model {model}: {e.stderr}")
        raise RuntimeError(f"Failed to start model '{model}'. Make sure it's installed: ollama pull {model}")
    except Exception as e:
        logger.error(f"Unexpected error starting model {model}: {e}")
        raise

def stop_ollama() -> bool:
    """
    Stop the Ollama server gracefully.
    
    Returns:
        True if server was stopped, False if no server was running
    """
    if _active_processes["ollama_server"] is None:
        logger.warning("No Ollama server process to stop")
        return False
    
    try:
        logger.info(f"Stopping Ollama server (PID: {_active_processes['ollama_server'].pid})")
        _active_processes["ollama_server"].terminate()
        
        # Wait up to 5 seconds for graceful shutdown
        try:
            _active_processes["ollama_server"].wait(timeout=5)
            logger.info("Ollama server stopped gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Ollama server did not stop gracefully, forcing shutdown")
            _active_processes["ollama_server"].kill()
            _active_processes["ollama_server"].wait()
            logger.info("Ollama server forcefully terminated")
        
        _active_processes["ollama_server"] = None
        return True
        
    except Exception as e:
        logger.error(f"Error stopping Ollama server: {e}")
        return False

def stop_model(model: str) -> bool:
    """
    Stop a running model.
    
    Args:
        model: Name of the model to stop
        
    Returns:
        True if model was stopped, False if model wasn't running
    """
    if model not in _active_processes["models"]:
        logger.warning(f"Model {model} is not running")
        return False
    
    try:
        process = _active_processes["models"][model]
        logger.info(f"Stopping model {model} (PID: {process.pid})")
        process.terminate()
        
        try:
            process.wait(timeout=5)
            logger.info(f"Model {model} stopped gracefully")
        except subprocess.TimeoutExpired:
            logger.warning(f"Model {model} did not stop gracefully, forcing shutdown")
            process.kill()
            process.wait()
            logger.info(f"Model {model} forcefully terminated")
        
        del _active_processes["models"][model]
        return True
        
    except Exception as e:
        logger.error(f"Error stopping model {model}: {e}")
        return False

def get_active_processes() -> dict:
    """
    Get information about all active processes.
    
    Returns:
        Dictionary with active server and model processes
    """
    info = {
        "ollama_server": None,
        "models": []
    }
    
    if _active_processes["ollama_server"] is not None:
        info["ollama_server"] = {
            "pid": _active_processes["ollama_server"].pid,
            "running": _active_processes["ollama_server"].poll() is None
        }
    
    for model, process in _active_processes["models"].items():
        info["models"].append({
            "name": model,
            "pid": process.pid,
            "running": process.poll() is None
        })
    
    return info

def launch_claude(model):
    ollama_launch_claude(model)