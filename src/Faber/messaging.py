# Messaging to and from models via Ollama's HTTP API (stdlib urllib only).
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Faber.models import _get_context

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"


@dataclass
class Message:
    """A single chat message. Role is 'system', 'user', or 'assistant'."""
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    """Structured reply from the model."""
    model: str
    message: Message
    done: bool = True
    total_duration_ns: Optional[int] = None
    eval_count: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

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


def _parse_chat_response(payload: dict, model: str) -> ChatResponse:
    raw_message = payload.get("message") or {}
    return ChatResponse(
        model=payload.get("model", model),
        message=Message(role=raw_message.get("role", "assistant"),
                        content=raw_message.get("content", "")),
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


def chat(
    model: str,
    messages: List[Message],
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 300,
    record: bool = True,
) -> ChatResponse:
    """
    Send a conversation to a model and return its reply.

    When a RuntimeContext is bound (Faber.models.set_context) and record is
    True, the outgoing messages and the reply are appended to AIMemory.

    Raises RuntimeError if the server is unreachable or returns an error.
    """
    body = {
        "model": model,
        "messages": [m.to_dict() for m in messages],
        "stream": False,
    }

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

    response = _parse_chat_response(payload, model)

    _publish(EventType.MESSAGE_RECEIVED, model, response.message)

    if record:
        _record_conversation(model, messages, response.message)

    logger.info("Chat with '%s' completed (%s eval tokens)", model, response.eval_count)
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
