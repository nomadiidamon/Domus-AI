@page python_implementation Python README

# Domus-AI for Python

This directory contains the active Domus-AI implementation: the Janus command-line runtime, installable Python packages, runtime data, tests, and development scripts. Its subsystems cover model/process actions, messaging, runtime context and memory, events, model-agent behavior, and permission-controlled MCP tools. `DomusAPI` provides a package-level facade for common library workflows.

Python 3.10 or newer and a local Ollama installation are needed for the main runtime workflows. For project-wide structure and behavior contracts, see [Architecture](https://nomadiidamon.github.io/Domus-AI/architecture.html), [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html), and [Concepts](https://nomadiidamon.github.io/Domus-AI/concepts.html). For contribution and coding guidance, see [Contributing](https://nomadiidamon.github.io/Domus-AI/contributing.html).

## Install

From the repository root:

```bash
python -m pip install ./python
```

For development and tests:

```bash
python -m pip install -e "./python[dev]"
python -m pytest -ra
```

The `janus` command is installed as a console script. The Python package source is under `src/`, the pytest suite is under `tests/`, and implementation-specific scripts are under `scripts/`.

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

## Development

From the repository root, install the editable package with its development dependencies and run the test suite:

```bash
python -m pip install -e "./python[dev]"
python -m pytest -ra
```

The editable install ensures imports use this checkout. Tests live in `tests/`; platform helpers and the cross-platform test runner live in `scripts/`.

## Metadata

Package version, description, Python requirement, authorship, and project URLs are read from the repository-level `project.ini` by `setup.py`. The distribution name remains statically declared in `pyproject.toml`, as required by PEP 621.