"""
Messaging to and from models via Ollama's HTTP API (stdlib urllib only).

@todo: Create a chat function that allows for thinking controls
@todo: Create a chat function that allows for streaming responses
@todo: Create an ask function that allows tool calls
@todo: Create an ask function that supports streaming responses
"""

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Faber.models import _get_context

logger = logging.getLogger(__name__)

## @todo: Read the URL from the configuration instead of hardcoding it.
DEFAULT_BASE_URL = "http://localhost:11434"


@dataclass
class Message:
    """A single chat message. Role is 'system', 'user', 'assistant', or 'tool'.

    tool_name:  set on an outgoing role="tool" message - identifies which
                tool this result came from (Ollama's convention).
    tool_calls: set on an incoming role="assistant" message when the model
                requested tool calls instead of (or alongside) replying
                directly. Each entry is Ollama's raw
                {"function": {"name": str, "arguments": dict}} shape.
    """
    role: str
    content: str
    tool_name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_name is not None:
            d["tool_name"] = self.tool_name
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class ChatResponse:
    """Structured reply from the model.

    tool_trace holds every intermediate message generated while resolving
    tool calls (each assistant turn that requested tools, and each
    resulting role="tool" message), in order. Empty when tools weren't
    used or the model didn't call any. `message`/`content` always refer
    to the final, non-tool-call reply.
    """
    model: str
    message: Message
    done: bool = True
    total_duration_ns: Optional[int] = None
    eval_count: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    tool_trace: List[Message] = field(default_factory=list)

    @property
    def content(self) -> str:
        """The model's reply text, stripped of surrounding whitespace."""
        return self.message.content.strip()


def _post_json(url: str, body: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Ollama server unreachable at {url} - start it with 'ollama serve' ({e})"
        ) from e



# Matches a fenced ```json ... ``` or bare ``` ... ``` block, to unwrap a
# tool call some models (qwen2.5-coder in particular) wrap in a code fence
# instead of emitting Ollama's native tool_calls.
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
 
# Matches a <tool_call>...</tool_call> wrapper (Hermes/Qwen convention) -
# some templates emit this as literal text instead of a native tool call.
_TOOL_CALL_TAG_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
 
 
def _coerce_tool_call_dict(obj: Any) -> Optional[Dict[str, Any]]:
    """If obj looks like a single tool-call object (has a tool/function name
    plus arguments, under any of the common key spellings), return it
    reshaped to Ollama's {"function": {"name", "arguments"}} shape.
    Returns None if obj doesn't look like a tool call at all."""
    if not isinstance(obj, dict):
        return None
 
    # Already Ollama-shaped: {"function": {"name": ..., "arguments": ...}}
    if isinstance(obj.get("function"), dict) and "name" in obj["function"]:
        function = obj["function"]
        return {"function": {
            "name": function["name"],
            "arguments": function.get("arguments") or {},
        }}
 
    name = obj.get("name") or obj.get("tool") or obj.get("tool_name")
    if not name:
        return None
    arguments = obj.get("arguments") or obj.get("parameters") or obj.get("input") or {}
    if not isinstance(arguments, dict):
        return None
    return {"function": {"name": name, "arguments": arguments}}
 
 
def _extract_fallback_tool_calls(content: str) -> List[Dict[str, Any]]:
    """
    Best-effort recovery of tool calls a model described as JSON text in
    `content` instead of Ollama's native tool_calls field - seen with
    qwen2.5-coder-based models (e.g. Mercury), which frequently emit
    {"name": ..., "arguments": ...}, a ```json ... ``` fenced version of
    the same, or a <tool_call>...</tool_call>-wrapped version, rather
    than populating the structured field.
 
    Tries, in order: a <tool_call> tag, a fenced code block, then the
    raw content itself. Accepts either a single tool-call object or a
    JSON array of them. Returns [] if nothing in `content` looks like a
    tool call - callers should treat that as "no tool calls", not an error.
    """
    if not content or not content.strip():
        return []
 
    candidates = []
    tag_match = _TOOL_CALL_TAG_RE.search(content)
    if tag_match:
        candidates.append(tag_match.group(1))
    fence_match = _CODE_FENCE_RE.search(content)
    if fence_match:
        candidates.append(fence_match.group(1))
    candidates.append(content)
 
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
 
        items = parsed if isinstance(parsed, list) else [parsed]
        calls = [c for c in (_coerce_tool_call_dict(item) for item in items) if c is not None]
        if calls:
            return calls
 
    return []


