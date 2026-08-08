"""
Domus-AI package.

Provides management interfaces for:
- Backends:
    - Ollama server
    - Claude Code integration
- Local models
- Runtime sessions
"""

__version__ = "0.1.0"
__author__ = "Domus-AI Contributors"



from runtime.ollama_service import (
    start_ollama,
    stop_ollama,
)

from runtime.models import (
    start_model,
    stop_model,
)

from runtime.claude_service import (
    ollama_launch_claude,
    stop_claude,
)

from runtime.session import (
    get_status,
    stop_session,
)

from runtime.doctor import (
    full_diagnostic,
)


__all__ = [

    # Ollama
    "start_ollama",
    "stop_ollama",

    # Models
    "start_model",
    "stop_model",

    # Claude
    "ollama_launch_claude",
    "stop_claude",

    # Sessions
    "get_status",
    "stop_session",

    # Diagnostics
    "full_diagnostic",
]