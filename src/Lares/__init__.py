"""
Lares - Agents subsystem for Domus-AI.

The spirits of the home (Domus). Responsible for persistent helpers,
personalized agents, specialized agents, and general assistants.

Faber executes actions and knows nothing about which model it's talking
to beyond the string name; Custos gates permissions from static config;
neither one decides whether a given model should be trusted with tools
or whether its replies are any good. Lares is the layer that makes those
decisions, as three concrete pieces (the current scope):

  - profiles:        per-model capability/quirk declarations
                      (AgentProfile) - the registry that makes adding a
                      new model, or fixing/tightening an existing one's
                      behavior, a one-place edit.
  - permissions:      an agent-scoped view over Custos.MCPManager, plus
                      the "does this model's base even support tool
                      calls at all" gate Custos has no concept of.
  - response_policy:  detects and corrects the two known-bad reply
                      patterns seen in practice (an empty reply after a
                      tool round-trip, and a reply that ignores a tool
                      result it just received) - gated per-profile, not
                      applied blanket to every model.

agent.Agent ties those three together into one object per model;
Janus.main.handle_chat is built on top of it rather than reimplementing
tool setup/response handling itself.

roles (personas/traits) and persistence (durable agent state across
restarts) are intentionally stubbed - see their modules for why neither
is built out yet.

@todo: Finish implementing the roles module
@todo: Finish implementing the persistence module
"""

from .agent import Agent
from .permissions import AgentPermissions
from .profiles import AgentProfile, get_profile, list_profiles, register_profile

__all__ = [
    "Agent",
    "AgentPermissions",
    "AgentProfile",
    "get_profile",
    "list_profiles",
    "register_profile",
]