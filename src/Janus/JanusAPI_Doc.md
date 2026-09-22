# Janus-API: Runtime State

The threshold users must cross for runtime capabilities: the CLI, configuration loading, subsystem lifecycles, startup/shutdown, and component registration.

## CLI (`Janus.main`, exposed as `janus` / `Janus` / `python -m Janus`)
Commands: `start`, `stop`, `status`, `build`, `pull`, `list`, `remove`, `ask`, `chat`, `doctor`, `mcp launch|tools`, `help`. Global flag: `--root <path>` (suggested host project root).

`ask <model> <prompt>` sends a single one-off prompt via `Faber.messaging.generate` and prints the reply. `chat <model>` starts an interactive, multi-turn REPL (type `exit`/`quit`, or Ctrl+C/Ctrl+D, to end) via `Faber.messaging.chat`, keeping conversation history in memory for the session. Both start the Ollama server first (like `start`) and go through the RuntimeContext-initializing dispatch path, so exchanges are recorded into Mentis AIMemory when a context is bound.

Read-only commands (`status`, `doctor`, `list`, `mcp tools`) dispatch without initializing the RuntimeContext, so they never trigger the interactive host prompt. Mutating commands start the RuntimeContext and the Mercurius bus first, publish paired STARTUP/SHUTDOWN events, and bind the context to Faber via `set_context`.

## Configuration (`Janus.config`)
Reads `config/models.json`, `claude.json`, `runtime.json`, and `ollama.env` from the repo's `config/` directory (resolved via `paths.find_root()`).
- `load_models_config()` / `get_model_config(name)`, `load_claude_config()`, `load_runtime_config()`, `load_env()`, `get_env(key)`, `load_all_config()`

## Paths (`Janus.paths`)
- Runtime source (read-only): `find_root()` (via `.domus-marker` or `LOCAL_AI_RUNTIME_ROOT`), `get_modelfiles_path()`, `get_mcp_path()`
- Host project (writable): `initialize_host(suggested, non_interactive)` (prompts unless non-interactive, or unless `host_marker_exists_at(suggested)` is already true - see below), `get_host_project_root()`, `ensure_host_dirs()`, and per-directory getters (`get_cache_dir`, `get_logs_dir`, `get_models_dir`, `get_memory_dir`, `get_config_dir`, `get_sessions_dir`)
- `host_marker_exists_at(path)`: read-only disk check for whether `path` already has both `.domus-host-marker` and `.domus-AI/`. Performs no writes and doesn't touch the in-memory host-root cache. `initialize_host()` uses it to silently adopt an already-initialized directory instead of re-prompting.

## Diagnostics (`Janus.doctor`)
`full_diagnostic()` - dependency checks, Ollama server health, installed-model check, MCP config validation.

## Dependencies / Installer
`Janus.dependencies` (DependencyChecker and dependency types) and `Janus.installer` back `install.py`'s check/repair flow.