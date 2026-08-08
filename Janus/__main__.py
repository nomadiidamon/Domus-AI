"""
Entry point for `python -m Janus <command>`.

Janus owns the CLI and acts as the runtime orchestrator, dispatching into
Hestia (hardware), and the not-yet-relocated runtime/ modules (Faber/Custos
territory: session, models, ollama_service, claude, mcp) as they move.

Actual argument parsing and command handling lives in main.py so it can be
imported and tested independently of this shim.
"""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())