# Domus-AI


## Description
This is meant to serve as tool for harnessing local AI models for development and testing purposes.

It provides a simple interface to run and interact with various AI models locally without relying on external APIs, although there are plans to allow integrations with tools such as Claude Code.

It is designed to be modular, allowing users to easily add support for new models and runtimes as they become available.

This project may be used as a package for other projects, or as a standalone tool for local AI model development and testing.

----------------------------------------------------

## Project Structure and Architecture
The main pieces that comprise Domus-AI are:
### DomusAPI - Simplified API
The stable, top-level API for the whole package - a thin wrapper around the subsystems below. Library-safe: no `sys.exit`, no interactive prompts, errors raise and results return. Covers lifecycle (`init`/`shutdown`), hardware detection, model management, messaging (`ask`/`chat`), MCP permissions, and event subscription.

### Hestia - General Runtime
The hearth of Domus-AI. It is the main subsytem for operating within Domus' local AI environment. It is responsible for Initializing subsytems, dependency injection and exposing a unified API that Domus-API wraps around. It is also the home for hardware and system detection. 

### Janus - Runtime State
The threshold users must cross for runtime capabilities. It is responsible for the runtime state, the CLI, Configuration laoding, other susbsystem lifecycles, startup and shutdown, and component registration.

### Mercurius - Event Bus
The messenger of the entire environment: a thread-safe, queue-based pub/sub bus with a background dispatch thread. Janus instantiates it at startup and publishes lifecycle events (STARTUP/SHUTDOWN/MODEL_LOADED/MODEL_UNLOADED); Mentis bridges its context events onto it (including MESSAGE_SENT/MESSAGE_RECEIVED and the memory intents CONVERSATION_CONDENSED/MEMORY_STORED/USER_MEMORY_UPDATED); the MCP tool servers publish TOOL_INVOKED/TOOL_RESULT/TOOL_CONFIRMATION_REQUIRED. Subscribers can react to any of these via `Mercurius.get_bus().subscribe(...)` or `DomusAPI.subscribe(...)`.

### Custos - Security and MCP
The security guard of Domus-AI: permissions, trusts, approvals and sandboxing. Holds the MCPManager, which reads `mcp/servers.json` and `mcp/profiles/<Model>.json` to gate which MCP servers and tools each model may use (`enable`/`get_tools`/`allow_tool`). The local MCP tool servers live under [mcp/](mcp) (filesystem, git, fetch - pure Python, stdio JSON-RPC). Tools that cross the project trust boundary (e.g. `read_external_file`) ask the human running the runtime for approval on the terminal - the model cannot approve itself.

### Mentis - Context and Memory
The memory and mind of the Domus environment. It is responsible for session management, persistent user and project memories, preferences, and contextual awareness. AIMemory persists conversation history, durable conversation notes, and permanent user memory to disk (surviving restarts), and supports memory intents like condensing conversations, storing notes, and remembering user facts.

### Lares - Agents (Not yet Implemented)
The spirits of the home (Domus). Is responsible for persistent helpers, personalized agents, specialized agents and general assistants.

