# Mercurius: Event Bus

The messenger of the Domus environment. Mercurius provides a process-wide, thread-safe, queue-based pub/sub bus. `publish()` enqueues without waiting; one background thread dispatches events in FIFO order. Subscriber callbacks run on that dispatch thread, and an exception from one callback is logged without stopping delivery to the others.

Mercurius owns the canonical event vocabulary used by all subsystems. Janus publishes lifecycle and model events, Faber publishes message traffic, Mentis records context and memory events using these same `EventType` values, and MCP servers publish tool activity when configured to do so. Mentis re-exports `ContextEventType` as a compatibility alias of `Mercurius.EventType`; it is not a separate enum.

## Events

`EventType` values are `STARTUP`, `SHUTDOWN`, `MODEL_LOADED`, `MODEL_UNLOADED`, `INFERENCE_RUN`, `STATE_CHANGED`, `ERROR`, `WARNING`, `MESSAGE_SENT`, `MESSAGE_RECEIVED`, `CONVERSATION_CONDENSED`, `MEMORY_STORED`, `USER_MEMORY_UPDATED`, `TOOL_INVOKED`, `TOOL_RESULT`, `TOOL_CONFIRMATION_REQUIRED`, and `CUSTOM`. 

`INFERENCE_RUN` and `STATE_CHANGED` cover Mentis context events; both are first-class bus types, not remapped to `CUSTOM`.

An `Event` has `type`, `payload` (dictionary), `source`, and ISO-formatted `timestamp`. `Event.to_dict()` returns a serializable dictionary.

## Process-wide API

- `initialize_bus() -> EventBus` creates and starts the singleton; repeated calls while it is running return it.
- `get_bus() -> EventBus | None` returns the current singleton.
- `publish_event(event_type, source="", payload=None)` enqueues only when the singleton is running; otherwise it is a no-op.
- `shutdown_bus(drain=True)` stops the dispatch thread and clears the singleton. With `drain=False`, queued events are discarded.

## EventBus API

- `subscribe(event_type, callback)` registers a callback receiving an `Event`.
- `unsubscribe(event_type, callback) -> bool` removes a matching callback, if present.
- `publish(event)` enqueues an event and returns immediately.
- `start()` is idempotent while the thread is alive and can restart a stopped/dead dispatcher.
- `stop(drain=True, timeout=5.0)` stops the dispatcher; draining processes already-queued events first.
- `is_running` reports whether dispatch is active.

The process-wide helper `publish_event()` is safe to call before initialization because it becomes a no-op. A direct `EventBus.publish()` may queue before `start()`; queued events are delivered after the bus starts.

## Example

```python
from Mercurius import EventType, initialize_bus, shutdown_bus

def on_message(event):
	print(event.source, event.payload)

bus = initialize_bus()
bus.subscribe(EventType.MESSAGE_RECEIVED, on_message)
try:
	# Runtime components publish events while the bus is running.
	...
finally:
	bus.unsubscribe(EventType.MESSAGE_RECEIVED, on_message)
	shutdown_bus()
```