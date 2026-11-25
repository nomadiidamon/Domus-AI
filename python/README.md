@page python_implementation Python README

# Domus-AI for Python

This directory contains the active Domus-AI implementation: the Janus command-line runtime, installable Python packages, runtime data, tests, and development scripts. Its subsystems cover model/process actions, messaging, runtime context and memory, events, model-agent behavior, and permission-controlled MCP tools. `DomusAPI` provides a package-level facade for common library workflows.

Python 3.10 or newer and a local Ollama installation are needed for the main runtime workflows. For project-wide structure and behavior contracts, see [Architecture](https://nomadiidamon.github.io/Domus-AI/architecture.html), [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html), and [Concepts](https://nomadiidamon.github.io/Domus-AI/concepts.html). For contribution and coding guidance, see [Contributing](https://nomadiidamon.github.io/Domus-AI/contributing.html).

## Install

For a repository checkout, create and activate a virtual environment from the repository root before installing. The installer uses the Python interpreter that runs it, so an active environment keeps the development install out of the system Python:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python python/install.py
```

This installs Domus-AI from the local `python/` package in editable mode with the `dev` extra, then checks runtime prerequisites. The checkout cleanup script preserves the repository-root `.venv`. To install only the runtime package from the checkout, use `python -m pip install ./python` while the intended environment is active.

For a published PyPI installation, create and activate a virtual environment in your project, then install the distribution directly; the repository's `install.py` and cleanup script are not part of this workflow:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install domus-ai
```

For NVIDIA GPU detection, install the optional extra with `python -m pip install "domus-ai[nvidia]"` (or `python -m pip install -e "./python[dev,nvidia]"` for a checkout). Without it, Hestia may not detect NVIDIA GPUs, particularly on Linux; the extra does not install NVIDIA drivers.

For development and tests from a checkout:

```bash
python -m pip install -e "./python[dev]"
python -m pytest -c python/pyproject.toml -ra
```

The `janus` command is installed as a console script. Run `python python/install.py --check-only` to check prerequisites without installing the package or attempting repairs. The Python package source is under `src/`, the pytest suite is under `tests/`, and implementation-specific scripts are under `scripts/`.

## Use

After installation, run `janus help` to see available commands. Typical starting points are `janus doctor` for dependency and runtime diagnostics, `janus list` to inspect installed Ollama models, and `janus chat <model>` to start an interactive session. The same CLI is available as `python -m Janus`.

For application code, use `DomusAPI` for the combined library lifecycle and common operations; import subsystem packages directly when lower-level control is needed. The subsystem API references are maintained with their packages under `src/` and are included in the generated project documentation.

| Submodule | API documentation |
| --- | --- |
| DomusAPI | [Package API](https://nomadiidamon.github.io/Domus-AI/domusapi__api.html) |
| Janus | [CLI and runtime setup](https://nomadiidamon.github.io/Domus-AI/janus__api.html) |
| Mentis | [Runtime context and memory](https://nomadiidamon.github.io/Domus-AI/mentis__api.html) |
| Faber | [Process and model actions](https://nomadiidamon.github.io/Domus-AI/faber__api.html) |
| Lares | [Model agents](https://nomadiidamon.github.io/Domus-AI/lares__api.html) |
| Custos | [MCP permissions and client](https://nomadiidamon.github.io/Domus-AI/custos__api.html) |
| DomusMCP | [MCP servers and tools](https://nomadiidamon.github.io/Domus-AI/domusmcp__api.html) |
| DomusData | [Bundled runtime data](https://nomadiidamon.github.io/Domus-AI/domusdata__api.html) |

## Logging

Domus uses a shared `Auctor.Livy.Livy` instance with separate categories for each subsystem. Before a runtime starts, the `DOMUS_LOG_PATH` environment variable can specify a log file or directory on any platform. Otherwise, the default is determined by the user's platform:

| Platform | Default log file |
| --- | --- |
| Windows | `%LOCALAPPDATA%\domus-ai\Logs\domus.log` |
| macOS | `~/Library/Logs/domus-ai/domus.log` |
| Linux | `$XDG_STATE_HOME/domus-ai/log/domus.log`, or `~/.local/state/domus-ai/log/domus.log` when unset |

Runtime startup switches logging to a timestamped file in the selected host's `.ai-runtime/logs` directory. Livy closes its log automatically at interpreter exit; shutting down a runtime does not close the process-wide logger, so other Domus components can continue using it.

Applications can inspect failures through the shared instance or a subsystem category:

```python
from utils import get_log_category, livy

janus = get_log_category("Janus")
janus.info("Application ready", component="example")
failure = janus.get_last_failure()
latest_failure = livy.get_last_failure()
```

Livy logs to a file and does not configure or propagate to the Python root logger. Its `exception(error, message)` method records a traceback; category names are shared across modules within each subsystem.

## Development

From the repository root, install the editable package with its development dependencies and run the test suite:

```bash
python -m pip install -e "./python[dev]"
python -m pytest -c python/pyproject.toml -ra
```

The editable install ensures imports use this checkout. Tests live in `tests/`; platform helpers and the cross-platform test runner live in `scripts/`.

## Metadata

Package version, description, Python requirement, authorship, and project URLs are read from the repository-level `project.ini` by `setup.py`. The distribution name remains statically declared in `pyproject.toml`, as required by PEP 621.