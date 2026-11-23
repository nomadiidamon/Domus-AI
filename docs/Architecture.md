@page architecture Architecture

# Domus-AI Architecture

Domus-AI is organized as a language-neutral project with an active Python implementation and a planned C++ implementation. Shared project documentation stays at the repository root; each implementation keeps its source, native build configuration, tests, and development tools in its own tree.

## Top-Level Layout

```text
Domus-AI/
|-- cpp/                 # Planned C++ implementation
|   |-- include/
|   |-- src/
|   |-- scripts/
|   `-- tool/
|-- python/              # Active Python implementation
|   |-- pyproject.toml
|   |-- setup.py
|   |-- README.md
|   |-- src/              # Installable Python packages
|   |-- tests/
|   `-- scripts/          # Development and platform helper scripts
|-- docs/                 # Shared architecture and language-specific notes
|   |-- cpp/
|   `-- python/           # Python specific documentation
|-- .github/workflows/    # Cross-project CI and documentation workflows
|-- project.ini           # Shared project metadata
|-- Doxyfile              # Doxygen documentation settings
`-- README.md             # Main project readme.md
```

## Language Boundaries

The Python implementation is packaged from `python/`; its source packages live in `python/src/`, and its tests and developer scripts are local to that implementation. The `janus` command remains the supported Python CLI.

The `cpp/` tree reserves the matching implementation boundary. It currently has no build system or implementation. When C++ work begins, use the toolchain native to that tree instead of coupling it to Python packaging.

## Shared Files

`project.ini` is the authoritative source for project-wide metadata. The root README and this architecture document describe the project as a whole. `Doxyfile`, generated documentation in `Docs/`, and the GitHub workflows are also shared. Language-specific setup and contributor notes belong under `docs/python/` or `docs/cpp/`.

## Adding Code

| Change | Location |
| --- | --- |
| Python package or runtime data | `python/src/` |
| Python tests | `python/tests/` |
| Python development helper | `python/scripts/` |
| C++ public headers | `cpp/include/` |
| C++ implementation | `cpp/src/` |
| C++ development helper | `cpp/scripts/` |
| Shared project documentation | `docs/` |