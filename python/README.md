# Domus-AI for Python

The Python implementation of Domus-AI provides the Janus command-line runtime and importable subsystem packages for local model management, messaging, memory, MCP tools, and the public DomusAPI facade.

For project-wide architecture and the planned C++ implementation, see [the repository architecture guide](../docs/Architecture.md). For setup and runtime usage, see the [repository README](../README.md).

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

## Metadata

Package version, description, Python requirement, authorship, and project URLs are read from the repository-level `project.ini` by `setup.py`. The distribution name remains statically declared in `pyproject.toml`, as required by PEP 621.