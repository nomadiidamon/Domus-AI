"""
Lares.response_policy - post-processing for a model's reply pattern.

Faber.messaging.chat() is purely mechanical: it runs the tool-call loop
and hands back whatever the model said. It has no opinion on whether
that reply is actually any good. This module is where that opinion
lives, and it exists because of two concrete failure patterns seen
running Analyst (gemma-based) through tool-enabled chat:

  1. Empty reply after a tool round-trip. Faber.messaging would append
     the empty assistant turn into history as if it were a normal
     answer; every later turn then replays that empty turn back to the
     model, which tends to compound into more empty/broken replies and
     the conversation never recovers on its own.

  2. "Prompt echo" - the model runs the requested tool(s), gets the
     result back, and then answers with something that reads like its
     own system prompt/persona description instead of using what the
     tool actually returned (e.g. "As a programming analyst, I focus on
     clarity and optimization..." instead of commenting on the file it
     was just asked to read).

Both are handled the same way: detect the pattern, then re-ask the
model once with a small, explicit nudge rather than silently accepting
the bad reply or silently retrying with no guidance (which tends to
reproduce the same failure). This is a pragmatic patch, not a proof of
correctness - the "did it actually use the tool result" check in
looks_like_prompt_echo() is a heuristic, not a semantic one, and a
model can still find a way to produce a bad reply that slips past it.
A more robust version of this (e.g. a real critic pass) is a reasonable
next step for Lares once there's a stronger need for it.

Nothing here is model-specific by name - behavior is driven entirely by
the AgentProfile passed in (ground_tool_replies / retry_on_empty_reply),
so turning this on for a different model (or off for Analyst, if a
future build stops needing it) is a one-line profile change, not a code
change here.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional

from Faber.messaging import ChatResponse, Message

if TYPE_CHECKING:
    from Lares.profiles import AgentProfile

logger = logging.getLogger(__name__)

__all__ = [
    "ResponsePolicyResult",
    "apply_response_policy",
    "looks_like_empty_reply",
    "looks_like_prompt_echo",
]

# A nudge appended as a synthetic user turn, never shown to the end user
# as if they'd typed it - see apply_response_policy. Kept generic (no
# model-specific wording) since it's driven by AgentProfile, not a
# per-model branch here.
_EMPTY_REPLY_NUDGE = (
    "Your previous response was empty. Using the tool result above, "
    "please answer the original question now."
)

_PROMPT_ECHO_NUDGE = (
    "Your previous response didn't engage with the tool result above - it "
    "read like a general description of your role instead of an answer. "
    "Please look at the tool result directly and answer the original "
    "question using what it actually contains."
)

# Phrases that tend to show up when a model falls back to describing its
# own persona/mission instead of answering - deliberately short and
# generic (first-person role framing), not a list of magic keywords to
# chase; this is meant to catch the common shape of a prompt echo, not
# every possible one.
_PROMPT_ECHO_MARKERS = (
    "as a programming analyst",
    "as an analyst",
    "my purpose is to",
    "my mission is to",
    "i am a programming analyst",
    "i am an ai assistant",
    "i'm a programming analyst",
)


@dataclass
class ResponsePolicyResult:
    """
    Outcome of running apply_response_policy over a ChatResponse.

    response:  The (possibly retried) ChatResponse to actually use.
    retried:   Whether a corrective re-prompt happened.
    reason:    Why a retry happened ("empty_reply" / "prompt_echo"), or
               None if the original reply was accepted as-is.
    """
    response: ChatResponse
    retried: bool = False
    reason: Optional[str] = None


def looks_like_empty_reply(response: ChatResponse) -> bool:
    """True if the model's final reply has no real content."""
    return not response.content.strip()


def looks_like_prompt_echo(response: ChatResponse) -> bool:
    """
    Heuristic: True if a reply that followed a tool call looks like it
    ignored the tool's result and just restated the model's role/persona
    instead. Only meaningful when response.tool_trace is non-empty (i.e.
    a tool actually ran this turn) - callers should check that first,
    since the same wording in a reply to an ordinary question is not a
    problem.
    """
    content = response.content.lower()
    if not content:
        return False
    return any(marker in content for marker in _PROMPT_ECHO_MARKERS)


def _last_tool_result_text(tool_trace: List[Message]) -> str:
    """The most recent role="tool" message's content, or "" if none."""
    for message in reversed(tool_trace):
        if message.role == "tool":
            return message.content
    return ""


def apply_response_policy(
    response: ChatResponse,
    profile: "AgentProfile",
    retry: Callable[[Message], ChatResponse],
) -> ResponsePolicyResult:
    """
    Inspect `response` against `profile`'s enabled workarounds and, if a
    known bad pattern is detected, issue exactly one corrective retry.

    Args:
        response: The ChatResponse to evaluate (as returned by
                  Faber.messaging.chat()).
        profile:  The agent's AgentProfile - retry_on_empty_reply and
                  ground_tool_replies gate whether each check runs at
                  all for this model.
        retry:    Callback that takes the synthetic nudge Message to
                  append and returns a fresh ChatResponse for the
                  retried turn (the caller owns how that's actually
                  sent - typically a thin wrapper around
                  Faber.messaging.chat with the nudge appended to
                  history). Called at most once.

    Returns:
        ResponsePolicyResult wrapping either the original response
        (nothing looked wrong, or the relevant workaround is off for
        this profile) or the retried one (only one retry is ever
        attempted - if the retry is *also* bad, it's returned as-is
        rather than looping, to avoid masking a real problem behind
        silent retries).
    """
    if profile.retry_on_empty_reply and looks_like_empty_reply(response):
        logger.info(
            "Agent '%s' returned an empty reply - retrying once with a nudge",
            profile.name,
        )
        retried_response = retry(Message("user", _EMPTY_REPLY_NUDGE))
        return ResponsePolicyResult(retried_response, retried=True, reason="empty_reply")

    if (
        profile.ground_tool_replies
        and response.tool_trace
        and looks_like_prompt_echo(response)
    ):
        logger.info(
            "Agent '%s' replied without engaging with its tool result - "
            "retrying once with a grounding nudge", profile.name,
        )
        retried_response = retry(Message("user", _PROMPT_ECHO_NUDGE))
        return ResponsePolicyResult(retried_response, retried=True, reason="prompt_echo")

    return ResponsePolicyResult(response)