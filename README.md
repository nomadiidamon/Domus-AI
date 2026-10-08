# Domus-AI


## Description
Domus-AI (Home-AI) is meant to serve as tool for harnessing local AI models for development and testing purposes.

It provides a simple interface to run and interact with AI models locally without relying on external APIs, and supports launching Claude Code through Ollama. See the [Faber API](src/Faber/FaberAPI_Doc.md) for that integration.

It is designed to be modular, allowing users to easily add support for new models and runtimes as desired.

This project may be used as a package for other projects, or as a standalone tool for local development and testing with AI models.

----------------------------------------------------

## Project Structure and Architecture
Subsystem responsibilities, public APIs, usage examples, and implementation status live with each subsystem:

| Subsystem | Responsibility                                                  | API documentation |
| --------- | --------------------------------------------------------------- | ----------------- |
| DomusAPI  | Stable package-level Python API.                                | [DomusAPI API](src/DomusAPI/DomusAPI_Doc.md)        |
| Hestia    | Hardware detection and model recommendations.                   | [Hestia API](src/Hestia/HestiaAPI_Doc.md)           |
| Janus     | CLI, configuration, diagnostics, paths, and runtime lifecycle.  | [Janus API](src/Janus/JanusAPI_Doc.md)              |
| Mercurius | Process-wide event bus.                                         | [Mercurius API](src/Mercurius/MercuriusAPI_Doc.md)  |
| Custos    | MCP permissions, client, and confirmation boundaries.           | [Custos API](src/Custos/CustosAPI_Doc.md)           |
| Mentis    | Runtime context and persistent memory.                          | [Mentis API](src/Mentis/MentisAPI_Doc.md)           |
| Lares     | Model profiles, tool permissions, and agent chat policy.        | [Lares API](src/Lares/LaresAPI_Doc.md)              |
| Faber     | Model/process actions and Ollama messaging.                     | [Faber API](src/Faber/FaberAPI_Doc.md)              |

The MCP server implementations and their bundled configuration are under [src/DomusMCP](src/DomusMCP).

-----------------------------------------------------

## Dependencies
### Required Dependencies
- Python: The primary programming language for running the runtime.
- Ollama: The primary runtime backend for running local AI models. Ensure you have the latest version installed.
- Git: Required by the runtime and its Git MCP integration; see the [Custos API](src/Custos/CustosAPI_Doc.md). bash should also be added to your Path (can lead to test failures if not present).

### Required Python Packages
- psutil: v5.9.0 (or greater) for CPU, RAM, and GPU usage monitoring
- packaging: v23.0 (or greater) for version comparison in dependency checks
- python-dotenv: v1.0 (or greater) for .env file support
- nvidia-ml-py: v12.0.0 (or greater), required package dependency and used for NVIDIA GPU monitoring

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

### 3b. Install the package itself
Installing the package makes the `janus` command, `python -m Janus`, and the Python subsystem packages available from any directory. See the [Janus API](src/Janus/JanusAPI_Doc.md) for CLI usage and the subsystem API docs above for Python usage. Config, Modelfiles, and MCP server definitions ship inside the package (`DomusData`, `DomusMCP`), so no repo checkout is needed at runtime.

**General usage (non-editable):**
```bash
python -m pip install .
```
This copies the package into site-packages. Re-run it after pulling changes to pick them up.

**Development (editable, with test dependencies):**
```bash
python -m pip install -e ".[dev]"
```
Editable mode always reflects your working tree in `src/`, and `[dev]` adds `pytest`. Use this if you plan to modify the code or run the tests.

