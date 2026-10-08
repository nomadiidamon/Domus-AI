# DomusMCP: MCP Servers and Tools

DomusMCP provides local Model Context Protocol (MCP) servers for project files, Git operations, and HTTP(S) fetching. Each server runs as a separate Python subprocess over stdio. The available servers are registered in [`servers.json`](servers.json); model-specific access policies are in `profiles/` and are enforced by Custos.

## Starting a server

Run a server from an environment where the Domus-AI `src/` packages are importable:

| Server | Command | Purpose |
| --- | --- | --- |
| `filesystem` | `python -m DomusMCP.filesystem` | Read and modify files under the host project root. |
| `git` | `python -m DomusMCP.git` | Inspect and modify the host repository's Git state. |
| `fetch` | `python -m DomusMCP.fetch` | Fetch text from HTTP(S) URLs. |

`servers.json` supplies `command`, `args`, optional `env`, `transport`, and `description` for each server. The host project root is read from `LOCAL_AI_RUNTIME_HOST`; standalone use falls back to the process working directory. Filesystem paths are resolved against that root and rejected if they escape it. Git commands run with that root as their working directory.

## MCP transport

`DomusMCP.server.ToolServer` reads one JSON-RPC 2.0 request per input line and writes responses to stdout. Tool output is returned as text content. The host implements `initialize` (protocol version `2024-11-05`), `notifications/initialized`, `ping`, `tools/list`, and `tools/call`. Notifications receive no response. Tool exceptions are returned as text results with `isError: true`; unknown methods return `-32601`, and unknown tool names return `-32602`.

Each tool module exports a `TOOL` metadata object containing its MCP name, description, and JSON input schema, plus `call(arguments)`. A server discovers these modules from its package when started.

## Tool reference

### Fetch

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `fetch` | Required `url` (HTTP or HTTPS); optional `max_chars` (default `20000`). | Fetches with a 15-second timeout and returns the response body decoded as UTF-8. The output is truncated at `max_chars` and marked when truncated. |

### Filesystem

All paths for these tools are relative to the host project root unless noted. `read_file` and `read_external_file` accept an optional `max_chars` limit.

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `read_file` | Required `path`; optional `max_chars`. | Reads a text file under the project root. |
| `list_directory` | Optional `path` (defaults to `.`). | Lists sorted entries; directory names end in `/`. |
| `search_files` | Required `pattern`; optional `path` (defaults to `.`). | Recursively finds files whose names contain the case-insensitive substring. Returns `(no matches)` when empty. |
| `write_file` | Required `path`, `content`. | Writes text under the project root, creating parent directories when needed. |
| `edit_file` | Required `path`, `start_line`, `end_line`, `content`. | Replaces an inclusive, 1-indexed line range in an existing file. |
| `read_external_file` | Required absolute `path`; optional `max_chars`. | Reads a text file outside the project root, subject to human approval. |

`read_external_file` is the only confirmation-gated tool. The human can approve a request at its interactive prompt, or pre-approve exact paths in `DOMUS_APPROVED_EXTERNAL_READS`, separated using the platform path separator (`;` on Windows, `:` on Unix). A client-supplied confirmation argument is not used as approval. If approval cannot be obtained, the operation is denied.

### Git

Git tools operate in the host project root and fail with an error result if the Git command fails. Each command has a 30-second timeout.

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `git_status` | None. | Shows short branch and working-tree status. |
| `git_diff` | Optional `staged` (boolean), `ref` (string), and `path` (string). | Shows a diff; defaults to unstaged changes. `staged: true` selects staged changes. |
| `git_log` | Optional `count` (default `10`). | Shows the requested number of recent commits in one-line format. |
| `git_add` | Required `paths` (array of strings). | Stages the supplied paths; use `["."]` to stage the whole working tree. |
| `git_commit` | Required `message`. | Commits currently staged changes. |

## Access profiles

Profiles are keyed by model name and list enabled servers plus allowed tool names for each server. `"*"` allows all tools from that server. Profile filenames are matched case-insensitively by Custos.

| Profile | Enabled servers | Access summary |
| --- | --- | --- |
| `Analyst` | `filesystem`, `fetch` | File reads and writes, including external reads; web fetch. |
| `Mercury` | `filesystem`, `git` | Project file tools and all listed Git tools. |
| `Minerva` | `filesystem` | Read-only project tools: read, list, and search. |
| `Vulcan` | `filesystem`, `git`, `fetch` | All tools on those servers. |

See [Custos](../Custos/CustosAPI_Doc.md) for profile loading and tool permission checks. Profile permissions determine which tools clients may use; they do not change the server tool implementations.


