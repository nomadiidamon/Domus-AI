# Faber-API: Agent Actions

The actions, tools and workflows of the Lares - and of the Janus CLI until Lares exists. Handles no intelligence, thought or planning: it facilitates actions and executes work (sessions, Ollama processes, model lifecycle, messaging, Claude Code launches).

## Sessions (`Faber.session`)
Process registry for anything Faber launches.
- `create_session(name, process, session_type, metadata)`, `get_session`, `get_session_by_pid`, `get_all_sessions`
- `get_status() -> [session dicts]`, `stop_session(name)`, `remove_session(name)`
- `Session` dataclass with `is_running()`

## Ollama server (`Faber.ollama_service`)
- `start_ollama()` - spawns `ollama serve` (idempotent), `stop_ollama()`

## Models (`Faber.models`)
- `start_model(model)` / `stop_model(model)` - `ollama run`; notifies the bound context (see below)
- `pull_model(model)`, `build_model(model)` (resolves the Modelfile via config, falling back to `Modelfiles/<Name>/Modelfile.<Name>`), `list_models()`, `remove_model(model)`
- `set_context(runtime_context)` - bind a Mentis RuntimeContext so load/unload events are tracked

## Messaging (`Faber.messaging`)
Talks to models over Ollama's HTTP API (stdlib only).
- `chat(model, messages, record=True) -> ChatResponse` - multi-turn via `/api/chat`
- `generate(model, prompt, system=None, record=True) -> ChatResponse` - single prompt via `/api/generate`
- `Message(role, content)`, `ChatResponse` (`.content` = stripped reply text)
- Publishes MESSAGE_SENT / MESSAGE_RECEIVED (and ERROR on failure) to Mercurius; records exchanges into the bound context's AIMemory unless `record=False`

## Claude Code (`Faber.claude_service`)
- `ollama_launch_claude(model, auto_yes=False)` / `stop_claude()`