### 4. Verify the setup
See the Janus [diagnostics documentation](src/Janus/JanusAPI_Doc.md#diagnostics) for the built-in setup check.

### 5. Use the runtime
The CLI is available as `janus`, `python -m Janus`, or through the optional platform launchers in [scripts](scripts). See the [Janus API documentation](src/Janus/JanusAPI_Doc.md) for command usage, chat controls, configuration, and host-project behavior. Use the subsystem API docs linked above for library workflows.

### 5b. Putting `Janus` on your PATH
After installing the package (step 3b), `janus` is already a proper command (a pip console script in `~/.local/bin` / `%APPDATA%\Scripts`) - it works from any directory with no PATH changes. This is the recommended way to invoke the CLI. The pip install does not create a capitalized `Janus` command (Windows is case-insensitive, so it resolves there anyway).

The optional per-platform scripts below are only needed if you want the repo's own `Janus` launcher on PATH instead (e.g. on a machine where the package isn't pip-installed - the launcher falls back to `python -m Janus`). They resolve their own location, so they work no matter where you invoke them from, and are idempotent (safe to re-run):

- **Linux**: `./scripts/Linux/Add-DomusToPath.sh` (appends to `~/.bashrc`)
- **macOS**: `./scripts/MacOS/Add-DomusToPath.sh` (appends to `~/.zshrc`)
- **Windows**: `scripts\Windows\Add-DomusToPath.bat` (adds to the user PATH in the registry; open a new terminal afterward)

**If the repo is moved or removed:** the PATH entry points at the repo's location at install time. After moving the repo, run `Remove-DomusFromPath` then `Add-DomusToPath` from the new location (each platform has both scripts alongside `Add-DomusToPath`). If the repo is deleted, the pip-installed `janus` command stops working too - reinstall with `pip uninstall domus-ai` to clean up. The PATH entry itself is inert if the directory no longer exists (the shell just skips it), but `Remove-DomusFromPath` will tidy it up.

The launcher scripts themselves live at [scripts/Linux/Janus.sh](scripts/Linux/Janus.sh), [scripts/MacOS/Janus.sh](scripts/MacOS/Janus.sh), and [scripts/Windows/Janus.bat](scripts/Windows/Janus.bat).

The platform-specific wrappers below are an alternative to the generic commands above - one script per operation per platform.

---

### Windows
Convenience `.bat` wrappers are provided under [scripts/Windows](scripts/Windows), calling the Python API directly (no PowerShell except for the PATH registry scripts, where `setx` would corrupt existing PATH entries):

- **Start a model** (per-model wrappers delegate to the generic one):
  ```bat
  scripts\Windows\Start-AI-Mercury.bat
  scripts\Windows\Start-AI.bat vulcan
  ```
- **Build a model** from its Modelfile (see [bundled Modelfiles](src/DomusData/Modelfiles)):
  ```bat
  scripts\Windows\Build-AI.bat mercury
  ```
- **Check status** of running models:
  ```bat
  scripts\Windows\Status-AI.bat
  ```
- **Stop** running models:
  ```bat
  scripts\Windows\Stop-AI.bat
  ```
- **Pull / list / remove** models:
  ```bat
  scripts\Windows\Pull-AI.bat qwen2.5:0.5b
  scripts\Windows\List-AI.bat
  scripts\Windows\Remove-AI.bat mercury
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

See the [Janus API documentation](src/Janus/JanusAPI_Doc.md#cli) for supported commands and options.

-----------------------------------------------------

## Using the Python APIs
For library setup, model operations, messaging, memory, MCP permissions, hardware inspection, and event subscriptions, start with the [DomusAPI documentation](src/DomusAPI/DomusAPI_Doc.md). Use the subsystem API docs linked in [Project Structure and Architecture](#project-structure-and-architecture) when lower-level control is needed.

-----------------------------------------------------

## Running Tests
Domus-AI uses `pytest` for its test suite under [tests](tests). Install the `[dev]` extra declared in [pyproject.toml](pyproject.toml) to add pytest.

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

- **Windows**: [scripts/Windows/Run-Tests.bat](scripts/Windows/Run-Tests.bat)
  ```bat
  scripts\Windows\Run-Tests.bat
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

