# Custos-API: Security and MCP

The security guard of Domus-AI: permissions, trusts, approvals, and sandboxing. Home to the MCPManager that gates which MCP servers and tools each model may use, and to the human-approval model for tools that cross the project trust boundary.

## MCPManager (`Custos.mcp`)
Reads `mcp/servers.json` (server definitions: `command`/`args`/`env`/`transport`/`description`) and `mcp/profiles/<Model>.json` (per-model `servers` + `allowed_tools`, with `"*"` wildcard support). Profile lookup is case-insensitive; configs are cached after first load.

- `enable(agent, server) -> bool` - enable a server for an agent; refuses servers not declared in the agent's profile, raises `MCPConfigError` for unknown servers
- `disable(agent, server) -> bool`
- `get_tools(model) -> {server: [tools]}` - enabled servers only, or all profile-declared servers if none are explicitly enabled yet (permissive default)
- `allow_tool(tool, model) -> bool` - exact match or per-server `"*"` wildcard

Errors: `MCPConfigError` (missing/malformed config), `ProfileNotFoundError` (no profile for the model).

## Confirmation (`mcp/confirmation.py`, used by the MCP tool servers)
Tools outside the trust boundary (e.g. `read_external_file`) must be approved by the human running the runtime - the `confirm` argument in a tools/call request comes from the model and proves nothing. Approval order: `DOMUS_APPROVED_EXTERNAL_READS` env allowlist (exact paths), then an interactive `[y/N]` prompt on the controlling TTY; anything else denies (`PermissionError`, fail-closed).

## Scaffolding (not yet enforced)
`Permission` / `Approval` dataclasses are placeholders for a future approval-workflow/sandboxing layer.

The MCP tool servers themselves live under `mcp/` (filesystem, git, fetch) - see `mcp/server.py` for the JSON-RPC stdio host.