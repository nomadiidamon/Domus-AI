# Mercurius-API: Event Bus

The messenger of the entire environment: a thread-safe, queue-based pub/sub bus. Publishers enqueue events; a single background dispatch thread delivers them to subscribers in FIFO order, so callbacks never run on a publisher's thread and one failing subscriber can't kill the bus.

Janus instantiates the bus at startup (`initialize_bus()`), publishes STARTUP/SHUTDOWN (always paired), and MODEL_LOADED/MODEL_UNLOADED from its start/stop handlers. Mentis bridges its context events onto the bus via `log_event`. The MCP tool servers publish tool activity.

## EventType
`STARTUP`, `SHUTDOWN`, `MODEL_LOADED`, `MODEL_UNLOADED`, `ERROR`, `WARNING`, `MESSAGE_SENT`, `MESSAGE_RECEIVED`, `CONVERSATION_CONDENSED`, `MEMORY_STORED`, `USER_MEMORY_UPDATED`, `TOOL_INVOKED`, `TOOL_RESULT`, `TOOL_CONFIRMATION_REQUIRED`, `CUSTOM`

## Event
`type`, `payload` (dict), `source`, `timestamp`; `to_dict()` for serialization.

## Process-wide singleton
- `initialize_bus() -> EventBus` - create + start (idempotent)
- `get_bus() -> EventBus | None`
- `shutdown_bus(drain=True)` - stop dispatch thread; `drain=False` discards queued events
- `publish_event(event_type, source="", payload=None)` - no-op when no bus is running (safe to call anywhere)

## EventBus instance API
- `subscribe(event_type, callback)` / `unsubscribe(event_type, callback) -> bool`
- `publish(event)` - non-blocking
- `start()` / `stop(drain=True, timeout=5.0)`; `start()` recovers from a dead dispatch thread
- `is_running`