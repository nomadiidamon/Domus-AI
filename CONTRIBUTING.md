@page contributing Contributing Guidelines

# Domus-AI Contributing Guidelines

## Introduction

Thank you for your interest in contributing! This document outlines the guidelines and best practices for contributing to Domus-AI. Python is active; C++ is not yet implemented.

### Code of Conduct

All contributors are expected to follow our [Code of Conduct](https://nomadiidamon.github.io/Domus-AI/codeofconduct.html).

## Repository Model

This repository separates **implementation** from **shared semantics and concepts**:

- **Shared concepts and semantics** are in [Concepts](https://nomadiidamon.github.io/Domus-AI/concepts.html) and [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html). They describe active Python behavior and the intended cross-language contract.
- **Implementations** live in `cpp/` and `python/`, each with its own tooling. C++ is currently a placeholder; see the [C++ guide](https://nomadiidamon.github.io/Domus-AI/cpp_implementation.html) and [Python guide](https://nomadiidamon.github.io/Domus-AI/python_implementation.html).
- **Shared metadata** (version, contributors, etc.) lives in `project.ini`.
- **Examples** live under `examples/`.

See [Architecture](https://nomadiidamon.github.io/Domus-AI/architecture.html) for the full layout.

### Ground Rules

- A behavior change starts in [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html) or [Concepts](https://nomadiidamon.github.io/Domus-AI/concepts.html). Update the active Python implementation; describe any intended C++ follow-up when relevant.
- Do not introduce cross-language build dependencies. Each language keeps its native tooling.
- Do not duplicate project-wide metadata; update `project.ini`.
- Keep docs and examples in the matching language subtree.

## Getting Started

1. **Fork the Repository** using the "Fork" button on the repository page.
2. **Clone Your Fork**:
```bash
git clone --recursive https://github.com/nomadiidamon/Domus-AI <desiredLocation>
```
3. **Set Up the Development Environment** for the language(s) you are working on (see below).
4. **Create a Branch** with a descriptive name for your feature or fix.
5. **Make Changes** following the coding standards and naming conventions below.
6. **Test Your Changes**: run existing tests and add new ones where needed.
7. **Commit** with clear, concise messages in small, focused commits.
8. **Push** to your fork.
9. **Open a Pull Request** describing the problem, the solution, and which implementations are affected.
10. **Address Feedback**: maintainers may request changes. Be open to feedback and responsive.
11. **Merge**: once approved, a maintainer will merge your changes.

## Development Setup

### C++

```bash
cd cpp
premake5 <action>   # e.g. vs2022, gmake2
```

Format code with `cpp/scripts/format.sh`.

### Python

Python 3.10 or newer is required. From the `python/` directory, create a virtual environment and install the package in editable mode **with the `dev` extra**, which installs the development dependencies (pytest, linters/formatters, etc.) defined under `[project.optional-dependencies]` in `python/pyproject.toml`:

```bash
cd python
python -m venv .venv
```

#### Windows: Command Prompt

```bat
.venv\Scripts\activate
```

#### macOS and Linux

```bash
source .venv/bin/activate
```

#### Install dependencies and run tests

```bash
pip install -e ".[dev]"
```

Run the tests with `pytest` and format code with `python scripts/format.py`.

## Naming Conventions

### C++

- Snake_Case/snake_case/snake_Case is fine for private member or local variables.
- camelCase is fine for public member or local variables, although `Name` is preferred to something like `myName`.
- Functions should always be PascalCase - `DoThing()` - unless it is a variant - `DoThing_Internal()` - in which case Snake_Case is fine.

Examples:
- Class member variables (private): `m_name`, `m_array`, etc.
- Class member variables (public): `Name`, `myName`, `Length`, `applicationConfig`, etc.
- Class functions (private): `DoThing()`, `DoThing_Internal()`, etc.
- Class functions (public): `DoThing()`, `DoThingAgain()`, etc.
- Class static variables (private): `s_name`, `s_array`, etc.
- Class static variables (public): `sName`, `sArray`, etc.
- Boolean values: `bHasAccess`, `b_Access`, etc.

### Python

Follow PEP 8:

- Modules and packages: `lower_snake_case` (short, no hyphens).
- Classes and exceptions: `PascalCase` (`CapWords`).
- Functions, methods, variables, and arguments: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Non-public members and helpers: single leading underscore (`_internal_value`, `_do_thing()`).
- Name-mangled attributes: double leading underscore only when truly needed.
- Booleans: read as predicates (`is_valid`, `has_access`).
- Add type hints to public APIs and docstrings to public modules, classes, and functions.

### Cross-Language Parity

When C++ is implemented, equivalent public concepts should be recognizably the same across implementations (e.g. C++ `DoThing()` corresponds to Python `do_thing()`). Each language should use its own conventions rather than copying the other's.

## Coding Standards

- Follow the existing style of the language tree you are editing.
- Use clear, descriptive names.
- Comment only where the code cannot explain itself, such as complex logic or non-obvious constraints.
- Keep code modular and reusable; avoid duplication.
- Write unit tests for new features and bug fixes in each affected implementation.
- Ensure behavior matches [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html).
- Update docs and examples when public behavior changes.
