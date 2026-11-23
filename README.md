# Domus-AI

Domus-AI is a local-first runtime for using AI models in development and testing workflows. It provides a command-line interface and Python APIs for managing local models, chatting with them, retaining runtime memory, and connecting permission-controlled tools. Python is the active implementation; C++ is planned.

## Quick Start

Install Ollama and Python 3.10 or newer, then install Domus-AI from a checkout:

```bash
python -m pip install ./python
janus help
```

Use `janus doctor` to check the local setup, `janus list` to see installed models, and `janus chat <model>` to start a conversation. For development, install the test extra with `python -m pip install -e "./python[dev]"` and run `python -m pytest`.

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