def _parse_chat_response(payload: dict, model: str,
                          tools_offered: bool = False) -> ChatResponse:
    raw_message = payload.get("message") or {}
    content = raw_message.get("content", "")
    tool_calls = raw_message.get("tool_calls") or None
 
    if tool_calls is None and tools_offered:
        fallback = _extract_fallback_tool_calls(content)
        if fallback:
            logger.info(
                "Model '%s' returned tool call(s) as text instead of native "
                "tool_calls - recovered %d via fallback parsing", model, len(fallback),
            )
            tool_calls = fallback
            # The call itself is consumed by the fallback parse - don't
            # also feed the model's own JSON-as-text back to it/the user
            # as if it were a normal reply.
            content = ""
 
    return ChatResponse(
        model=payload.get("model", model),
        message=Message(
            role=raw_message.get("role", "assistant"),
            content=content,
            tool_calls=tool_calls,
        ),
        done=payload.get("done", True),
        total_duration_ns=payload.get("total_duration"),
        eval_count=payload.get("eval_count"),
        raw=payload,
    )


def _record_conversation(model: str, messages: List[Message], reply: Message) -> None:
    """Mirror the exchange into Mentis AIMemory when a context is bound."""
    context = _get_context()
    if context is None:
        return
    for message in messages:
        context.update_ai_memory(message.role, message.content)
    context.update_ai_memory(reply.role, reply.content,
                             metadata={"model": model})


def _record_tool_trace(model: str, tool_trace: List[Message]) -> None:
    """Mirror intermediate tool-call/tool-result turns into AIMemory.

    Separate from _record_conversation because these messages carry a
    tool_name (for role="tool" entries) that belongs in metadata, not
    alongside the user/assistant turns _record_conversation handles.
    """
    if not tool_trace:
        return
    context = _get_context()
    if context is None:
        return
    for message in tool_trace:
        metadata = {"model": model}
        if message.tool_name:
            metadata["tool_name"] = message.tool_name
        context.update_ai_memory(message.role, message.content, metadata=metadata)

def _publish(event_type, model: str, message: Message) -> None:
    """Publish a messaging event to the Mercurius bus (no-op without one)."""
    try:
        from Mercurius import publish_event
        publish_event(
            event_type,
            source="faber",
            payload={
                "model": model,
                "role": message.role,
                "content": message.content,
            },
        )
    except Exception:
        logger.debug("Mercurius bus unavailable; messaging event not published",
                     exc_info=True)

## @todo: Add MAX_TOOL_ITERATIONS to the configuration options.
MAX_TOOL_ITERATIONS = 12


def _chat_once(model: str, messages: List[Message], tools: Optional[List[Dict[str, Any]]],
                base_url: str, timeout: int) -> ChatResponse:
    """Single, non-looping call to /api/chat. Used by chat() both for the
    first turn and for each follow-up turn after resolving tool calls."""
    body: Dict[str, Any] = {
        "model": model,
        "messages": [m.to_dict() for m in messages],
        "stream": False,
    }
    if tools:
        body["tools"] = tools

    from Mercurius import EventType
    for message in messages:
        _publish(EventType.MESSAGE_SENT, model, message)

    try:
        payload = _post_json(f"{base_url}/api/chat", body, timeout)
    except RuntimeError as e:
        _publish(EventType.ERROR, model, Message("system", str(e)))
        raise

    if "error" in payload:
        _publish(EventType.ERROR, model,
                 Message("system", f"chat failed: {payload['error']}"))
        raise RuntimeError(f"Ollama chat failed for model '{model}': {payload['error']}")

    response = _parse_chat_response(payload, model, tools_offered=bool(tools))
    _publish(EventType.MESSAGE_RECEIVED, model, response.message)
    return response


