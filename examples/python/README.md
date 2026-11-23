# Python Examples

Each Python example has a `main()` entry point and can be run with `python path/to/example.py` after installing the package. Model-backed examples additionally need a reachable Ollama server and the named model.

Run all seven groups from the repository root with:

```sh
python examples/python/run_all_examples.py
```

The runner adds `python/src` to the subprocess import path, but the project's dependencies must still be installed in the selected Python environment (for example, with `python -m pip install -e ./python`). The DomusAPI, Faber, and Lares messaging examples require a reachable Ollama server with the `mercury` model. Runtime examples can create or modify state in the repository root.

| Area | Examples |
| --- | --- |
| DomusAPI | `DomusAPI_1_lifecycle.py`, `DomusAPI_2_messaging.py`, `DomusAPI_3_events.py` |
| Janus | `Janus/Janus_1_cli.py`, `Janus/Janus_2_configuration.py` |
| Mentis | `Mentis/Mentis_1_memory.py` |
| Custos | `Custos/Custos_1_mcp_permissions.py` |
| DomusEvents | `DomusEvents/DomusEvents_1_pub_sub.py` |
| Faber | `Faber/Faber_1_messaging.py` |
| Lares | `Lares/Lares_1_agent_chat.py` |