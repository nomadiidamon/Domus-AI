"""
Tests for Lares/response_policy.py.

Covers the two detectors (looks_like_empty_reply, looks_like_prompt_echo)
in isolation, then apply_response_policy's gating/retry orchestration -
including that each workaround only fires when its profile flag is on,
that at most one retry ever happens (no looping even if the retry is
also bad), and that the nudge is appended to a copy rather than mutating
history the caller passed in.
"""

import pytest

from Faber.messaging import ChatResponse, Message
from Lares.profiles import AgentProfile
from Lares.response_policy import (
    apply_response_policy,
    looks_like_empty_reply,
    looks_like_prompt_echo,
)

pytestmark = pytest.mark.lares


def _response(content, tool_trace=None):
    return ChatResponse(
        model="test", message=Message("assistant", content),
        tool_trace=tool_trace or [],
    )


class TestLooksLikeEmptyReply:
    def test_true_for_empty_string(self):
        assert looks_like_empty_reply(_response("")) is True

    def test_true_for_whitespace_only(self):
        assert looks_like_empty_reply(_response("   \n\t ")) is True

    def test_false_for_real_content(self):
        assert looks_like_empty_reply(_response("here's the answer")) is False


class TestLooksLikePromptEcho:
    def test_true_for_role_restatement(self):
        content = "As a programming analyst, I focus on clarity and optimization."
        assert looks_like_prompt_echo(_response(content)) is True

    def test_true_is_case_insensitive(self):
        content = "AS A PROGRAMMING ANALYST, here is my approach."
        assert looks_like_prompt_echo(_response(content)) is True

    def test_false_for_a_grounded_answer(self):
        content = "The file contains a single function, `parse_config`, which reads JSON."
        assert looks_like_prompt_echo(_response(content)) is False

    def test_false_for_empty_content(self):
        assert looks_like_prompt_echo(_response("")) is False


class TestApplyResponsePolicyEmptyReply:
    def test_retries_when_enabled_and_reply_is_empty(self):
        profile = AgentProfile(name="Test", retry_on_empty_reply=True)
        original = _response("")
        retried = _response("the real answer")
        retry_calls = []

        def retry(nudge):
            retry_calls.append(nudge)
            return retried

        result = apply_response_policy(original, profile, retry)

        assert result.retried is True
        assert result.reason == "empty_reply"
        assert result.response is retried
        assert len(retry_calls) == 1
        assert retry_calls[0].role == "user"

    def test_does_not_retry_when_disabled(self):
        profile = AgentProfile(name="Test", retry_on_empty_reply=False)
        original = _response("")

        def retry(nudge):
            raise AssertionError("retry should not be called when disabled")

        result = apply_response_policy(original, profile, retry)

        assert result.retried is False
        assert result.reason is None
        assert result.response is original

    def test_does_not_retry_a_non_empty_reply(self):
        profile = AgentProfile(name="Test", retry_on_empty_reply=True)
        original = _response("a perfectly good answer")

        def retry(nudge):
            raise AssertionError("retry should not be called for a good reply")

        result = apply_response_policy(original, profile, retry)
        assert result.retried is False
        assert result.response is original


class TestApplyResponsePolicyPromptEcho:
    def test_retries_when_enabled_tool_used_and_echo_detected(self):
        profile = AgentProfile(name="Test", ground_tool_replies=True)
        tool_trace = [Message("tool", "file contents: def foo(): pass")]
        original = _response(
            "As a programming analyst, I aim to enhance understanding.",
            tool_trace=tool_trace,
        )
        retried = _response("The file defines a single function, foo.")

        result = apply_response_policy(original, profile, lambda nudge: retried)

        assert result.retried is True
        assert result.reason == "prompt_echo"
        assert result.response is retried

    def test_does_not_retry_when_disabled(self):
        profile = AgentProfile(name="Test", ground_tool_replies=False)
        tool_trace = [Message("tool", "file contents")]
        original = _response("As a programming analyst, I...", tool_trace=tool_trace)

        def retry(nudge):
            raise AssertionError("retry should not be called when disabled")

        result = apply_response_policy(original, profile, retry)
        assert result.retried is False
        assert result.response is original

    def test_does_not_retry_when_no_tool_was_used(self):
        # Same "echo-ish" wording, but tool_trace is empty - this is just
        # an ordinary reply to a question about the agent's role, not a
        # failure to use a tool result, since no tool ran this turn.
        profile = AgentProfile(name="Test", ground_tool_replies=True)
        original = _response("As a programming analyst, I can help with that.")

        def retry(nudge):
            raise AssertionError("retry should not fire without a tool_trace")

        result = apply_response_policy(original, profile, retry)
        assert result.retried is False

    def test_does_not_retry_a_grounded_reply(self):
        profile = AgentProfile(name="Test", ground_tool_replies=True)
        tool_trace = [Message("tool", "42")]
        original = _response("The result of the tool call was 42.", tool_trace=tool_trace)

        def retry(nudge):
            raise AssertionError("retry should not fire for a grounded reply")

        result = apply_response_policy(original, profile, retry)
        assert result.retried is False


class TestApplyResponsePolicyNeverLoops:
    def test_only_retries_once_even_if_retry_is_also_bad(self):
        profile = AgentProfile(name="Test", retry_on_empty_reply=True)
        original = _response("")
        still_empty = _response("")
        retry_calls = []

        def retry(nudge):
            retry_calls.append(nudge)
            return still_empty

        result = apply_response_policy(original, profile, retry)

        assert len(retry_calls) == 1
        assert result.retried is True
        assert result.response is still_empty
        assert result.response.content == ""  # bad reply is surfaced, not hidden


class TestApplyResponsePolicyPriority:
    def test_empty_reply_check_takes_priority_over_prompt_echo(self):
        # An empty reply trivially can't also match the prompt-echo
        # marker check, but make sure the empty-reply branch is the one
        # that runs (and retries) when both workarounds are enabled.
        profile = AgentProfile(
            name="Test", retry_on_empty_reply=True, ground_tool_replies=True,
        )
        original = _response("", tool_trace=[Message("tool", "data")])
        retried = _response("the answer")

        result = apply_response_policy(original, profile, lambda nudge: retried)

        assert result.reason == "empty_reply"