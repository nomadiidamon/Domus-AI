# Mentis: Runtime Context and Memory

The memory and mind of the Domus environment. Mentis provides `RuntimeContext`, the in-memory runtime state object, and `AIMemory`, its persistent conversation and user-memory store. Construction of a context is side-effect-free; `startup()` resolves the host project, creates managed directories, detects hardware, and loads saved state.

## RuntimeContext

Construct `RuntimeContext(project_name="DefaultProject", project_dir=None, mode=RuntimeMode.DEVELOPMENT)`. `project_dir` is advisory until startup resolves the confirmed host root.

- `startup(suggested_host=None, non_interactive=False) -> bool` initializes the context. Interactive mode may prompt for host confirmation; non-interactive mode accepts the suggestion/current directory without prompting.
- `shutdown() -> bool` marks the context stopped and persists config, AIMemory, and event state.
- `refresh_hardware() -> bool` refreshes the cached Hestia hardware profile and recommendation.
- Model/state methods: `load_model(name, metadata=None)`, `unload_model(name)`, and `record_inference(...)` update context tracking.
- Memory methods: `update_ai_memory(role, content, metadata=None)`, `get_ai_context(num_messages=10)`, `condense_conversation(keep_recent=10)`, `store_conversation_note(content, kind="note", **extra)`, and `remember_user_fact(key, value)`.
- Event/status methods: `log_event(type, message, metadata=None)`, `get_active_sessions()`, `get_system_status()`, `get_memory_usage()`, and `export_state()`.

The object exposes `config` (`ProjectConfig`), `ai_memory` (`AIMemory`), `hardware_profile`, `model_recommendation`, `loaded_models`, and an in-memory event list. `log_event()` also publishes a corresponding Mercurius event when the bus is running.

## AIMemory

With Janus' default host path helpers, persisted files are under `<host>/.domus-AI/`: `config/config.json`, `memory/ai_memory.json`, and `logs/events.json`. AIMemory state is restored on startup and saved on context shutdown. The memory object contains conversation history, learned-preference data, durable conversation notes, user facts, system instructions, and context/entry limits.

- `add_message(role, content, metadata=None)`, `get_recent_context(num_messages=10)`, and `clear_history()` manage conversation turns. History is capped by `memory_limit_entries` (default 1000).
- `condense_history(keep_recent=10)` moves older turns into a durable transcript note and keeps the latest turns. This is transcript compaction, not model-generated summarization.
- `store_note(content, kind="note", **extra)` creates a durable note that is not trimmed with conversation history.
- `remember(key, value)` and `recall(key, default=None)` store and retrieve persistent user facts.
- `to_dict()` returns serializable memory state.

RuntimeContext wrappers for condensing, notes, and facts also log memory events. Conversation history and notes are distinct: condensing preserves the old transcript as a note.

## Events and shared context

Mentis uses the canonical `Mercurius.EventType` for `ContextEvent.event_type` and `RuntimeContext.log_event()`. `ContextEventType` remains exported from Mentis as a compatibility alias to that same enum, so `ContextEventType is Mercurius.EventType`. Mentis emits context events including `INFERENCE_RUN` and `STATE_CHANGED`, which are also first-class Mercurius bus types; there is no separate Mentis event enum or translation map. `ContextEvent.to_dict()` serializes the shared enum's string value along with its message and metadata.

`get_context()` returns the process-wide context, creating an in-memory `RuntimeContext` if absent; it does not call `startup()`. `initialize_context(project_name, project_dir=None, mode=...)` replaces the global context with a new in-memory instance and likewise does not start it. For the combined, non-interactive library lifecycle use [DomusAPI](../DomusAPI/DomusAPI_Doc.md).

## Example

```python
from Mentis import RuntimeContext

context = RuntimeContext(project_name="Example")
if context.startup(suggested_host="."):
	context.update_ai_memory("user", "Prefer concise responses")
	context.store_conversation_note("Project uses pytest")
	context.shutdown()
```

The path helpers currently create and persist managed data under `.domus-AI/`. `RuntimeContext.working_dir` still points to the separate legacy `.ai-runtime/` path; see [Janus paths](../Janus/JanusAPI_Doc.md#paths-and-host-project-state).