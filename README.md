# Domus-AI

Domus-AI is a local-first runtime for using AI models in development and testing workflows. It provides a command-line interface and Python APIs for managing local models, chatting with them, retaining runtime memory, and connecting permission-controlled tools. Python is the active implementation; C++ is planned.

## Quick Start

Install Ollama and Python 3.10 or newer. For a repository checkout, create and activate a virtual environment first, then install Domus-AI:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python python/install.py
janus help
```

The checkout installer uses the Python interpreter that runs it, installs the local `python/` package in editable mode with its `dev` extra, then checks runtime prerequisites. The cleanup script preserves the repository-root `.venv`. PyPI users should instead create and activate a virtual environment, then run `python -m pip install domus-ai`; the checkout installer is not needed. Use `janus doctor` to check the local setup, `janus list` to see installed models, and `janus chat <model>` to start a conversation. To install only the runtime package from a checkout, use `python -m pip install ./python` in the active environment.

The [Python implementation README](https://github.com/nomadiidamon/Domus-AI/blob/main/python/README.md) covers package installation and usage in more detail. Start with the shared project docs for design, behavior, and contribution guidance:

- [Architecture](https://nomadiidamon.github.io/Domus-AI/architecture.html)
- [Semantics](https://nomadiidamon.github.io/Domus-AI/semantics.html)
- [Concepts](https://nomadiidamon.github.io/Domus-AI/concepts.html)
- [Code of Conduct](https://nomadiidamon.github.io/Domus-AI/codeofconduct.html)
- [Contributing](https://nomadiidamon.github.io/Domus-AI/contributing.html)

## Python API References

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
