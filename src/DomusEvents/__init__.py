"""
DomusEvents - Domus-AI's event vocabulary and process-wide bus.

Thin layer over the generic `Mercurius` package (PyPI: mercurius-events).
"""

import logging
import threading
from enum import Enum
from typing import Optional

import Mercurius
from Mercurius import Event, EventBus

logger = logging.getLogger(__name__)

__all__ = [
    "Event",
    "EventBus",
    "EventType",
    "get_bus",
    "initialize_bus",
    "shutdown_bus",
    "publish_event",
]


class EventType(str, Enum):
    """Event categories used by Domus subsystems."""
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    MODEL_LOADED = "model_loaded"
    MODEL_UNLOADED = "model_unloaded"
    ERROR = "error"
    WARNING = "warning"
    INFERENCE_RUN = "inference_run"
    STATE_CHANGED = "state_changed"
    # Conversation traffic to/from models (published by Faber.messaging)
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    # Memory intents (published by Mentis when memory operations run)
    CONVERSATION_CONDENSED = "conversation_condensed"
    MEMORY_STORED = "memory_stored"
    USER_MEMORY_UPDATED = "user_memory_updated"
    # MCP tool server activity (published by mcp/ servers)
    TOOL_INVOKED = "tool_invoked"
    TOOL_RESULT = "tool_result"
    TOOL_CONFIRMATION_REQUIRED = "tool_confirmation_required"
    CUSTOM = "custom"


_bus: Optional[EventBus] = None
_lock = threading.Lock()


def get_bus() -> Optional[EventBus]:
    """Return the process-wide bus, or None if it hasn't been initialized."""
    return _bus


def initialize_bus() -> EventBus:
    """Create the process-wide bus. Safe to re-call; restarts a stopped one."""
    global _bus
    with _lock:
        Mercurius.init()
        if _bus is None or _bus.is_closed:
            _bus = EventBus(name="domus")
        elif not _bus.is_running:
            _bus.start()
        return _bus


def shutdown_bus(drain: bool = True) -> None:
    """Shut down the process-wide bus and release it."""
    global _bus
    with _lock:
        bus, _bus = _bus, None
    if bus is not None:
        bus.shutdown(drain=drain)


def publish_event(event_type: EventType, source: str = "", payload: Optional[dict] = None) -> None:
    """Publish to the process-wide bus; no-op if it isn't running."""
    bus = _bus
    if bus is not None and bus.is_running:
        type_str = event_type.value if isinstance(event_type, Enum) else event_type
        bus.publish(Event(type_str, payload or {}, source))
