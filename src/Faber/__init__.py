"""
Faber - Agent actions subsystem for Domus-AI.

The actions, tools and workflows executed on behalf of Lares. Handles no
intelligence, thought, or planning - only facilitates actions and executes
the work Lares (or the Janus CLI, until Lares exists) requests.

Provides:
- session: process/session tracking for anything Faber launches
- ollama_service: start/stop the Ollama server
- models: start/stop/build/list/remove local models
- claude_service: launch/stop Claude Code sessions

@todo: Add a configuration option for the default Ollama server URL.
@todo: Add a configuration option for the default timeout when communicating with the Ollama server.
@todo: Add a configuration option for the maximum number of tool iterations (MAX_TOOL_ITERATIONS).
@todo: Create a base Tool class for all tools to inherit from, ensuring consistent interface and behavior.
@todo: Create a backend class for managing different model backends, ensuring consistent interface and behavior across all supported backends.
"""

from .session import (
    Session,
    create_session,
    get_session,
    get_session_by_pid,
    get_all_sessions,
    get_status,
    stop_session,
    remove_session,
)

from .ollama_service import (
    start_ollama,
    stop_ollama,
)

from .models import (
    start_model,
    stop_model,
    pull_model,
    build_model,
    list_models,
    remove_model,
    set_context,
)

from .claude_service import (
    ollama_launch_claude,
    stop_claude,
)

from .messaging import (
    Message,
    ChatResponse,
    chat,
    generate,
)

__all__ = [
    # Session
    "Session",
    "create_session",
    "get_session",
    "get_session_by_pid",
    "get_all_sessions",
    "get_status",
    "stop_session",
    "remove_session",

    # Ollama
    "start_ollama",
    "stop_ollama",

    # Models
    "start_model",
    "stop_model",
    "pull_model",
    "build_model",
    "list_models",
    "remove_model",
    "set_context",

    # Claude
    "ollama_launch_claude",
    "stop_claude",

    # Messaging
    "Message",
    "ChatResponse",
    "chat",
    "generate",
]