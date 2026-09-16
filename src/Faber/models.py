# Handles all model pulling and building commands
import subprocess
import logging
from pathlib import Path
from Faber.session import get_session, create_session, stop_session

logger = logging.getLogger(__name__)

_context = None

def set_context(context):
    """Bind a RuntimeContext instance so model events are tracked."""
    global _context
    _context = context

def _get_context():
    """Return the currently bound RuntimeContext, or None."""
    return _context

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

def _run_ollama(args, action, timeout=60):
    """Run an ollama command, raising RuntimeError with stderr on failure."""
    try:
        result = subprocess.run(
            ["ollama"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError("Ollama executable not found - ensure it is installed and on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"'ollama {action}' timed out after {timeout}s")

    if result.returncode != 0:
        raise RuntimeError(f"'ollama {action}' failed: {result.stderr.strip()}")

    return result


def _resolve_modelfile(model):
    """Find the Modelfile path for a model from models.json or the Modelfiles dir."""
    from Janus.config import get_model_config
    from Janus.paths import get_modelfiles_path

    # models.json keys are title-cased ("Mercury") but the CLI passes lowercase
    config = get_model_config(model)
    if config is None:
        from Janus.config import load_models_config
        for name, cfg in load_models_config().items():
            if name.lower() == model.lower():
                config = cfg
                break

    if config is not None:
        modelfile = Path(config.get("modelfile", ""))
        if modelfile.is_file():
            return modelfile

    # Portable fallback: Modelfiles/<Name>/Modelfile.<Name> in the repo
    name = model[:1].upper() + model[1:]
    fallback = get_modelfiles_path() / name / f"Modelfile.{name}"
    if fallback.is_file():
        return fallback

    raise RuntimeError(f"No Modelfile found for model '{model}'")


def pull_model(model):
    _run_ollama(["pull", model], f"pull {model}", timeout=3600)
    logger.info(f"Pulled model '{model}'")


def build_model(model):
    modelfile = _resolve_modelfile(model)
    _run_ollama(["create", model, "-f", str(modelfile)], f"create {model}", timeout=3600)
    logger.info(f"Built model '{model}' from {modelfile}")


def list_models():
    result = _run_ollama(["list"], "list", timeout=10)

    models = []
    lines = result.stdout.strip().splitlines()
    for line in lines[1:]:  # skip the NAME/ID/SIZE/MODIFIED header row
        fields = line.split()
        if not fields:
            continue
        models.append({
            "name": fields[0],
            "id": fields[1] if len(fields) > 1 else "",
            "size": " ".join(fields[2:4]) if len(fields) > 2 else "",
            "modified": " ".join(fields[4:]) if len(fields) > 4 else "",
        })
    return models


def remove_model(model):
    _run_ollama(["rm", model], f"rm {model}", timeout=60)

    # Terminate + drop any tracked session so status stays accurate
    if get_session(model) is not None:
        stop_session(model)

    logger.info(f"Removed model '{model}'")