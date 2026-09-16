"""
confirmation.py - Human-in-the-loop approval for sensitive MCP tools.

Tools that act outside the project's trust boundary (e.g. reading files
outside the host project root) must not proceed on the model's say-so -
the 'confirm' argument in a tools/call request comes from the *client*
(the model/agent), so it proves nothing. Real confirmation has to come
from the human running Domus-AI.

Approval is resolved in this order:

  1. The path is in the DOMUS_APPROVED_EXTERNAL_READS env var (os.pathsep-
     separated list of exact paths) - the non-interactive escape hatch
     for automation, set by the human ahead of time.
  2. An interactive y/N prompt on the controlling terminal. The server's
     stdin/stdout are the JSON-RPC pipe, so the prompt goes through
     /dev/tty (falling back to stdin when there is no controlling
     terminal, e.g. unit tests driving the server in-process).
  3. Anything else - denial. Failure to even ask (no TTY, EOF) denies.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

_APPROVED_ENV_VAR = "DOMUS_APPROVED_EXTERNAL_READS"


def is_preapproved(path: str, env_var: str = _APPROVED_ENV_VAR) -> bool:
    """True if the human pre-approved this exact path via environment."""
    approved = os.environ.get(env_var, "")
    return bool(approved) and path in approved.split(os.pathsep)


def request_confirmation(prompt: str) -> bool:
    """
    Ask the human running Domus-AI for a yes/no decision.

    Reads the answer from the controlling terminal so the question reaches
    the user even while the server's stdin/stdout carry the MCP protocol.
    Returns True only on an explicit affirmative ('y'/'yes').
    """
    question = f"{prompt} [y/N] "
    try:
        if os.path.exists("/dev/tty"):
            with open("/dev/tty", "r") as tty_in, open("/dev/tty", "w") as tty_out:
                tty_out.write(question)
                tty_out.flush()
                answer = tty_in.readline()
        else:
            # No controlling terminal (in-process tests, some IDEs): fall
            # back to stdout/stdin - callers using real stdio protocol mode
            # will have pre-approved via the env var instead.
            print(question, end="", flush=True)
            answer = sys.stdin.readline()
    except OSError as e:
        logger.warning("Could not prompt user for confirmation: %s", e)
        return False

    return answer.strip().lower() in ("y", "yes")


def require_user_approval(description: str, path: str) -> None:
    """
    Gate a sensitive operation on human approval.

    Args:
        description: What is being asked, e.g. "read a file outside the
                     project root" - shown in the prompt.
        path: The resource being accessed (pre-approval key + prompt text).

    Raises:
        PermissionError: If the human did not approve.
    """
    if is_preapproved(path):
        logger.info("Pre-approved via %s: %s", _APPROVED_ENV_VAR, path)
        return

    if not request_confirmation(
        f"MCP server requests to {description}:\n  {path}\nAllow?"
    ):
        raise PermissionError(
            f"User denied: {description} ({path}). "
            f"Pre-approve via {_APPROVED_ENV_VAR} for non-interactive use."
        )

    logger.info("User approved: %s (%s)", description, path)
