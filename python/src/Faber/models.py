"""
 Handles all model pulling and building commands

 @todo: Define and implement model tag support and naming rules for custom models.
"""

import json
from utils import get_log_category
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from Faber.session import get_session, create_session, stop_session

logger = get_log_category(__name__)

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


def _modelfile_create_fields(content):
    fields = {}
    parameters = {}
    lines = iter(content.splitlines(keepends=True))
    integer_parameters = {"num_ctx", "num_predict", "num_keep", "seed", "top_k", "repeat_last_n"}
    float_parameters = {"temperature", "top_p", "min_p", "repeat_penalty", "presence_penalty", "frequency_penalty"}

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise RuntimeError(f"Invalid Modelfile directive: {line}")
        directive, value = parts[0].upper(), parts[1].strip()
        if directive == "FROM":
            if "from" in fields:
                raise RuntimeError("Multiple FROM directives are not supported")
            if value.startswith((".", "/", "~")) or "\\" in value or value.lower().endswith((".gguf", ".safetensors")):
                raise RuntimeError("Local model files are not supported by the build API")
            fields["from"] = value
        elif directive == "SYSTEM":
            if "system" in fields:
                raise RuntimeError("Multiple SYSTEM directives are not supported")
            if value.startswith('"""'):
                value = value[3:]
                while '"""' not in value:
                    try:
                        value += next(lines)
                    except StopIteration:
                        raise RuntimeError("Unterminated SYSTEM directive") from None
                value, trailing = value.split('"""', 1)
                if trailing.strip():
                    raise RuntimeError("Unexpected text after SYSTEM directive")
                value = value.strip("\r\n")
            elif value.startswith('"'):
                try:
                    values = shlex.split(value)
                except ValueError as error:
                    raise RuntimeError(f"Invalid SYSTEM directive: {error}") from error
                if len(values) != 1:
                    raise RuntimeError("Invalid SYSTEM directive")
                value = values[0]
            fields["system"] = value
        elif directive == "PARAMETER":
            try:
                values = shlex.split(value)
            except ValueError as error:
                raise RuntimeError(f"Invalid PARAMETER directive: {error}") from error
            if len(values) != 2:
                raise RuntimeError(f"Invalid PARAMETER directive: {value}")
            name, parameter_value = values
            try:
                if name in integer_parameters:
                    parameters[name] = int(parameter_value)
                elif name in float_parameters:
                    parameters[name] = float(parameter_value)
                elif name == "stop":
                    parameters.setdefault(name, []).append(parameter_value)
                else:
                    raise RuntimeError(f"Unsupported Modelfile parameter: {name}")
            except ValueError as error:
                raise RuntimeError(f"Invalid value for Modelfile parameter {name}: {parameter_value}") from error
        else:
            raise RuntimeError(f"Unsupported Modelfile directive: {directive}")

    if not fields.get("from"):
        raise RuntimeError("Modelfile must specify a FROM directive")
    if parameters:
        fields["parameters"] = parameters
    return fields


def _stream_ollama(endpoint, payload, action, progress=None, timeout=3600, modelfile_content=None):
    """Stream Ollama progress events and report them to an optional callback."""
    from Hestia.software.installer import (
        InstallActionStatus, InstallProgress, InstallProgressTracker,
    )

    if progress is None:
        progress = InstallProgressTracker()

    if modelfile_content is not None:
        payload = {**payload, **_modelfile_create_fields(modelfile_content)}

    action_id = f"ollama-{action}"
    request = urllib.request.Request(
        f"http://localhost:11434/api/{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    def report(message, completed=None, status=None):
        if progress is not None:
            progress(InstallProgress(action_id, action, message, completed, status))

    report(f"Starting {action}", 0.0)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for line in response:
                if not line.strip():
                    continue
                event = json.loads(line.decode("utf-8"))
                if event.get("error"):
                    raise RuntimeError(event["error"])

                completed = event.get("completed")
                total = event.get("total")
                fraction = completed / total if total and completed is not None else None
                report(event.get("status", f"{action} in progress"), fraction)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        message = detail or str(error)
        report(message, status=InstallActionStatus.FAILED)
        raise RuntimeError(message) from error
    except urllib.error.URLError as error:
        message = f"Ollama server unreachable at localhost:11434 ({error})"
        report(message, status=InstallActionStatus.FAILED)
        raise RuntimeError(message) from error
    except TimeoutError as error:
        message = f"'ollama {action}' timed out after {timeout}s"
        report(message, status=InstallActionStatus.FAILED)
        raise RuntimeError(message) from error
    except Exception as error:
        report(str(error), status=InstallActionStatus.FAILED)
        raise

    report(f"{action} finished", 1.0, InstallActionStatus.SUCCEEDED)


def pull_model(model, progress=None):
    _stream_ollama("pull", {"name": model, "stream": True}, f"pull {model}", progress)
    logger.info(f"Pulled model '{model}'")


def build_model(model, progress=None):
    modelfile = _resolve_modelfile(model)
    _stream_ollama(
        "create", {"model": model, "stream": True}, f"build {model}", progress,
        modelfile_content=modelfile.read_text(encoding="utf-8"),
    )
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