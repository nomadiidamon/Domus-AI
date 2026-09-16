"""
DomusAPI - Stable, top-level API for the Domus-AI package.

A simple wrapper around the finer-grained subsystem APIs (Hestia, Janus,
Mentis, Faber, Custos, Mercurius), meant for consumers who want a stable
surface without needing the fine-grained control those subsystems expose
directly to developers building more intensive integrations.

Every function here is library-safe: no sys.exit, no interactive prompts,
no swallowed errors - failures raise and results are returned. The Janus
CLI handles user-facing concerns (printing, exit codes); this API does not.

Example:
    import DomusAPI

    DomusAPI.init()                      # context + event bus, non-interactive
    reply = DomusAPI.ask("mercury", "Summarize this function: ...")
    print(DomusAPI.status())
    DomusAPI.shutdown()
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "init",
    "shutdown",
    "get_context",
    "detect_hardware",
    "start_model",
    "stop_model",
    "pull_model",
    "build_model",
    "list_models",
    "remove_model",
    "status",
    "ask",
    "chat",
    "get_mcp_tools",
    "allow_mcp_tool",
    "subscribe",
    "publish",
]

_context = None


def init(suggested_host=None) -> "object":
    """
    Initialize the runtime for library use: RuntimeContext (started
    non-interactively) bound to Faber, plus the Mercurius event bus.

    Returns the RuntimeContext. Safe to call twice - returns the existing
    context.
    """
    global _context
    if _context is not None:
        return _context

    from pathlib import Path

    import Mercurius
    from Faber.models import set_context
    from Mentis.context import RuntimeContext

    ctx = RuntimeContext(project_name="DomusAPI")
    try:
        started = ctx.startup(
            suggested_host=Path(suggested_host) if suggested_host else None,
            non_interactive=True,
        )
        if not started:
            raise RuntimeError("RuntimeContext startup failed - see logs for details")

        set_context(ctx)
        Mercurius.initialize_bus()
    except Exception:
        # Leave no partial state: a failed init must be invisible to callers.
        set_context(None)
        Mercurius.shutdown_bus(drain=False)
        raise

    _context = ctx
    return ctx


def shutdown() -> None:
    """Shut down the runtime context and event bus started by init()."""
    global _context
    import Mercurius
    from Faber.models import set_context

    # Context first (stops Mentis publishing), then the bus (drains last events).
    if _context is not None:
        _context.shutdown()
        _context = None
    set_context(None)
    Mercurius.shutdown_bus()


def get_context():
    """Return the active RuntimeContext (calling init() first if needed)."""
    return _context if _context is not None else init()


# ---------------------------------------------------------------------------
# Hardware (Hestia)
# ---------------------------------------------------------------------------
def detect_hardware():
    """Detect and return the system's HardwareProfile (via Hestia)."""
    from Hestia.hardware import detect_hardware as _detect
    return _detect()


# ---------------------------------------------------------------------------
# Models (Faber)
# ---------------------------------------------------------------------------
def start_model(model: str):
    """Start the Ollama server (if needed) and run a model. Returns the Session."""
    from Faber.models import start_model as _start
    from Faber.ollama_service import start_ollama

    start_ollama()
    return _start(model)


def stop_model(model: str) -> bool:
    """Stop a running model. Returns True if it was running."""
    from Faber.models import stop_model as _stop
    return _stop(model)


def pull_model(model: str) -> None:
    """Download a model from the Ollama registry."""
    from Faber.models import pull_model as _pull
    _pull(model)


def build_model(model: str) -> None:
    """Build a custom model from its Modelfile."""
    from Faber.models import build_model as _build
    _build(model)


def list_models() -> List[Dict[str, Any]]:
    """List models installed in Ollama (name/id/size/modified dicts)."""
    from Faber.models import list_models as _list
    return _list()


def remove_model(model: str) -> None:
    """Remove a model from Ollama (and stop its session if tracked)."""
    from Faber.models import remove_model as _remove
    _remove(model)


def status() -> List[Dict[str, Any]]:
    """Snapshot of all active sessions (name/type/pid/running/started)."""
    from Faber.session import get_status
    return get_status()


# ---------------------------------------------------------------------------
# Messaging (Faber.messaging)
# ---------------------------------------------------------------------------
def ask(
    model: str,
    prompt: str,
    *,
    system: Optional[str] = None,
    record: bool = True,
    **kwargs,
) -> str:
    """
    Send a single prompt to a model and return its reply text.

    Requires the Ollama server to be running (see start_model). The
    exchange is recorded into the bound RuntimeContext's AIMemory unless
    record=False.
    """
    from Faber.messaging import generate
    return generate(model, prompt, system=system, record=record, **kwargs).content


def chat(model: str, messages: List, *, record: bool = True, **kwargs) -> str:
    """
    Send a multi-turn conversation (list of Faber.messaging.Message, or
    {"role": ..., "content": ...} dicts) and return the reply text.
    """
    from Faber.messaging import Message
    from Faber.messaging import chat as _chat

    normalized = [
        m if isinstance(m, Message) else Message(m["role"], m["content"])
        for m in messages
    ]
    return _chat(model, normalized, record=record, **kwargs).content


# ---------------------------------------------------------------------------
# MCP / permissions (Custos)
# ---------------------------------------------------------------------------
def get_mcp_tools(model: str) -> Dict[str, List[str]]:
    """Tool allowlist for a model, keyed by MCP server."""
    from Custos.mcp import MCPManager
    return MCPManager().get_tools(model)


def allow_mcp_tool(tool: str, model: str) -> bool:
    """True if the model's MCP profile permits this tool call."""
    from Custos.mcp import MCPManager
    return MCPManager().allow_tool(tool, model)


# ---------------------------------------------------------------------------
# Events (Mercurius)
# ---------------------------------------------------------------------------
def subscribe(event_type, callback) -> None:
    """Subscribe a callback to a Mercurius EventType on the process-wide bus."""
    import Mercurius
    bus = Mercurius.get_bus()
    if bus is None:
        bus = Mercurius.initialize_bus()
    bus.subscribe(event_type, callback)


def publish(event_type, *, source: str = "domusapi", payload: Optional[dict] = None) -> None:
    """Publish an event on the process-wide bus (no-op if it isn't running)."""
    import Mercurius
    Mercurius.publish_event(event_type, source=source, payload=payload)
