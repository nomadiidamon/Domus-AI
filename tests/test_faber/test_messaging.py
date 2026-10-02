"""
Tests for Faber/messaging.py

chat()/generate() talk to Ollama over HTTP via urllib; every test here
mocks urllib.request.urlopen so no real server or network is involved.
Conversation recording into a bound RuntimeContext's AIMemory is tested
with a MagicMock context (the real context is covered by Mentis tests).

The last class, TestLiveModelMessaging, is the e2e test: it is skipped
unless a live Ollama server is reachable, and is additionally marked
'e2e' so it can be deselected wholesale with -m "not e2e".
"""

import io
import json
import shutil
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from Faber.messaging import (
    DEFAULT_BASE_URL,
    ChatResponse,
    Message,
    chat,
    generate,
)
from Faber.models import set_context

pytestmark = pytest.mark.faber


def _http_response(payload: dict):
    """Build a context-manager fake for urllib.request.urlopen."""
    body = json.dumps(payload).encode("utf-8")
    response = MagicMock()
    response.read.return_value = body
    response.__enter__ = lambda s: s
    response.__exit__ = MagicMock(return_value=False)
    return response


class TestMessage:
    def test_to_dict(self):
        assert Message("user", "hello").to_dict() == {"role": "user", "content": "hello"}


class TestChatResponse:
    def test_content_is_stripped(self):
        response = ChatResponse(model="m", message=Message("assistant", "  reply \n"))
        assert response.content == "reply"


