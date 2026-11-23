"""
Entry point for `python -m Janus <command>`.
 
Janus owns the CLI and acts as the runtime orchestrator, dispatching into
Hestia (hardware), Faber (session/model/ollama/claude execution), Mentis
(context/memory), and Custos (MCP/security) as needed.
 
Actual argument parsing and command handling lives in main.py so it can be
imported and tested independently of this shim.
"""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())