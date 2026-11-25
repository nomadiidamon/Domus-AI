# Shared helpers for the project
# Logging, JSON loading, formatting outputs, etc.

"""
utils.py - Shared helpers available to every Domus-AI subsystem equally.

Lives at the project root (a sibling of Janus, Mentis, Faber,
Custos, Lares, DomusAPI) rather than inside any one subsystem,
since logging configuration and JSON loading are used across all of them
and none of them is the "owner" of these concerns.

@todo: Incorporate the PrintColor handling from Janus for consistent output formatting across subsystems.
@todo: Create an error struct with a error symbol and message for consistent error reporting across subsystems.
@todo: Create a success struct with a success symbol and message for consistent success reporting across subsystems.
@todo: Create a generic error handling mechanism for all subsystems.
@todo: Create a function to read a configuration file for a specific value or key.
@todo: Create a function to write a configuration value to a file.
@todo: Create a function to parse a string for specific patterns or values.
@todo: Create a function that can convert a fenced block of text into a different format (e.g., a JSON object to a Python dictionary).
"""

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Optional

from Auctor.Livy import Category, Livy
from platformdirs import user_log_path

livy = Livy("Domus")
_logging_lock = RLock()


def get_log_category(name: str) -> Category:
    """Return the shared Livy category for a Domus subsystem."""
    configure_logging()
    return livy.create_category(name.split(".", 1)[0])


def configure_logging(path: Optional[Path] = None) -> None:
    """Initialize Livy, switching to the host log when a path is supplied."""
    with _logging_lock:
        if path is None and livy.is_initialized():
            return
        if path is None:
            path = Path(os.environ.get("DOMUS_LOG_PATH") or user_log_path("domus-ai", appauthor=False) / "domus.log")
        path = Path(path)
        previous_path = livy.log_file if livy.is_initialized() else None
        target = path / "livy.log" if path.is_dir() or not path.suffix else path
        if previous_path is not None:
            if previous_path == target:
                return
            livy.shutdown()
        if not livy.initialize(path):
            failure = livy.get_last_failure()
            if previous_path is not None:
                livy.initialize(previous_path)
            raise RuntimeError(failure.message if failure else "Could not initialize Domus logging")


def load_json(path: Path, default: Any = None, logger: Optional[Category] = None) -> Any:
    """
    Load and parse a JSON file, with consistent handling for the common
    "config file that may not exist yet or may be malformed" case.

    Args:
        path: Path to the JSON file.
        default: Value to return if the file is missing, empty, or
                 invalid. Defaults to None if not provided - pass {} or
                 [] explicitly if that's what the caller expects back.
        logger: Optional logger to report warnings/errors to. If omitted,
                nothing is logged (callers that want their own log
                messages should keep doing that logging themselves;
                this parameter is for callers happy with generic ones).

    Returns:
        The parsed JSON value, or `default` if the file doesn't exist or
        can't be parsed.
    """
    path = Path(path)

    if not path.exists():
        if logger:
            logger.warning(f"{path.name} not found at {path}")
        return default

    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        if logger:
            logger.error(f"Error parsing {path.name}: {e}")
        return default
    except Exception as e:
        if logger:
            logger.error(f"Error loading {path.name}: {e}")
        return default