class TestChat:
    def test_posts_messages_to_chat_endpoint(self):
        payload = {
            "model": "mercury",
            "message": {"role": "assistant", "content": "hi there"},
            "done": True,
        }
        with patch("urllib.request.urlopen", return_value=_http_response(payload)) as mock_open:
            response = chat("mercury", [Message("user", "say hi")])

        request = mock_open.call_args[0][0]
        assert request.full_url == f"{DEFAULT_BASE_URL}/api/chat"
        body = json.loads(request.data.decode("utf-8"))
        assert body == {
            "model": "mercury",
            "messages": [{"role": "user", "content": "say hi"}],
            "stream": False,
        }
        assert response.content == "hi there"
        assert response.done is True

    def test_raises_on_ollama_error_payload(self):
        payload = {"error": "model 'ghost' not found"}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            with pytest.raises(RuntimeError, match="ghost"):
                chat("ghost", [Message("user", "hi")])

    def test_raises_when_server_unreachable(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            with pytest.raises(RuntimeError, match="unreachable"):
                chat("mercury", [Message("user", "hi")])


class TestChatFallbackToolCallParsing:
    """
    Some models (qwen2.5-coder-based ones, e.g. Mercury) don't emit
    Ollama's native tool_calls field - they describe the call as JSON
    text in `content` instead, in one of a few shapes (bare JSON object,
    ```json fenced block, <tool_call> tag, or a JSON array of calls).
    chat() should recover these into response.message.tool_calls exactly
    as if the model had used the native field, so the rest of the tool
    loop (and Janus.main's tool_executor) doesn't need to know the
    difference. This fallback only kicks in when tools were actually
    offered on the request - plain conversational JSON in a reply to a
    tool-less chat must never be misread as a tool call.
    """

    _TOOLS = [{"type": "function", "function": {
        "name": "read_file", "description": "", "parameters": {}}}]

    def _payload(self, content: str) -> dict:
        return {"model": "mercury",
                "message": {"role": "assistant", "content": content},
                "done": True}

    def test_recovers_bare_json_object(self):
        content = '{"name": "read_file", "arguments": {"path": "a.txt"}}'
        with patch("urllib.request.urlopen", return_value=_http_response(self._payload(content))):
            response = chat("mercury", [Message("user", "read a.txt")], tools=self._TOOLS)

        assert response.message.tool_calls == [
            {"function": {"name": "read_file", "arguments": {"path": "a.txt"}}}
        ]
        # The recovered JSON shouldn't also be surfaced as the reply text.
        assert response.content == ""

    def test_recovers_json_fenced_in_code_block(self):
        content = (
            "Sure, I'll read that file.\n"
            "```json\n"
            '{"name": "read_file", "arguments": {"path": "a.txt"}}\n'
            "```"
        )
        with patch("urllib.request.urlopen", return_value=_http_response(self._payload(content))):
            response = chat("mercury", [Message("user", "read a.txt")], tools=self._TOOLS)

        assert response.message.tool_calls == [
            {"function": {"name": "read_file", "arguments": {"path": "a.txt"}}}
        ]

    def test_recovers_tool_call_tag(self):
        content = '<tool_call>{"name": "read_file", "arguments": {"path": "a.txt"}}</tool_call>'
        with patch("urllib.request.urlopen", return_value=_http_response(self._payload(content))):
            response = chat("mercury", [Message("user", "read a.txt")], tools=self._TOOLS)

        assert response.message.tool_calls == [
            {"function": {"name": "read_file", "arguments": {"path": "a.txt"}}}
        ]

    def test_recovers_json_array_of_calls(self):
        content = (
            '[{"name": "read_file", "arguments": {"path": "a.txt"}}, '
            '{"name": "read_file", "arguments": {"path": "b.txt"}}]'
        )
        with patch("urllib.request.urlopen", return_value=_http_response(self._payload(content))):
            response = chat("mercury", [Message("user", "read both files")], tools=self._TOOLS)

        assert response.message.tool_calls == [
            {"function": {"name": "read_file", "arguments": {"path": "a.txt"}}},
            {"function": {"name": "read_file", "arguments": {"path": "b.txt"}}},
        ]

    def test_native_tool_calls_take_priority_over_content(self):
        """If Ollama did populate tool_calls natively, the fallback parser
        must not run at all - even if content happens to contain JSON."""
        payload = {
            "model": "mercury",
            "message": {
                "role": "assistant",
                "content": '{"not": "a real call, just noise"}',
                "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "x"}}}],
            },
            "done": True,
        }
        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            response = chat("mercury", [Message("user", "hi")], tools=self._TOOLS)

        assert response.message.tool_calls == [
            {"function": {"name": "read_file", "arguments": {"path": "x"}}}
        ]
        # content is left untouched when no fallback parse happened
        assert response.message.content == '{"not": "a real call, just noise"}'

    def test_no_fallback_when_tools_not_offered(self):
        """Plain chat (no tools= passed) must never have ordinary text
        misread as a tool call, even if it happens to look like JSON."""
        content = '{"name": "read_file", "arguments": {"path": "a.txt"}}'
        with patch("urllib.request.urlopen", return_value=_http_response(self._payload(content))):
            response = chat("mercury", [Message("user", "hi")])

        assert response.message.tool_calls is None
        assert response.content == content

    def test_ordinary_reply_with_tools_offered_is_left_alone(self):
        """A normal non-JSON reply to a tools-enabled chat must pass
        through unchanged - the fallback parser should find nothing to
        recover and leave content/tool_calls as-is."""
        content = "The capital of France is Paris."
        with patch("urllib.request.urlopen", return_value=_http_response(self._payload(content))):
            response = chat("mercury", [Message("user", "capital of France?")], tools=self._TOOLS)

        assert response.message.tool_calls is None
        assert response.content == content


class TestChatRecording:
    def test_records_exchange_into_bound_context(self):
        payload = {"model": "mercury",
                   "message": {"role": "assistant", "content": "pong"},
                   "done": True}
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            chat("mercury", [Message("user", "ping")])

        calls = fake_context.update_ai_memory.call_args_list
        assert calls[0][0][:2] == ("user", "ping")
        assert calls[1][0][:2] == ("assistant", "pong")
        assert calls[1][1]["metadata"] == {"model": "mercury"}

    def test_record_false_skips_context(self):
        payload = {"model": "mercury",
                   "message": {"role": "assistant", "content": "pong"},
                   "done": True}
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            chat("mercury", [Message("user", "ping")], record=False)

        fake_context.update_ai_memory.assert_not_called()

    def test_no_context_bound_does_not_crash(self):
        # Root conftest's _reset_faber_models_context guarantees _context is None.
        payload = {"model": "mercury",
                   "message": {"role": "assistant", "content": "pong"},
                   "done": True}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            chat("mercury", [Message("user", "ping")])  # must not raise


class TestMessagingBusEvents:
    """chat()/generate() must publish MESSAGE_SENT for every outbound
    message and MESSAGE_RECEIVED for the model's reply, so subscribers
    (e.g. a UI, or a 'condense the conversation' listener) can observe
    conversation traffic on the bus."""

    @pytest.fixture
    def bus(self):
        import Mercurius
        bus = Mercurius.initialize_bus()
        yield bus
        Mercurius.shutdown_bus(drain=False)

    def test_chat_publishes_sent_and_received(self, bus):
        import Mercurius
        sent, received = [], []
        bus.subscribe(Mercurius.EventType.MESSAGE_SENT, sent.append)
        bus.subscribe(Mercurius.EventType.MESSAGE_RECEIVED, received.append)

        payload = {"model": "mercury",
                   "message": {"role": "assistant", "content": "pong"},
                   "done": True}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            chat("mercury",
                 [Message("system", "be terse"), Message("user", "ping")],
                 record=False)

        bus.stop(drain=True)

        assert [e.payload["role"] for e in sent] == ["system", "user"]
        assert all(e.source == "faber" and e.payload["model"] == "mercury" for e in sent)
        assert len(received) == 1
        assert received[0].payload["content"] == "pong"

    def test_generate_publishes_sent_and_received(self, bus):
        import Mercurius
        sent, received = [], []
        bus.subscribe(Mercurius.EventType.MESSAGE_SENT, sent.append)
        bus.subscribe(Mercurius.EventType.MESSAGE_RECEIVED, received.append)

        payload = {"model": "mercury", "response": "42", "done": True}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            generate("mercury", "the question", record=False)

        bus.stop(drain=True)

        assert len(sent) == 1 and sent[0].payload["content"] == "the question"
        assert len(received) == 1 and received[0].payload["content"] == "42"

    def test_no_events_published_on_error(self, bus):
        import Mercurius
        received = []
        bus.subscribe(Mercurius.EventType.MESSAGE_RECEIVED, received.append)

        with patch("urllib.request.urlopen",
                   return_value=_http_response({"error": "boom"})):
            with pytest.raises(RuntimeError):
                generate("mercury", "ping", record=False)

        bus.stop(drain=True)
        assert received == []

    def test_no_bus_no_crash(self):
        # No bus initialized: publishing must silently no-op.
        payload = {"model": "mercury",
                   "message": {"role": "assistant", "content": "pong"},
                   "done": True}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            chat("mercury", [Message("user", "ping")], record=False)


class TestGenerate:
    def test_posts_prompt_to_generate_endpoint(self):
        payload = {"model": "mercury", "response": "42", "done": True,
                   "total_duration": 123, "eval_count": 3}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)) as mock_open:
            response = generate("mercury", "what is the answer?")

        request = mock_open.call_args[0][0]
        assert request.full_url == f"{DEFAULT_BASE_URL}/api/generate"
        body = json.loads(request.data.decode("utf-8"))
        assert body == {"model": "mercury", "prompt": "what is the answer?", "stream": False}
        assert response.content == "42"
        assert response.eval_count == 3

    def test_includes_system_prompt_when_given(self):
        payload = {"model": "mercury", "response": "ok", "done": True}
        with patch("urllib.request.urlopen", return_value=_http_response(payload)) as mock_open:
            generate("mercury", "ping", system="be terse")

        body = json.loads(mock_open.call_args[0][0].data.decode("utf-8"))
        assert body["system"] == "be terse"

    def test_raises_on_error_payload(self):
        with patch("urllib.request.urlopen", return_value=_http_response({"error": "nope"})):
            with pytest.raises(RuntimeError, match="nope"):
                generate("mercury", "ping")

    def test_records_prompt_and_reply_into_bound_context(self):
        payload = {"model": "mercury", "response": "pong", "done": True}
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("urllib.request.urlopen", return_value=_http_response(payload)):
            generate("mercury", "ping")

        calls = fake_context.update_ai_memory.call_args_list
        assert calls[0][0][:2] == ("user", "ping")
        assert calls[1][0][:2] == ("assistant", "pong")


