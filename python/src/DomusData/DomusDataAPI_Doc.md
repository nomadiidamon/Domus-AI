# DomusData: Bundled Runtime Data

DomusData packages the default configuration and Ollama Modelfiles used by Domus-AI. It is a data package; it does not expose Python functions. Janus resolves the bundled files through `importlib.resources` and reads configuration from `DomusData/config/` and model definitions from `DomusData/Modelfiles/`.

Set `LOCAL_AI_RUNTIME_ROOT` to use an alternate runtime data tree instead of the packaged defaults. The alternate root must contain `.domus-marker`, `config/`, and `Modelfiles/`; Janus also expects its MCP data under `mcp/` at that root.

## Configuration files

| File | Contents and use |
| --- | --- |
| `config/models.json` | Object keyed by model name. Each model entry has `base` (Ollama base model), `modelfile` (optional configured file path), `profile`, and `description`. The bundled entries are `Analyst`, `Mercury`, `Minerva`, and `Vulcan`. Model builds use the configured Modelfile when that path exists, otherwise they try the bundled `Modelfiles/<Name>/Modelfile.<Name>`. |
| `config/runtime.json` | Runtime defaults: `ollama.host` and `ollama.managed`, `claude.launcher`, and `defaultAgent`. |
| `config/claude.json` | Claude integration and UI preferences, including `permissions`, `effortLevel`, `autoUpdatesChannel`, `theme`, `editorMode`, `verbose`, `terminalProgressBarEnabled`, `ai_access`, and an `env` object for Claude-compatible endpoint/auth variables. |
| `config/ollama.env` | Environment assignments loaded through `python-dotenv` when Janus loads its environment: `OLLAMA_KEEP_ALIVE`, `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_NUM_PARALLEL`, and `OLLAMA_FLASH_ATTENTION`. Existing process environment variables are not overridden by default. |

The bundled `models.json` currently contains absolute Windows Modelfile paths as examples. They are not required for portable installs: when a configured path does not exist, the bundled per-model Modelfile path is used as a fallback.

Janus exposes configuration loading through `Janus.config`: `load_models_config()`, `get_model_config(name)`, `load_runtime_config()`, `load_claude_config()`, `load_env()`, `get_env(key, default="")`, and `load_all_config()`. Non-empty JSON config results are cached for the process lifetime. See [Janus](../Janus/JanusAPI_Doc.md) for path resolution and runtime configuration behavior.

## Bundled Modelfiles

Each model directory contains one Ollama file:

| File | Base model | Intended use |
| --- | --- | --- |
| `Modelfiles/Analyst/Modelfile.Analyst` | `gemma4:12b` | Deep analysis and project review. |
| `Modelfiles/Mercury/Modelfile.Mercury` | `qwen2.5-coder:14b` | General coding and development. |
| `Modelfiles/Minerva/Modelfile.Minerva` | `starcoder2:7b` | Lightweight scripts and quick tasks. |
| `Modelfiles/Vulcan/Modelfile.Vulcan` | `deepseek-coder-v2:16b` | Heavy reasoning and difficult engineering tasks. |

The model's `base` entry in `models.json` describes the intended Ollama base model; the Modelfile itself is the build input. These files and config assets are included as package data in built distributions.
