# Thread-safe, queue-based event bus: publishers enqueue events, a
# background dispatch thread delivers them to subscribers in FIFO order.
import logging
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event categories routed by the bus."""
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    MODEL_LOADED = "model_loaded"
    MODEL_UNLOADED = "model_unloaded"
    ERROR = "error"
    WARNING = "warning"
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


@dataclass
class Event:
    """A single message on the bus."""
    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp,
        }


Subscriber = Callable[[Event], None]

_STOP = object()  # sentinel that ends the dispatch loop


class EventBus:
    """
    Process-wide pub/sub bus with a background dispatch thread.

    publish() is non-blocking; callbacks always run on the dispatch
    thread, never on the publisher's thread.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Subscriber]] = {}
        self._lock = threading.RLock()
        self._queue: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def subscribe(self, event_type: EventType, callback: Subscriber) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: EventType, callback: Subscriber) -> bool:
        with self._lock:
            callbacks = self._subscribers.get(event_type, [])
            if callback in callbacks:
                callbacks.remove(callback)
                return True
            return False

    def publish(self, event: Event) -> None:
        """Enqueue an event. Safe to call from any thread, started or not."""
        self._queue.put(event)

    def start(self) -> None:
        with self._lock:
            if self._running and self._thread is not None and self._thread.is_alive():
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._dispatch_loop,
                name="mercurius-event-bus",
                daemon=True,
            )
            self._thread.start()

    def stop(self, drain: bool = True, timeout: float = 5.0) -> None:
        """
        Stop the dispatch thread.

        drain=True processes all queued events first (FIFO puts the stop
        sentinel behind them); drain=False discards anything still queued.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False
            thread = self._thread

        if not drain:
            with self._queue.mutex:
                self._queue.queue.clear()
        self._queue.put(_STOP)

        if thread is not None:
            thread.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._running

    def _dispatch_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is _STOP:
                break
            self._dispatch(item)

    def _dispatch(self, event: Event) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event.type, []))

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                # One bad subscriber must not kill the bus or block others
                logger.exception(
                    "Subscriber %r raised while handling %s event",
                    callback, event.type.value,
                )
