# Custos: MCP Permissions and Client

The security guard of Domus-AI. Custos loads per-model MCP permissions and provides the stdio JSON-RPC client used to launch and call local MCP servers. The server implementations and bundled configuration are in the sibling `DomusMCP` package, not in `Custos`.

## Configuration

By default, `MCPManager` reads the bundled `DomusMCP/servers.json` and `DomusMCP/profiles/<Model>.json` (resolved through `Janus.paths.get_mcp_path()`). It can also be given an explicit `mcp_dir` for tests or custom configurations.

`servers.json` has a top-level `servers` object. Each entry supplies a subprocess `command`, `args`, optional `env`, `transport`, and `description`. A model profile declares `model`, `servers`, and per-server `allowed_tools`; an allowed-tools list may contain `"*"`. Profile filenames are matched case-insensitively. Loaded server and profile JSON is cached for the manager's lifetime.

The bundled server definitions are `filesystem`, `git`, and `fetch`. Profiles are maintained separately for the bundled models. Custos can inspect all three, but Lares currently launches only the `filesystem` server for agent chat.

## MCPManager (`Custos.mcp`)

- `MCPManager(mcp_dir=None)` creates a manager; files are loaded on first access.
- `enable(agent, server) -> bool` enables a server in memory for the current manager if it exists and is declared in that agent's profile. Unknown server names raise `MCPConfigError`; undeclared servers return `False`.
- `disable(agent, server) -> bool` removes a session enablement and reports whether it was enabled.
- `get_tools(model) -> dict[str, list[str]]` returns the profile's tool allowlist grouped by active server. Until `enable()` has been called for a model, all profile-declared servers are returned. Once any server is explicitly enabled for that model, only the enabled declared servers are returned.
- `allow_tool(tool, model) -> bool` checks exact tool names or a server's `"*"` grant.
- `get_server_config(server) -> dict` returns the configured server entry.
- `filter_tools_for_model(live_tools, server, model, manager)` filters live `tools/list` results to the profile's allowlist.
- `mcp_tools_to_ollama_tools(mcp_tools)` converts MCP tool schemas to Ollama chat tool schemas.

Missing or malformed server/profile data raises `MCPConfigError`; a missing model profile raises its subclass `ProfileNotFoundError`.

## MCPClient (`Custos.mcp_client`)

`MCPClient(server_name, server_config, cwd=None, env=None)` launches one configured local server over stdio and performs the MCP initialize handshake. It exposes `start(timeout=10)`, `list_tools(refresh=False)`, `call_tool(name, arguments, timeout=60) -> str`, `close()`, and `is_running`. Use it as a context manager to guarantee cleanup. Protocol, launch, and tool errors raise `MCPClientError`.

```python
from Custos import MCPClient, MCPManager

manager = MCPManager()
with MCPClient("filesystem", manager.get_server_config("filesystem")) as client:
	allowed = manager.get_tools("Mercury").get("filesystem", [])
	tools = [tool for tool in client.list_tools() if "*" in allowed or tool["name"] in allowed]
	print(tools)
```

The example lists only allowed live tool definitions; permission checks should also be enforced when dispatching a tool call.

## Human confirmation

Sensitive filesystem operations use `DomusMCP.confirmation.require_user_approval()`. A path is approved first if its exact string appears in the `DOMUS_APPROVED_EXTERNAL_READS` environment variable (paths separated using the platform path separator); otherwise the server asks the human for confirmation on `/dev/tty` when available, falling back to stdin in environments without it. The MCP request's `confirm` field is not trusted. An unreadable prompt, EOF, or a negative answer denies access with `PermissionError`.

## Not implemented

`Permission` and `Approval` are scaffolding dataclasses; they do not provide a general policy engine or sandbox. Confirmation currently protects specific trust-boundary operations rather than every MCP tool. See [DomusMCP](../DomusMCP) for server implementations and tool behavior.