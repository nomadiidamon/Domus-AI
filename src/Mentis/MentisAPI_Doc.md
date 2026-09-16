# Mentis-API: Context and memory

The memory and mind of the Domus environment: runtime state, session management, persistent user/project memories, preferences, and contextual awareness.

## RuntimeContext (`Mentis.context`)
The central state object. Construction is side-effect-free; `startup()` resolves the host project root (via Janus.paths), creates the `.ai-runtime/` directories, detects hardware, and loads saved state. `shutdown()` unloads models and persists state.

- State: `config` (ProjectConfig), `ai_memory` (AIMemory), `hardware_profile`, `model_recommendation`, `loaded_models`, `events`
- Lifecycle: `startup(suggested_host=None, non_interactive=False)`, `shutdown()`, `refresh_hardware()`
- Model tracking: `load_model(name, metadata)`, `unload_model(name)`, `record_inference(...)`
- Events: `log_event(type, message, metadata)` - also bridges to the Mercurius bus (no-op without one)
- Status: `get_system_status()`, `get_memory_usage()`, `get_active_sessions()`, `export_state()`

## AIMemory
Persisted to `<host>/.ai-runtime/memory/ai_memory.json` on shutdown and restored on startup.
- `add_message(role, content, metadata)`, `get_recent_context(n)`, `clear_history()`
- `condense_history(keep_recent=10)` - folds old messages into a durable transcript note ("condense the conversation")
- `store_note(content, kind="note")` - durable conversation notes, never trimmed ("store this in conversation memory")
- `remember(key, value)` / `recall(key)` - permanent user memory ("add this to permanent user memory")
- RuntimeContext wrappers: `condense_conversation`, `store_conversation_note`, `remember_user_fact` (each logs an event)

## Events
`ContextEventType`: STARTUP, SHUTDOWN, MODEL_LOADED, MODEL_UNLOADED, INFERENCE_RUN, ERROR, WARNING, STATE_CHANGED, MESSAGE_SENT, MESSAGE_RECEIVED, CONVERSATION_CONDENSED, MEMORY_STORED, USER_MEMORY_UPDATED.

## Singleton
`initialize_context(...)` / `get_context()` for the process-wide context.