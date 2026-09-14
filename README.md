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
The simplified general API for usage - a wrapper around Hestia's stronger more detailed API

### Hestia - General Runtime
The hearth of Domus-AI. It is the main subsytem for operating within Domus' local AI environment. It is responsible for Initializing subsytems, dependency injection and exposing a unified API that Domus-API wraps around. It is also the home for hardware and system detection. 

### Janus - Runtime State
The threshold users must cross for runtime capabilities. It is responsible for the runtime state, the CLI, Configuration laoding, other susbsystem lifecycles, startup and shutdown, and component registration.

### Mercurius - Event Bus (Not yet Implemented)
The messenger of the entire environment. It is tied directly to Janus and is instantiated when Janus starts its processes. It is responsible for sending messages, broadcasting events, subsystem coordination, and other lifecycle hooks.

### Custos - Security and MCP (Not yet Implemented / Stubbed)
The security guard of Domus-AI. It is the home for permissions, trusts, approvals and sandboxing. It also holds the Model Context Protocol(MCP) Manager that agents must work through when performing tasks actions, or gaining access to any systems.

### Mentis - Context and Memory (Not yet Implemented - Memory)
The memory and mind of the Domus environment. It is responsible for session management, persistent user and project memories, preferences, and contextual awareness.

### Lares - Agents (Not yet Implemented)
The spirits of the home (Domus). Is responsible for persistent helpers, personalized agents, specialized agents and general assistants.

### Faber - Actions (Not yet Implemented)
The actions, tools and workflows of the Lares. Handles no intelligence, thought or planning. Is only responsible for facilitating actions and executing work needed by the Lares. Can handle simple things like automation, scripting and external actions like Git.

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

### 4. Verify the setup
Run the built-in diagnostic command to confirm everything is wired up correctly:
```bash
python -m Janus doctor
```

### 5. Start a model
Models and their settings are defined in [config/models.json](config/models.json), with Ollama runtime options in [config/ollama.env](config/ollama.env). The steps to start, stop, build and check the status of a model differ slightly by platform - see the subsections below.

---

### Windows
Convenience `.ps1`/`.bat` wrappers are provided under [scripts/Windows](scripts/Windows), split into [scripts/Windows/ps1](scripts/Windows/ps1) and [scripts/Windows/bat](scripts/Windows/bat), so no manual `python -m Janus` invocation is required.

- **Start a model** (per-model wrapper, e.g. Mercury/Minerva/Vulcan):
  ```bat
  scripts\Windows\bat\Start-AI-Mercury.bat
  ```
  Or generically, for any configured model:
  ```powershell
  scripts\Windows\ps1\Start-AI.ps1 -Model mercury
  ```
- **Build a model** from its Modelfile (see [Modelfiles](Modelfiles)):
  ```powershell
  scripts\Windows\ps1\Build-AI.ps1 -Model mercury
  ```
- **Check status** of running models:
  ```bat
  scripts\Windows\bat\Status-AI.bat
  ```
- **Stop** running models:
  ```bat
  scripts\Windows\bat\Stop-AI.bat
  ```

> The `.bat` files simply invoke the matching `.ps1` script from `scripts\Windows\ps1` with `powershell.exe -ExecutionPolicy Bypass`, so running the `.ps1` scripts directly from PowerShell works the same way.

### macOS and Linux
Native shell wrappers under [scripts/MacOS](scripts/MacOS) and [scripts/Linux](scripts/Linux) are currently stubs, so use the Janus CLI directly through Python:

```bash
# Start a model (starts the Ollama server first if it isn't already running)
python -m Janus start mercury

# Check status of running models and hardware
python -m Janus status

# Build a model from its Modelfile
python -m Janus build mercury

# Stop a specific model, or all models and the Ollama server if no model is given
python -m Janus stop mercury
python -m Janus stop
```

Run `python -m Janus help` at any time for the full list of commands.

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

- **Windows**: [scripts/Windows/bat/Run-Tests.bat](scripts/Windows/bat/Run-Tests.bat) (or [scripts/Windows/ps1/Run-Tests.ps1](scripts/Windows/ps1/Run-Tests.ps1) directly)
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
