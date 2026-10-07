# DomusAPI: Package API

`DomusAPI` is the stable, package-level Python surface over Hestia, Faber, Custos, Mentis, and Mercurius. Use it when you want common operations without managing the lower-level subsystem objects directly.

It does not use the CLI's `sys.exit` or host-selection prompt. Errors are raised to the caller. Initialization still creates the host marker and runtime directories through `RuntimeContext.startup()`; a startup failure can print the context's diagnostic before `init()` raises.

## Lifecycle

- `init(suggested_host=None) -> RuntimeContext` starts a non-interactive Mentis context, binds it to Faber, and starts the Mercurius bus. It returns the already-active context when called again.
- `get_context() -> RuntimeContext` returns the active context or calls `init()` if needed.
- `shutdown() -> None` shuts down the context before draining and stopping the event bus, then clears Faber's context binding.

When no host is supplied, initialization uses the current working directory. Pass `suggested_host` to select another existing directory.

## Public functions

### Hardware

- `detect_hardware() -> HardwareProfile` runs Hestia hardware detection.

### Models and sessions

- `start_model(model)` starts Ollama if needed and starts the named model.
- `stop_model(model)` stops the tracked model session. Although DomusAPI annotates this as returning `bool`, Faber currently returns `None`, so callers must not use the result as a success flag.
- `pull_model(model)`, `build_model(model)`, and `remove_model(model)` manage Ollama models.
- `list_models() -> list[dict]` returns installed model details (`name`, `id`, `size`, `modified`).
- `status() -> list[dict]` returns tracked session status (`name`, `type`, `pid`, `running`, `started`).

### Messaging

- `ask(model, prompt, *, system=None, record=True, **kwargs) -> str` sends one prompt and returns reply text. The Ollama server must be reachable; unlike the Janus CLI `ask`, this function does not start it.
- `chat(model, messages, *, record=True, **kwargs) -> str` sends a conversation and returns reply text. `messages` may contain Faber `Message` objects or dictionaries with `role` and `content` keys. Messaging keyword arguments are forwarded to Faber, including `base_url`, `timeout`, and (for `chat`) tool options.
- When a RuntimeContext is bound, outgoing messages and replies are recorded unless `record=False`.

### MCP permissions

- `get_mcp_tools(model) -> dict[str, list[str]]` returns the model profile's allowed tool names grouped by server.
- `allow_mcp_tool(tool, model) -> bool` checks the model's profile for a tool.

These functions inspect permission configuration; they do not launch MCP servers. See the [Custos API](../Custos/CustosAPI_Doc.md) and [Lares API](../Lares/LaresAPI_Doc.md) for execution and agent-level behavior.

### Events

- `subscribe(event_type, callback)` initializes the process-wide bus if necessary and subscribes a callback receiving a `Mercurius.Event`.
- `publish(event_type, *, source="domusapi", payload=None)` publishes only when the bus is running; otherwise it is a no-op.

`DomusAPI` does not expose a top-level unsubscribe function. For that operation, use `Mercurius.get_bus().unsubscribe(...)`.

## Example

```python
import DomusAPI
from Mercurius import EventType

try:
	context = DomusAPI.init(".")
	hardware = DomusAPI.detect_hardware()
	print(hardware.primary_accelerator)
	DomusAPI.start_model("mercury")
	reply = DomusAPI.ask("mercury", "Explain this function")
	context.store_conversation_note("user prefers concise answers")
	print(reply)
finally:
	DomusAPI.shutdown()
```

To subscribe to message events, define a callback that accepts an event and call `DomusAPI.subscribe(EventType.MESSAGE_RECEIVED, callback)` after or before initialization.