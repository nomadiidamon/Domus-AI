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
The stable, top-level API for the whole package - a thin wrapper around the subsystems below. Library-safe: no `sys.exit`, no interactive prompts, errors raise and results return. Covers lifecycle (`init`/`shutdown`), hardware detection, model management, messaging (`ask`/`chat`), MCP permissions, and event subscription. See "Using DomusAPI as a library" below.

### Hestia - General Runtime
The hearth of Domus-AI. It is the main subsytem for operating within Domus' local AI environment. It is responsible for Initializing subsytems, dependency injection and exposing a unified API that Domus-API wraps around. It is also the home for hardware and system detection. 

### Janus - Runtime State
The threshold users must cross for runtime capabilities. It is responsible for the runtime state, the CLI, Configuration laoding, other susbsystem lifecycles, startup and shutdown, and component registration. Exposed as the `janus`/`Janus` command-line tools.

### Mercurius - Event Bus
The messenger of the entire environment: a thread-safe, queue-based pub/sub bus with a background dispatch thread. Janus instantiates it at startup and publishes lifecycle events (STARTUP/SHUTDOWN/MODEL_LOADED/MODEL_UNLOADED); Mentis bridges its context events onto it (MESSAGE_SENT/MESSAGE_RECEIVED, and the memory intents CONVERSATION_CONDENSED/MEMORY_STORED/USER_MEMORY_UPDATED); the MCP tool servers publish TOOL_INVOKED/TOOL_RESULT/TOOL_CONFIRMATION_REQUIRED.

### Custos - Security and MCP
The security guard of Domus-AI: permissions, trusts, approvals and sandboxing. Holds the MCPManager, which reads `mcp/servers.json` and `mcp/profiles/<Model>.json` to gate which MCP servers and tools each model may use (`enable`/`get_tools`/`allow_tool`). The local MCP tool servers live under `mcp/` (filesystem, git, fetch - pure Python, stdio JSON-RPC). Tools that cross the project trust boundary (e.g. `read_external_file`) ask the human running the runtime for approval on the terminal - the model cannot approve itself.

### Mentis - Context and Memory
The memory and mind of the Domus environment. It is responsible for session management, persistent user and project memories, preferences, and contextual awareness. AIMemory persists conversation history, durable conversation notes, and permanent user memory to disk (surviving restarts), and supports memory intents like condensing conversations, storing notes, and remembering user facts.

### Lares - Agents (Not yet Implemented)
The spirits of the home (Domus). Is responsible for persistent helpers, personalized agents, specialized agents and general assistants.

### Faber - Actions
The actions, tools and workflows of the Lares (and of the Janus CLI until Lares exists). Owns process/session management, Ollama server control, model lifecycle (start/stop/pull/build/list/remove), Claude Code launching, and model messaging (`chat`/`generate` over Ollama's HTTP API, with exchanges recorded into Mentis and published to Mercurius).

-----------------------------------------------------

## Dependencies
### Required Dependencies
- Python: The primary programming language for running the runtime. Requires 3.10 or greater; developed with python version 3.14.
- Ollama: The primary runtime backend for running local AI models. Ensure you have the latest version installed.
- Git: Required by the git MCP tool server and the installer checks.

### Required Python Packages
Installed automatically by `pip install -e .` (see [pyproject.toml](../pyproject.toml)):
- psutil: v5.9.0 (or greater) for CPU, RAM, and GPU usage monitoring
- packaging: v23.0 (or greater) for version comparison in dependency checks
- python-dotenv: v1.0 (or greater) for .env file support
- nvidia-ml-py: v12.0.0 (or greater) for GPU monitoring (if using NVIDIA GPUs)

The MCP tool servers and messaging layer use only the Python standard library (urllib, subprocess) - no additional dependencies.

### Optional Dependencies
- Claude Code: For Claude models, or direct integration with Claude Code's CLI if desired.
- pytest: Only needed to run the test suite (installed via [requirements.txt](../requirements.txt)).

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
The installer checks for required tools (Python, Git, Ollama) and Python packages, and attempts to auto-repair anything missing:
```bash
python install.py
```
Use `--check-only` to only report on dependency status without repairing:
```bash
python install.py --check-only
```

### 4. Install the package (editable)
To make the `janus`/`Janus` commands and `import DomusAPI` work from any directory:
```bash
python -m pip install -e .
```
Editable install is important: a plain `pip install .` copies the code into site-packages, and subsequent edits in `src/` would silently not apply. If you ever see `Could not find config directory` after pulling or reinstalling, rerun the editable install.

### 5. Verify the setup
```bash
janus doctor
```

-----------------------------------------------------

## Using the CLI

Both `janus` and `Janus` are registered commands after installation - use whichever casing you prefer:

```bash
janus start mercury        # start a model (starts the Ollama server first if needed)
janus status               # running models + hardware report
janus build mercury        # build a model from its Modelfile
janus pull qwen2.5:0.5b    # download a model
janus list                 # list installed models
janus remove mercury       # remove a model
janus stop mercury         # stop one model (or `janus stop` for everything)
janus mcp tools Mercury    # show which MCP tools a model's profile permits
janus doctor               # diagnostic checks
```

Per-platform convenience wrappers live under [scripts/](../scripts) (`Start-AI.sh`/`Status-AI.bat`/`Build-AI.sh` etc.), and each platform has `Add-DomusToPath`/`Remove-DomusFromPath` scripts if you want the launchers on your PATH permanently.

-----------------------------------------------------

## Using DomusAPI as a library
```python
import DomusAPI

DomusAPI.init()                                    # context + event bus, non-interactive
print(DomusAPI.detect_hardware().primary_accelerator)
reply = DomusAPI.ask("mercury", "Explain this function: ...")
DomusAPI.get_context().store_conversation_note("user prefers pytest")
DomusAPI.get_context().remember_user_fact("editor", "vscode")
print(DomusAPI.list_models())
DomusAPI.shutdown()
```

Subscribe to runtime events to react to model lifecycle, conversation traffic, memory intents, and MCP tool activity:
```python
import Mercurius
import DomusAPI

DomusAPI.subscribe(Mercurius.EventType.MESSAGE_RECEIVED, lambda e: print(e.payload["content"]))
```

The full function list is documented in [src/DomusAPI/__init__.py](../src/DomusAPI/__init__.py).

-----------------------------------------------------

## Running Tests
```bash
python scripts/run_tests.py          # full suite (streams + logs to test-output.log)
pytest -m "not e2e"                  # everything except live-model tests
pytest -m e2e                        # live end-to-end tests (needs a running Ollama server)
```
Per-platform wrappers: [scripts/Linux/Run-Tests.sh](../scripts/Linux/Run-Tests.sh), [scripts/MacOS/Run-Tests.sh](../scripts/MacOS/Run-Tests.sh), [scripts/Windows/bat/Run-Tests.bat](../scripts/Windows/bat/Run-Tests.bat). All forward extra arguments to pytest.

-----------------------------------------------------
