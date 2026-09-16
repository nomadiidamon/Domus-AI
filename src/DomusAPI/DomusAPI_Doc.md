# Domus-API: DomusAI Package API

The stable, top-level API for the entire DomusAI project - a thin wrapper around the subsystem APIs (Hestia, Janus, Mentis, Faber, Custos, Mercurius) for consumers who want a simple surface without fine-grained subsystem control.

**Contract:** every function is library-safe - no `sys.exit`, no interactive prompts, no print-and-swallow. Errors raise, results return. The Janus CLI owns user-facing concerns; this API does not.

## Lifecycle
- `init(suggested_host=None) -> RuntimeContext` - start context + event bus (non-interactive, idempotent)
- `shutdown()` - context first, then the bus (so Mentis' final events drain)
- `get_context()` - active RuntimeContext (calls `init()` if needed)

## Hardware (Hestia)
- `detect_hardware() -> HardwareProfile`

## Models (Faber)
- `start_model(model)` - starts the Ollama server first, then the model
- `stop_model(model) -> bool`
- `pull_model(model)` / `build_model(model)` / `remove_model(model)`
- `list_models() -> [{name, id, size, modified}]`
- `status() -> [{name, type, pid, running, started}]`

## Messaging (Faber.messaging)
- `ask(model, prompt, system=None, record=True) -> str` - single prompt, returns reply text
- `chat(model, messages, record=True) -> str` - multi-turn; messages may be `Message` objects or `{"role", "content"}` dicts

## MCP (Custos)
- `get_mcp_tools(model) -> {server: [tools]}`
- `allow_mcp_tool(tool, model) -> bool`

## Events (Mercurius)
- `subscribe(event_type, callback)` - initializes the bus if needed
- `publish(event_type, source="domusapi", payload=None)`