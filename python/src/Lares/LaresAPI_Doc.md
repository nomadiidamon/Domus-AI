# Lares: Model Agents

The spirits of the home (Domus). Is responsible for persistent helpers, personalized agents, specialized agents and general assistants.

Lares is implemented as an agent layer over Faber messaging, Custos MCP permissions, and model-specific handling. An `Agent` combines a model profile, permission checks, supported MCP tool setup, and optional response corrections. 

**It does not yet provide persistent agent state or assignable roles.**

## Public API

The package exports:

- `Agent(model, profile=None, permissions=None)` for a model-bound chat facade.
- `AgentPermissions` for profile-aware MCP access checks.
- `AgentProfile`, `get_profile(model)`, `list_profiles()`, and `register_profile(profile)` for model capability/quirk metadata.

Profile names are case-insensitive. Unknown model names use `DEFAULT_PROFILE`, which assumes tool-call support but enables no response retries. Built-in profiles are registered for Mercury, Analyst, Vulcan, and Minerva. Profile fields include `supports_tool_calls`, `needs_fallback_tool_parsing`, `max_tool_iterations`, `ground_tool_replies`, `retry_on_empty_reply`, and `mcp_profile_name`.

## Agent permissions

`AgentPermissions(model, profile, manager=None)` wraps Custos for a particular agent. Use `has_mcp_profile()`, `tools_allowed()`, `get_tools()`, `allow_tool(tool_name)`, and `get_server_config(server)`. Tool use is denied when the profile says the model cannot call tools or when its MCP profile is missing. Custos remains the source of the server/tool allowlist.

## Tool lifecycle and chat

- `setup_tools() -> (clients, ollama_tools)` launches permitted supported servers and returns schemas formatted for Ollama. The current `Agent` implementation launches only the `filesystem` MCP server. A missing profile, unsupported model, empty allowlist, or server error degrades to chatting without advertised tools.
- `call_tool(tool_name, arguments) -> str` routes a call to the client that advertised the tool; names must come from this agent's `setup_tools()` result.
- `permitted_tool_names(ollama_tools)` returns the names to use for a dispatch-time allowlist check.
- `close_tools()` closes all MCP clients started by this agent. Call it in `finally` after the session.
- `chat(history, *, tools=None, tool_executor=None, **kwargs) -> ChatResponse` performs one turn through Faber and applies the enabled response policy. The Ollama server must be running; this method does not start it.

`Agent.chat()` always calls Faber with `record=False`, including retries. The caller owns memory recording. Passing `record=` to `Agent.chat()` raises `TypeError`. A profile can trigger at most one corrective retry for an empty reply or a likely role/prompt echo after tool use; these checks are heuristics, not a guarantee of answer quality.

```python
from Faber import Message, start_ollama
from Lares import Agent

start_ollama()
agent = Agent("Mercury")
clients, tools = agent.setup_tools()
history = [Message("user", "Read the project README and summarize it")]
try:
	response = agent.chat(
		history,
		tools=tools,
		tool_executor=lambda name, arguments: agent.call_tool(name, arguments),
	)
	history.extend(response.tool_trace)
	history.append(response.message)
	print(response.content)
finally:
	agent.close_tools()
```

When retaining turns across calls, append the returned `tool_trace` and final `message` to the caller's history. The tool trace covers only the final attempt if a response-policy retry occurred.

## Response policy

`Lares.response_policy.apply_response_policy(response, profile, retry)` returns a `ResponsePolicyResult` with `response`, `retried`, and `reason`. `looks_like_empty_reply()` checks for blank final text; `looks_like_prompt_echo()` checks a small set of role-description phrases and is relevant only after a tool call. The retry callback receives a synthetic user `Message` nudge and is called at most once.

The built-in Analyst profile enables both empty-reply retry and tool-reply grounding. Mercury records a fallback-tool-parsing expectation; Faber performs parsing. Vulcan and Minerva do not advertise tools because their declared bases lack native tool-call support.

## Not implemented

`Lares.roles` and `Lares.persistence` are placeholders. Roles/personas and durable agent-specific state are not currently runtime features; conversation memory belongs to [Mentis](../Mentis/MentisAPI_Doc.md).