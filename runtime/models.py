# Handles all model pulling and building commands
import subprocess
import logging
from session import get_session, create_session, stop_session

logger = logging.getLogger(__name__)

_context = None

def set_context(context):
    """Bind a RuntimeContext instance so model events are tracked."""
    global _context
    _context = context

def start_model(model):

    existing = get_session(model)

    if existing:
        return existing


    process = subprocess.Popen(
        [
            "ollama",
            "run",
            model
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


    session = create_session(
        name=model,
        process=process,
        session_type="model",
        metadata={
            "model": model
        }
    )

    if _context is not None:
        _context.load_model(model, metadata={"model": model, "pid": process.pid})

    logger.info(f"Started model '{model}' with PID '{process.pid}'")

    return process

def stop_model(model):

    result = stop_session(model)

    if result and _context is not None:
        _context.unload_model(model)

def pull_model(model):
    pass

def build_model(model):
    pass

def list_models():
    pass

def remove_model(model):
    pass