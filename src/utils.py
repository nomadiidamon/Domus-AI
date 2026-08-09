# Shared helpers for the project
# Logging, JSON loading, formatting outputs, etc.

"""
utils.py - Shared helpers available to every Domus-AI subsystem equally.

Lives at the project root (a sibling of Hestia, Janus, Mentis, Faber,
Custos, Mercurius, Lares, DomusAPI) rather than inside any one subsystem,
since logging configuration and JSON loading are used across all of them
and none of them is the "owner" of these concerns.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional


DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_logging_configured = False


def configure_logging(level: int = logging.INFO, fmt: str = DEFAULT_LOG_FORMAT) -> None:
    """
    Configure the root logger once for the whole process.

    Safe to call from multiple subsystems/entry points - only the first
    call takes effect (matching logging.basicConfig's own semantics), so
    it's fine for several modules to call this defensively without
    coordinating who goes first. Prefer this over calling
    logging.basicConfig(...) directly so the format stays consistent
    everywhere instead of silently depending on import order.
    """
    global _logging_configured
    if _logging_configured:
        return
    logging.basicConfig(level=level, format=fmt)
    _logging_configured = True


def load_json(path: Path, default: Any = None, logger: Optional[logging.Logger] = None) -> Any:
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