@pytest.mark.e2e
class TestLiveModelMessaging:
    """
    End-to-end: requires a live Ollama server and a small local model.

    Skipped automatically when no server is reachable. Run explicitly with:
        pytest -m e2e
    The model is pulled on demand (ollama pull) if missing.
    """

    LIVE_MODEL = "qwen2.5:0.5b"

    @pytest.fixture(scope="class")
    @classmethod
    def live_server(cls):
        try:
            with urllib.request.urlopen(f"{DEFAULT_BASE_URL}/api/tags", timeout=3):
                pass
        except Exception:
            pytest.skip("no live Ollama server reachable - skipping e2e messaging tests")
        return DEFAULT_BASE_URL

    def test_simple_prompt_gets_intended_answer(self, live_server):
        from Faber.models import pull_model, list_models

        if not any(m["name"].startswith(self.LIVE_MODEL) for m in list_models()):
            pull_model(self.LIVE_MODEL)

        response = generate(
            self.LIVE_MODEL,
            "Reply with exactly the single word: pong",
            system="You are a test harness. Always follow instructions literally.",
            timeout=120,
            record=False,
        )

        assert response.done is True
        assert "pong" in response.content.lower()

    def test_chat_conversation_round_trip(self, live_server):
        from Faber.models import pull_model, list_models

        if not any(m["name"].startswith(self.LIVE_MODEL) for m in list_models()):
            pull_model(self.LIVE_MODEL)

        response = chat(
            self.LIVE_MODEL,
            [Message("user", "What is 2+2? Answer with just the number.")],
            timeout=120,
            record=False,
        )

        assert response.done is True
        assert "4" in response.content