def chat(
    model: str,
    messages: List[Message],
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 300,
    record: bool = True,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_executor: Optional[Any] = None,
    max_tool_iterations: int = MAX_TOOL_ITERATIONS,
) -> ChatResponse:
    """
    Send a conversation to a model and return its reply.

    When a RuntimeContext is bound (Faber.models.set_context) and record is
    True, the outgoing messages and the final reply (plus any tool_trace)
    are appended to AIMemory.

    Tool calling (optional): pass `tools` (Ollama-format tool schemas, see
    Custos.mcp.mcp_tools_to_ollama_tools) and `tool_executor` - a callable
    `(tool_name: str, arguments: dict) -> str` that actually runs the tool
    (e.g. Custos.mcp_client.MCPClient.call_tool) and returns its text
    result, raising on failure. When the model's reply includes
    `tool_calls`, chat() runs each through tool_executor, feeds the
    results back as role="tool" messages, and re-calls the model - up to
    max_tool_iterations rounds - until it replies with plain content
    instead of more tool calls. If tool_executor is not given, tools are
    still advertised to the model but any tool_calls in the reply are
    left for the caller to resolve (response.message.tool_calls).

    Raises RuntimeError if the server is unreachable or returns an error.
    MCPClientError (a RuntimeError subclass) propagates uncaught if a
    tool_executor call fails - the exchange up to that point is not
    recorded, mirroring how a network failure mid-chat isn't recorded.
    """
    working_messages = list(messages)
    tool_trace: List[Message] = []

    response = _chat_once(model, working_messages, tools, base_url, timeout)

    iterations = 0
    while (
        tool_executor is not None
        and response.message.tool_calls
        and iterations < max_tool_iterations
    ):
        iterations += 1
        assistant_turn = response.message
        working_messages.append(assistant_turn)
        tool_trace.append(assistant_turn)

        for call in assistant_turn.tool_calls:
            function = call.get("function", {})
            tool_name = function.get("name", "")
            arguments = function.get("arguments") or {}
            try:
                result_text = tool_executor(tool_name, arguments)
            except Exception as e:
                result_text = f"Error: {e}"
                logger.warning("Tool '%s' failed during chat: %s", tool_name, e)

            tool_message = Message("tool", result_text, tool_name=tool_name)
            working_messages.append(tool_message)
            tool_trace.append(tool_message)

        response = _chat_once(model, working_messages, tools, base_url, timeout)

    if iterations >= max_tool_iterations and response.message.tool_calls:
        logger.warning(
            "Chat with '%s' hit max_tool_iterations (%d) with tool calls still "
            "pending - returning the model's last tool-call turn as-is",
            model, max_tool_iterations,
        )

    response.tool_trace = tool_trace

    if record:
        _record_conversation(model, messages, response.message)
        _record_tool_trace(model, tool_trace)
    
    logger.info("Chat with '%s' completed (%s eval tokens, %d tool round(s))",
                model, response.eval_count, iterations)
    return response


def generate(
    model: str,
    prompt: str,
    *,
    system: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 300,
    record: bool = True,
) -> ChatResponse:
    """
    Send a single prompt to a model and return its reply.

    Convenience wrapper over chat(): builds the message list from prompt
    (and optional system prompt) and adapts the /api/generate response
    into the same ChatResponse shape.

    @todo: Allow passing Ollama `options` (temperature, seed, num_predict)
    """
    body: Dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
    if system is not None:
        body["system"] = system

    from Mercurius import EventType
    outbound = [Message("user", prompt)]
    if system is not None:
        outbound.insert(0, Message("system", system))
    for message in outbound:
        _publish(EventType.MESSAGE_SENT, model, message)

    try:
        payload = _post_json(f"{base_url}/api/generate", body, timeout)
    except RuntimeError as e:
        _publish(EventType.ERROR, model, Message("system", str(e)))
        raise

    if "error" in payload:
        _publish(EventType.ERROR, model,
                 Message("system", f"generate failed: {payload['error']}"))
        raise RuntimeError(f"Ollama generate failed for model '{model}': {payload['error']}")

    response = ChatResponse(
        model=payload.get("model", model),
        message=Message(role="assistant", content=payload.get("response", "")),
        done=payload.get("done", True),
        total_duration_ns=payload.get("total_duration"),
        eval_count=payload.get("eval_count"),
        raw=payload,
    )

    _publish(EventType.MESSAGE_RECEIVED, model, response.message)

    if record:
        _record_conversation(model, outbound, response.message)

    logger.info("Generate with '%s' completed (%s eval tokens)", model, response.eval_count)
    return response
