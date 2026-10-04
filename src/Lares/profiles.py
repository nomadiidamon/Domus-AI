"""
Lares.profiles - per-model agent profiles.

An AgentProfile is what makes a model usable as a Lares Agent: the
*capabilities* and *quirks* of that specific model/base that the chat
loop (Faber.messaging.chat, and anything Lares builds on top of it)
needs to know about but that Faber itself has no business knowing,
since Faber only executes - it does not decide.

This was split out directly from real bugs seen running Mercury,
Analyst, Vulcan and Minerva through the plain Janus CLI chat loop:

  - Mercury (qwen2.5-coder base) describes tool calls as JSON text in
    its reply instead of using Ollama's native tool_calls field.
    needs_fallback_tool_parsing=True documents this; the actual parsing
    already happens defensively for any model in
    Faber.messaging._extract_fallback_tool_calls, but the profile is
    what lets Lares *know* a given model needs it, for diagnostics and
    for deciding whether to warn the user/skip advertising tools at all
    if parsing keeps failing.

  - Vulcan (deepseek-coder-v2 base) and Minerva (starcoder2 base) have
    no real native tool-calling support in their chat template at all.
    supports_tool_calls=False means Lares should not offer them `tools`
    in the first place - advertising tools to a model that was never
    templated for them produces confused, often broken output, not a
    graceful fallback.

  - Analyst (gemma-based) sometimes returns an empty reply after a tool
    result, and sometimes replies by restating its system prompt/role
    instead of using the tool result it just received. ground_tool_replies
    and retry_on_empty_reply are what Lares.response_policy acts on to
    paper over exactly those two symptoms.

Registering a new model (whether a brand new base model or a
differently-tuned build of an existing one) is adding or editing one
AgentProfile - nothing else in Lares, Faber or Janus needs to change
for the new model to get the same tool-usage, response-pattern and
permission handling as any other.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

__all__ = [
    "AgentProfile",
    "register_profile",
    "get_profile",
    "list_profiles",
    "DEFAULT_PROFILE",
]


@dataclass
class AgentProfile:
    """
    Declared capabilities and quirks for one model, keyed by model name
    (case-insensitive - see register_profile/get_profile).

    Fields are grouped by the three areas Lares currently governs
    (tool usage, response patterns, permissions); roles/traits and
    persistence are intentionally not modeled yet - see Lares.roles and
    Lares.persistence.

    Attributes:
        name:
            The model name this profile applies to (matches the name
            used with Ollama and in mcp/profiles/<Model>.json - case
            is not significant, see register_profile).
        base_model:
            Informational: the underlying Ollama base this model's
            Modelfile is FROM (e.g. "qwen2.5-coder:14b"). Not used for
            any decision here - decisions are made from the explicit
            capability flags below, which may need hand-tuning per
            build even among models that share a base.

        --- Tool usage ---
        supports_tool_calls:
            Whether this model's chat template actually emits Ollama's
            native tool_calls field at all. When False, Lares does not
            offer `tools` to the model in the first place - advertising
            tools to a model with no tool-call grammar (e.g. a plain
            starcoder2 or deepseek-coder-v2 base) tends to produce
            confused output rather than a clean refusal.
        needs_fallback_tool_parsing:
            Whether this model is known to describe tool calls as JSON
            text in its reply (bare JSON, a ```json fence, or a
            <tool_call> tag) instead of using the native field, even
            though it was offered tools. Faber.messaging already
            attempts this recovery defensively for any tools-enabled
            chat, so this flag does not change Faber's behavior - it
            documents the expectation so Lares can log/surface when a
            model that's supposed to need this *stops* needing it (base
            model or Modelfile updated) or a model that isn't supposed
            to need it starts hitting the fallback path unexpectedly.
        max_tool_iterations:
            Override for Faber.messaging.chat's max_tool_iterations.
            None means use Faber's own default.

        --- Response patterns ---
        ground_tool_replies:
            Whether Lares.response_policy should check that a reply
            following a tool result actually engages with that result,
            and issue one corrective re-prompt if it looks like the
            model ignored the tool output (e.g. restated its system
            prompt/role instead). See Lares.response_policy for the
            heuristic and its limits - it's a pragmatic patch, not a
            guarantee.
        retry_on_empty_reply:
            Whether Lares.response_policy should retry once, with an
            explicit nudge, when the model returns an empty final
            reply (seen with Analyst after a tool round-trip) instead
            of accepting the empty turn into history - an empty
            assistant turn tends to compound into further empty/broken
            replies once it's in the model's own context.

        --- Permissions ---
        mcp_profile_name:
            The mcp/profiles/<name>.json profile to use for this agent.
            Defaults to `name` - override if an agent should borrow
            another model's permission profile.

        description:
            Free-text note for humans reading the registry.
    """

    name: str
    base_model: str = ""

    # Tool usage
    supports_tool_calls: bool = True
    needs_fallback_tool_parsing: bool = False
    max_tool_iterations: Optional[int] = None

    # Response patterns
    ground_tool_replies: bool = False
    retry_on_empty_reply: bool = False

    # Permissions
    mcp_profile_name: Optional[str] = None

    description: str = ""

    def effective_mcp_profile_name(self) -> str:
        """The mcp/profiles/<...>.json name this agent should use."""
        return self.mcp_profile_name or self.name


DEFAULT_PROFILE = AgentProfile(
    name="__default__",
    description=(
        "Fallback profile for any model with no explicit registration. "
        "Conservative: assumes native tool-call support, no known quirks, "
        "and does not turn on the response-pattern workarounds (those are "
        "opt-in per model, not a blanket retry/re-prompt for everyone)."
    ),
)


_registry: Dict[str, AgentProfile] = {}


def register_profile(profile: AgentProfile) -> None:
    """Add or replace the profile for profile.name (case-insensitive key)."""
    _registry[profile.name.lower()] = profile


def get_profile(model: str) -> AgentProfile:
    """
    Return the registered profile for `model`, or DEFAULT_PROFILE if none
    is registered. Never raises - an unregistered model is meant to still
    work, just without any of the model-specific workarounds applied.
    """
    return _registry.get(model.lower(), DEFAULT_PROFILE)


def list_profiles() -> Dict[str, AgentProfile]:
    """All explicitly registered profiles, keyed by their registered name."""
    return dict(_registry)


# ---------------------------------------------------------------------------
# Built-in profiles for the models shipped with this project's Modelfiles/.
# These encode exactly the quirks diagnosed for Mercury/Analyst/Vulcan/
# Minerva. A fresh model (or a retuned Modelfile that fixes one of these
# quirks) just needs its profile added/edited here - nothing in Faber or
# Janus needs to change.
# ---------------------------------------------------------------------------

register_profile(AgentProfile(
    name="Mercury",
    base_model="qwen2.5-coder:14b",
    supports_tool_calls=True,
    needs_fallback_tool_parsing=True,
    ground_tool_replies=False,
    retry_on_empty_reply=False,
    description=(
        "Fast coding assistant. Known to describe tool calls as JSON text "
        "in content instead of native tool_calls - see "
        "Faber.messaging._extract_fallback_tool_calls."
    ),
))

register_profile(AgentProfile(
    name="Analyst",
    base_model="gemma4:12b",
    supports_tool_calls=True,
    needs_fallback_tool_parsing=False,
    ground_tool_replies=True,
    retry_on_empty_reply=True,
    description=(
        "Heavy-weight review/analysis agent. Occasionally returns an empty "
        "reply after a tool result, or replies by restating its system "
        "prompt instead of using the tool result - both workarounds are "
        "enabled for this profile."
    ),
))

register_profile(AgentProfile(
    name="Vulcan",
    base_model="deepseek-coder-v2:16b",
    supports_tool_calls=False,
    needs_fallback_tool_parsing=False,
    description=(
        "Heavy reasoning agent. Base model has no native Ollama tool-call "
        "support - tools are not offered to this model at all."
    ),
))

register_profile(AgentProfile(
    name="Minerva",
    base_model="starcoder2:7b",
    supports_tool_calls=False,
    needs_fallback_tool_parsing=False,
    description=(
        "Lightweight assistant. Base model has no native Ollama tool-call "
        "support - tools are not offered to this model at all."
    ),
))