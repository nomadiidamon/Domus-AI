"""
Mercurius - Event bus subsystem for Domus-AI.

The messenger of the environment. Tied directly to Janus and instantiated
when Janus starts its processes. Responsible for sending messages,
broadcasting events, subsystem coordination, and other lifecycle hooks.
"""

import logging
from typing import Optional

from .bus import Event, EventBus, EventType

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

_bus: Optional[EventBus] = None


def get_bus() -> Optional[EventBus]:
    """Return the process-wide bus, or None if it hasn't been initialized."""
    return _bus


def initialize_bus() -> EventBus:
    """Create and start the process-wide bus (idempotent)."""
    global _bus
    if _bus is None or not _bus.is_running:
        _bus = EventBus()
        _bus.start()
    return _bus


def shutdown_bus(drain: bool = True) -> None:
    """Stop the process-wide bus and release the singleton."""
    global _bus
    if _bus is not None:
        _bus.stop(drain=drain)
        _bus = None


def publish_event(event_type: EventType, source: str = "", payload: Optional[dict] = None) -> None:
    """Publish to the process-wide bus; no-op if it isn't running."""
    bus = get_bus()
    if bus is not None and bus.is_running:
        bus.publish(Event(type=event_type, source=source, payload=payload or {}))