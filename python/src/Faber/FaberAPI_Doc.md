# Faber: Process and Model Actions

The actions, tools and workflows of the [Lares](../Lares/LaresAPI_Doc.md). Faber executes process, model, and messaging operations for Janus and Lares. It does not select agent behavior or enforce MCP permissions; see [Lares](../Lares/LaresAPI_Doc.md) and [Custos](../Custos/CustosAPI_Doc.md) for those responsibilities.

## Sessions (`Faber.session`)

Sessions are stored in a process-local registry; they are not persisted across restarts.

- `create_session(name, process, session_type, metadata=None)` registers a subprocess and returns a `Session`.
- `get_session(name)`, `get_session_by_pid(pid)`, and `get_all_sessions()` query the registry.
- `get_status()` returns dictionaries with `name`, `type`, `running`, `pid`, and `started` (`datetime`).
- `stop_session(name) -> bool` terminates a tracked process and removes it; it returns `False` when no session exists.
- `remove_session(name)` drops a registry entry without stopping its process.
- `Session.is_running()` checks whether its process has exited.

## Ollama server (`Faber.ollama_service`)

- `start_ollama()` launches `ollama serve` and registers it as `ollama_server`. It reuses an existing Faber session with that name; it does not independently verify whether an Ollama server started outside Faber is already reachable.
- `stop_ollama()` stops the tracked `ollama_server` session.

## Models (`Faber.models`)

- `start_model(model)` launches `ollama run <model>` unless a tracked session with that model name already exists. When a context is bound, model load/unload state is reported to it.
- `stop_model(model)` stops a tracked model session; it currently has no explicit return value.
- `pull_model(model)` and `remove_model(model)` call the matching Ollama CLI operations.
- `build_model(model)` resolves the Modelfile from model configuration, then falls back to `Modelfiles/<Name>/Modelfile.<Name>`.
- `list_models()` parses `ollama list` into `name`, `id`, `size`, and `modified` fields.
- `set_context(runtime_context)` / `Faber.models.set_context(None)` bind or clear the Mentis context used for tracking.

Ollama command failures raise `RuntimeError`. Pull/build operations allow up to an hour for completion.

## Messaging (`Faber.messaging`)

Messaging uses Ollama's HTTP API via Python's standard library. The server must be reachable; these functions do not start it.

- `generate(model, prompt, *, system=None, base_url="http://localhost:11434", timeout=300, record=True) -> ChatResponse` sends one `/api/generate` request.
- `chat(model, messages, *, base_url=..., timeout=300, record=True, tools=None, tool_executor=None, max_tool_iterations=12) -> ChatResponse` sends a conversation to `/api/chat`.
- `Message(role, content, tool_name=None, tool_calls=None)` represents system, user, assistant, and tool turns.
- `ChatResponse` exposes `model`, `message`, stripped `.content`, completion/token metadata, raw response data, and `tool_trace`.

If a context is bound and `record=True`, outgoing messages, the final reply, and any tool trace are added to AIMemory. Message events are published to Mercurius when its bus is running. `record=False` suppresses memory recording, not event publishing.

For tool calling, supply Ollama-format `tools` plus a `tool_executor(name, arguments) -> str`. Faber executes tool calls and repeats the chat request until the model gives a final reply or `max_tool_iterations` is reached. Without an executor, returned tool calls remain on `response.message.tool_calls`. If a tool fails, its error is returned to the model as tool text; a network/API failure raises `RuntimeError`. Text-encoded JSON tool calls are also recovered when tools were offered.

```python
from Faber import generate, start_ollama

start_ollama()
response = generate("mercury", "Explain this function")
print(response.content)
```

## Claude Code (`Faber.claude_service`)

- `ollama_launch_claude(model, auto_yes=False)` launches `ollama launch claude --model <model>` and registers the integration session. `auto_yes=True` appends Ollama's `--yes` flag.
- `stop_claude()` stops the tracked Claude integration session.

Launching requires an Ollama version that supports the Claude integration command. A missing Ollama executable raises `RuntimeError`.

