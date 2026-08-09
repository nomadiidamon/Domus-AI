"""
runtime package.
 
This package is being phased out as part of the Domus-AI restructure — see
the project README for the target structure (Hestia, Janus, Mentis, Faber,
Custos, Lares, DomusAPI). Most of what used to live here (hardware, config,
context, session/model/ollama/claude execution) has already moved to its
new home package. What remains in runtime/ today: mcp.py (Custos territory,
not yet moved) and utils.py.
 
This __init__.py re-exports the relocated names for backwards
compatibility with anything still doing `from runtime import X`. New code
should import directly from the owning package (Faber, Janus, etc.)
instead of relying on these re-exports.
"""

__version__ = "0.1.0"
__author__ = "Domus-AI Contributors"



from Faber import (
    start_ollama,
    stop_ollama,
    start_model,
    stop_model,
    ollama_launch_claude,
    stop_claude,
    get_status,
    stop_session,
)

from Janus.doctor import (
    full_diagnostic,
)


__all__ = [

    # Ollama (moved to Faber)
    "start_ollama",
    "stop_ollama",
 
    # Models (moved to Faber)
    "start_model",
    "stop_model",
 
    # Claude (moved to Faber)
    "ollama_launch_claude",
    "stop_claude",
 
    # Sessions (moved to Faber)
    "get_status",
    "stop_session",
 
    # Diagnostics (moved to Janus)
    "full_diagnostic",
]