### Faber - Actions
The actions, tools and workflows of the Lares (and of the Janus CLI until Lares exists). Owns process/session management, Ollama server control, model lifecycle (start/stop/pull/build/list/remove), Claude Code launching, and model messaging (`chat`/`generate` over Ollama's HTTP API, with exchanges recorded into Mentis and published to Mercurius).

-----------------------------------------------------

## Dependencies
### Required Dependencies
- Python: The primary programming language for running the runtime. Developed with python version 3.14.6
- Ollama: The primary runtime backend for running local AI models. Ensure you have the latest version installed.

### Required Python Packages
- psutil: v5.9.0 (or greater) for CPU, RAM, and GPU usage monitoring
- packaging: v23.0 (or greater) for version comparison in dependency checks
- python-dotenv: v1.0 (or greater) for .env file support
- nvidia-ml-py: v12.0.0 (or greater) for GPU monitoring (if using NVIDIA GPUs)

### Optional Dependencies
- Claude Code: For Claude models, or direct integration with Claude Code's CLI if desired.

-----------------------------------------------------

## Installation and Setup

### 1. Clone the repository
```bash
git clone https://github.com/nomadiidamon/Domus-AI.git
cd Domus-AI
```

### 2. Install Ollama
Ollama is required and is not installed automatically. Download and install it from [ollama.com/download](https://ollama.com/download), then confirm it's on your `PATH`:
```bash
ollama --version
```

### 3. Run the installer
The installer checks for required tools (Python, Git, Ollama) and Python packages (`psutil`, `packaging`, `python-dotenv`, `nvidia-ml-py`), and attempts to auto-repair anything missing (e.g. installing missing Python packages via pip):
```bash
python install.py
```
Use `--check-only` (or `--no-repair`) to only report on dependency status without attempting to install/repair anything:
```bash
python install.py --check-only
```

### 3b. Install the package itself (editable)
To make `python -m Janus ...` and `from Hestia import ...` work from any directory, install the package in editable mode so it always reflects your working tree:
```bash
python -m pip install -e .
```
Editable install is important: a plain `pip install .` copies the code into site-packages, and subsequent edits in `src/` would silently not apply. If you ever see errors like `Could not find config directory` right after pulling or reinstalling, rerun the editable install command above.

### 4. Verify the setup
Run the built-in diagnostic command to confirm everything is wired up correctly:
```bash
python -m Janus doctor
```

### 5. Start a model
Models and their settings are defined in [config/models.json](config/models.json), with Ollama runtime options in [config/ollama.env](config/ollama.env). After `python -m pip install -e .`, the CLI is available three ways: `janus <command>` (pip console script, works anywhere), `python -m Janus <command>`, or `Janus <command>` via the platform shims in [scripts](scripts) (run the matching `Add-DomusToPath` script first - see below).

```bash
# Start a model (starts the Ollama server first if it isn't already running)
janus start mercury

# Check status of running models and hardware
janus status

# Build / pull / list / remove models
janus build mercury
janus pull qwen2.5:0.5b
janus list
janus remove mercury

# Stop a specific model, or all models and the Ollama server if no model is given
janus stop mercury
janus stop

# Show which MCP tools a model's profile permits
janus mcp tools Mercury
```

Run `janus help` at any time for the full list of commands.

### 5b. Putting `Janus` on your PATH
After `python -m pip install -e .`, **both** `janus` and `Janus` are already proper commands (pip console scripts in `~/.local/bin` / `%APPDATA%\Scripts`) - they work from any directory with no PATH changes. This is the recommended way to invoke the CLI.

The optional per-platform scripts below are only needed if you want the repo's own `Janus` launcher on PATH instead (e.g. on a machine where the package isn't pip-installed - the launcher falls back to `python -m Janus`). They resolve their own location, so they work no matter where you invoke them from, and are idempotent (safe to re-run):

- **Linux**: `./scripts/Linux/Add-DomusToPath.sh` (appends to `~/.bashrc`)
- **macOS**: `./scripts/MacOS/Add-DomusToPath.sh` (appends to `~/.zshrc`)
- **Windows**: `scripts\Windows\bat\Add-DomusToPath.bat` (adds to the user PATH in the registry; open a new terminal afterward)

**If the repo is moved or removed:** the PATH entry points at the repo's location at install time. After moving the repo, run `Remove-DomusFromPath` then `Add-DomusToPath` from the new location (each platform has both scripts alongside `Add-DomusToPath`). If the repo is deleted, the pip-installed `janus`/`Janus` commands stop working too - reinstall with `pip uninstall domus-ai` to clean up. The PATH entry itself is inert if the directory no longer exists (the shell just skips it), but `Remove-DomusFromPath` will tidy it up.

The launcher scripts themselves live at [scripts/Linux/Janus.sh](scripts/Linux/Janus.sh), [scripts/MacOS/Janus.sh](scripts/MacOS/Janus.sh), and [scripts/Windows/bat/Janus.bat](scripts/Windows/bat/Janus.bat).

The platform-specific wrappers below are an alternative to the generic commands above - one script per operation per platform.

---

### Windows
Convenience `.bat` wrappers are provided under [scripts/Windows/bat](scripts/Windows/bat), calling the Python API directly (no PowerShell except for the PATH registry scripts, where `setx` would corrupt existing PATH entries):

- **Start a model** (per-model wrappers delegate to the generic one):
  ```bat
  scripts\Windows\bat\Start-AI-Mercury.bat
  scripts\Windows\bat\Start-AI.bat vulcan
  ```
- **Build a model** from its Modelfile (see [Modelfiles](Modelfiles)):
  ```bat
  scripts\Windows\bat\Build-AI.bat mercury
  ```
- **Check status** of running models:
  ```bat
  scripts\Windows\bat\Status-AI.bat
  ```
- **Stop** running models:
  ```bat
  scripts\Windows\bat\Stop-AI.bat
  ```
- **Pull / list / remove** models:
  ```bat
  scripts\Windows\bat\Pull-AI.bat qwen2.5:0.5b
  scripts\Windows\bat\List-AI.bat
  scripts\Windows\bat\Remove-AI.bat mercury
  ```

### macOS and Linux
The same wrapper set exists as shell scripts under [scripts/Linux](scripts/Linux) and [scripts/MacOS](scripts/MacOS) (identical bash on both platforms):

```bash
./scripts/Linux/Start-AI.sh mercury      # or Start-AI-Mercury.sh
./scripts/Linux/Stop-AI.sh mercury
./scripts/Linux/Status-AI.sh
./scripts/Linux/Build-AI.sh mercury
./scripts/Linux/Pull-AI.sh qwen2.5:0.5b
./scripts/Linux/List-AI.sh
./scripts/Linux/Remove-AI.sh mercury
```

Or use the CLI directly - same commands:

```bash
janus start mercury
janus status
janus build mercury
janus stop mercury
janus stop
```

Run `janus help` at any time for the full list of commands.

-----------------------------------------------------

## Using DomusAPI as a library
```python
import DomusAPI

DomusAPI.init()                                    # context + event bus, non-interactive
print(DomusAPI.detect_hardware().primary_accelerator)
reply = DomusAPI.ask("mercury", "Explain this function: ...")
notes = DomusAPI.get_context().store_conversation_note("user prefers pytest")
print(DomusAPI.list_models())
DomusAPI.shutdown()
```
Subscribe to runtime events with `DomusAPI.subscribe(Mercurius.EventType.MESSAGE_RECEIVED, callback)` - the bus carries model lifecycle, conversation traffic, memory intents, and MCP tool activity.

-----------------------------------------------------

## Running Tests
Domus-AI uses `pytest` for its test suite under [tests](tests). `pytest` is installed as part of [requirements.txt](requirements.txt)/`install.py`.

### Cross-platform test runner
[scripts/run_tests.py](scripts/run_tests.py) runs the full suite the same way on Linux, macOS, and Windows, streaming results to the console while also saving a full copy to `test-output.log` at the repo root for easy sharing:
```bash
python scripts/run_tests.py
```
Any extra arguments are passed straight through to `pytest`, e.g. to run a subset of tests:
```bash
python scripts/run_tests.py -k hardware
python scripts/run_tests.py -m janus -v
```

### Platform wrapper scripts
Each platform also has a wrapper that calls `scripts/run_tests.py` for you, matching the per-platform layout used for the runtime scripts:

- **Windows**: [scripts/Windows/bat/Run-Tests.bat](scripts/Windows/bat/Run-Tests.bat)
  ```bat
  scripts\Windows\bat\Run-Tests.bat
  ```
- **macOS**: [scripts/MacOS/Run-Tests.sh](scripts/MacOS/Run-Tests.sh)
  ```bash
  ./scripts/MacOS/Run-Tests.sh
  ```
- **Linux**: [scripts/Linux/Run-Tests.sh](scripts/Linux/Run-Tests.sh)
  ```bash
  ./scripts/Linux/Run-Tests.sh
  ```

All wrappers forward any extra arguments to `pytest`, e.g. `./scripts/Linux/Run-Tests.sh -k hardware`.

### Running pytest directly
Alternatively, run `pytest` directly from the repo root:
```bash
pytest
```

-----------------------------------------------------
