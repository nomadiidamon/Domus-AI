# Python Documentation

This section is for documentation about developing, packaging, testing, and using the Python implementation specifically. The implementation and subsystem API references live with the Python packages; use this area for Python guidance that does not define a project-wide contract or duplicate API reference material.

## Project Guidance

Start with the shared docs when working on behavior or project structure:

- [Contributing](https://nomadiidamon.github.io/Domus-AI/contributing.html)
- [Architecture](https://nomadiidamon.github.io/Domus-AI/architecture.html)
- [Concepts](https://nomadiidamon.github.io/Domus-AI/concepts.html)
- [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html)

## API References

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

## Python Workflows

The [Python implementation README](https://github.com/nomadiidamon/Domus-AI/blob/main/python/README.md) describes installation, CLI use, package development, and tests. In brief, install the package in editable mode with its `dev` extra from the repository root, then run `python -m pytest -c python/pyproject.toml -ra` to exercise the Python suite.

Add Python-specific setup notes, packaging decisions, testing guidance, and implementation workflows here. Put shared design principles and cross-language behavior in the linked project docs, and keep public subsystem behavior documented alongside its API.