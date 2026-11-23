"""
Mentis - Context and memory subsystem for Domus-AI.

The memory and mind of the Domus environment: session management,
persistent user/project memories, preferences, and contextual awareness.

Provides:
- RuntimeContext: the central runtime state object (hardware profile,
  loaded models, event log, project config, AI memory)
- AIMemory / ProjectConfig: persisted state RuntimeContext manages
- get_context / initialize_context: access to the process-wide context
"""

from .context import (
    RuntimeMode,
    ContextEventType,
    ContextEvent,
    AIMemory,
    ProjectConfig,
    RuntimeContext,
    get_context,
    initialize_context,
)

__all__ = [
    "RuntimeMode",
    "ContextEventType",
    "ContextEvent",
    "AIMemory",
    "ProjectConfig",
    "RuntimeContext",
    "get_context",
    "initialize_context",
]