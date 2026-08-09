"""
Handles the Claude Code integration through Ollama.
"""

import subprocess
import logging
from typing import Optional

from Faber.session import create_session, get_session, stop_session


logger = logging.getLogger(__name__)


CLAUDE_SESSION_NAME = "claude"


def ollama_launch_claude(
    model: str,
    auto_yes: bool = False
) -> Optional[subprocess.Popen]:

    if not model or not isinstance(model, str):
        raise ValueError(
            f"Model must be a non-empty string, got: {model}"
        )


    existing = get_session(CLAUDE_SESSION_NAME)

    if existing:
        logger.info("Claude Code already running")
        return existing.process


    command = [
        "ollama",
        "launch",
        "claude",
        "--model",
        model
    ]


    if auto_yes:
        command.append("--yes")


    try:

        logger.info(
            f"Launching Claude Code through Ollama using {model}"
        )


        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )


        create_session(
            name=CLAUDE_SESSION_NAME,
            process=process,
            session_type="integration",
            metadata={
                "provider": "ollama",
                "integration": "claude",
                "model": model
            }
        )


        return process


    except FileNotFoundError:

        raise RuntimeError(
            "Ollama is not installed or not in PATH."
        )


def stop_claude():

    return stop_session(CLAUDE_SESSION_NAME)