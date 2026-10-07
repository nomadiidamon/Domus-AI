# Janus: CLI and Runtime Setup

The threshold users must cross for runtime capabilities. Janus owns the `janus` command, configuration and path resolution, host initialization, dependency checks, diagnostics, and installer flow. The command is available as `janus`, `python -m Janus`, or `Janus` through the optional platform launchers.

## CLI

Run `janus help` (or `python -m Janus help`) to print built-in usage. The implemented commands are:

| Command | Behavior |
| --- | --- |
| `start <model>` | Launch the tracked Ollama server, then start the model. |
| `stop [model]` | Stop one model, or all tracked models and the Ollama server if omitted. |
| `status` | Show active sessions and hardware information. |
| `build <model>` | Build a configured model from its Modelfile. |
| `pull <model>` | Pull a model from the Ollama registry. |
| `list` | List models installed in Ollama. |
| `remove <model>` | Remove a model from Ollama. |
| `ask <model> <prompt>` | Launch the tracked Ollama server, send one prompt, and print the reply. |
| `chat <model> [--no-tools]` | Start an interactive conversation. MCP tools are enabled only when the model's profile allows them; `--no-tools` disables them. |
| `history [n]` | Show saved chat/ask turns (default: 20). Requires an initialized host project in the current directory. |
| `history --model <name> [n]` | Filter saved turns by model. |
| `history --notes [n]` | Show the most recent saved notes (default: 20). |
| `history --facts` | Show remembered user facts. |
| `doctor` | Run dependency, Ollama, model, and MCP configuration checks. |
| `mcp tools <model>` | Show profile permissions without starting the runtime context. |
| `mcp launch <model> [--yes]` | Launch Claude Code via `ollama launch claude`; `--yes` passes confirmation through. |
| `help` | Print CLI usage. |

`--root <path>` is a global suggestion for the host project root. For commands that initialize a context, Janus still asks for confirmation unless that directory is already initialized or the command is running non-interactively. The history command reads the current directory's host project state and does not accept `--root` as a history filter.

The built-in help text currently shows an `mcp enable` example, but there is no CLI implementation for that action. MCP permissions can be managed through the Custos API; Janus CLI currently implements only `mcp tools` and `mcp launch`.

### Interactive chat

At the `chat` prompt, enter:

| Command | Behavior |
| --- | --- |
| `/help` | List available chat controls. |
| `/save` | Persist current memory immediately and continue the session. |
| `/note <text>` | Store a durable conversation note. |
| `/remember <key>=<value>` | Store a persistent user fact. |
| `/condense [n]` | Move all but the latest `n` turns into a durable transcript note; default `n` is 10. |
| `/history [n]` | Print recent context turns; default `n` is 10. |
| `/tools` | List tools available in this chat, when enabled. |
| `exit`, `quit` | End the session. Ctrl+C or Ctrl+D also exits. |

The `/note`, `/remember`, `/condense`, and `/history` controls require a bound runtime context. `/tools` reports an informational message when the chat has no tools enabled. Tool setup and per-model response handling are owned by [Lares](../Lares/LaresAPI_Doc.md); MCP configuration and the low-level client are documented by [Custos](../Custos/CustosAPI_Doc.md).

### Dispatch and recording

`status`, `doctor`, `list`, `history`, and `mcp tools` use read-only paths and do not initialize a new runtime context. Commands that need runtime state initialize Mentis, bind it to Faber, and start the Mercurius bus; Janus publishes paired startup/shutdown events. CLI `ask` and `chat` record messages to AIMemory when a context is available.

## Configuration

`Janus.config` reads bundled `DomusData/config/models.json`, `claude.json`, `runtime.json`, and `ollama.env`. `LOCAL_AI_RUNTIME_ROOT` can point to an alternate runtime root containing `.domus-marker`, `config/`, `Modelfiles/`, and `mcp/` data.

The public configuration functions are `load_models_config()`, `get_model_config(name)`, `load_claude_config()`, `load_runtime_config()`, `load_env()`, `get_env(key, default="")`, and `load_all_config()`. Config loads are cached when a non-empty result is loaded.

## Paths and host-project state

`get_config_path()`, `get_modelfiles_path()`, and `get_mcp_path()` resolve data from the installed `DomusData` and `DomusMCP` packages through `importlib.resources`. `LOCAL_AI_RUNTIME_ROOT` overrides these paths and must point at a runtime root marked by `.domus-marker`. `get_python_requirements_path()` is different: it resolves `requirements.txt` from the runtime source checkout using `find_root()`.

Writable state belongs to a host project. `initialize_host(suggested=None, non_interactive=False)` adopts an existing initialized host or confirms/sets a directory; `get_host_project_root()` resolves the selected root. The host-root resolution uses the in-memory confirmed root first, then `LOCAL_AI_RUNTIME_HOST`, and otherwise requires initialization. A host is recognized on disk by `.domus-host-marker` and `.domus-AI/`. `host_marker_exists_at(path)` checks those markers without writing or changing the in-memory root. `LOCAL_AI_RUNTIME_ROOT` instead overrides the read-only runtime asset root.

`ensure_host_dirs()` creates `.domus-AI/` and its `cache/`, `config/`, `logs/`, `memory/`, `models/`, and `sessions/` directories. The corresponding getters are `get_ai_runtime_dir()`, `get_cache_dir()`, `get_config_dir()`, `get_logs_dir()`, `get_memory_dir()`, `get_models_dir()`, and `get_sessions_dir()`. RuntimeContext persists `config.json` and `ai_memory.json` in the host config and memory directories, and `events.json` under logs.

Current implementation note: `RuntimeContext.working_dir` is assigned `<host>/.ai-runtime`, while Janus' host-directory helpers and persisted state use `<host>/.domus-AI/`. Use the path helpers above to locate managed state.

## Diagnostics and installation

`Janus.doctor.full_diagnostic()` checks Python/system dependencies, Ollama availability, installed models, and MCP configuration. The `doctor` CLI command prints its result.

`Janus.dependencies.DependencyChecker` supports package, system-command, directory, and environment-variable dependencies. `Janus.installer` backs `install.py`'s check-and-repair flow; the standalone installer supports `--check-only` and `--no-repair`.