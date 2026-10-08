"""
Custos.mcp_client - stdio client for local MCP tool servers.

MCPManager (mcp.py) answers "is this tool allowed?" from static config.
This module is the other half: it actually launches an MCP server (one
of mcp/servers.json's entries, e.g. "filesystem") as a subprocess and
speaks the same newline-delimited JSON-RPC 2.0 protocol that
mcp/server.py's ToolServer implements on the far end - initialize,
tools/list, tools/call.

One MCPClient instance owns one server subprocess. Use as a context
manager so the subprocess is always terminated:

    with MCPClient("filesystem") as client:
        tools = client.list_tools()
        result = client.call_tool("read_file", {"path": "README.md"})

The subprocess inherits this process's stdin/stdout for its own stdio
JSON-RPC pipe (via subprocess.PIPE), but its stderr and the controlling
terminal are left alone - a tool that needs to prompt the human (e.g.
read_external_file's confirmation) does so over /dev/tty, orthogonal to
this pipe. See mcp/confirmation.py.
"""

import json
import logging
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_STARTUP_TIMEOUT = 10
DEFAULT_CALL_TIMEOUT = 60


class MCPClientError(RuntimeError):
    """Raised for launch failures, protocol errors, or a tool error result."""


class MCPClient:
    """
    A stdio JSON-RPC client for one MCP server subprocess.

    Args:
        server_name: Key into mcp/servers.json's "servers" object.
        server_config: That entry's dict ({"command", "args", "env", ...}).
        cwd:          Working directory for the subprocess. Tool servers
                      that scope paths to a project root (e.g. filesystem's
                      resolve_safe) read LOCAL_AI_RUNTIME_HOST from the
                      environment instead, so this mainly affects relative
                      command/module resolution.
        env:          Extra environment variables merged over the current
                      environment and the config's own "env" entries.
    """

    def __init__(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        self.server_name = server_name
        self._config = server_config
        self._cwd = cwd
        self._extra_env = env or {}
        self._process: Optional[subprocess.Popen] = None
        self._next_id = 1
        self._lock = threading.Lock()
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, timeout: int = DEFAULT_STARTUP_TIMEOUT) -> None:
        """Launch the server subprocess and complete the initialize handshake."""
        if self._process is not None:
            return  # already started

        import os

        command = self._config.get("command")
        args = self._config.get("args", [])
        if not command:
            raise MCPClientError(
                f"MCP server '{self.server_name}' has no 'command' in servers.json"
            )

        full_env = os.environ.copy()
        full_env.update(self._config.get("env", {}))
        full_env.update(self._extra_env)

        try:
            self._process = subprocess.Popen(
                [command, *args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self._cwd) if self._cwd else None,
                env=full_env,
                text=True,
                bufsize=1,  # line-buffered
            )
        except OSError as e:
            raise MCPClientError(
                f"Failed to launch MCP server '{self.server_name}' "
                f"({command} {' '.join(args)}): {e}"
            ) from e

        try:
            self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "domus-janus", "version": "0.3.5"},
            }, timeout=timeout)
            self._send_notification("notifications/initialized")
        except Exception:
            self.close()
            raise

        logger.info("MCP server '%s' started (pid %s)", self.server_name, self._process.pid)

    def close(self) -> None:
        """Terminate the subprocess, if running. Safe to call more than once."""
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
        except Exception:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        logger.info("MCP server '%s' stopped", self.server_name)

    def __enter__(self) -> "MCPClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------
    def _send_notification(self, method: str, params: Optional[dict] = None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _send_request(self, method: str, params: Optional[dict] = None,
                       timeout: int = DEFAULT_CALL_TIMEOUT) -> dict:
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise MCPClientError(f"MCP server '{self.server_name}' is not running")

        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            self._write({
                "jsonrpc": "2.0", "id": request_id,
                "method": method, "params": params or {},
            })
            response = self._read_response(request_id, timeout)

        if "error" in response:
            error = response["error"]
            raise MCPClientError(
                f"MCP server '{self.server_name}' returned an error for {method}: "
                f"{error.get('message', error)}"
            )
        return response.get("result", {})

    def _write(self, message: dict) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise MCPClientError(f"MCP server '{self.server_name}' is not running")
        try:
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            stderr = self._drain_stderr()
            raise MCPClientError(
                f"MCP server '{self.server_name}' pipe closed unexpectedly"
                f"{': ' + stderr if stderr else ''}"
            ) from e

    def _read_response(self, expected_id: int, timeout: int) -> dict:
        """Read lines until one carries expected_id (skipping any
        notifications the server might emit in between)."""
        import time

        process = self._process
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() > deadline:
                stderr = self._drain_stderr()
                raise MCPClientError(
                    f"Timed out waiting for MCP server '{self.server_name}' "
                    f"to respond{': ' + stderr if stderr else ''}"
                )
            if process is None or process.poll() is not None:
                stderr = self._drain_stderr()
                raise MCPClientError(
                    f"MCP server '{self.server_name}' exited unexpectedly"
                    f"{': ' + stderr if stderr else ''}"
                )
            line = process.stdout.readline()
            if not line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line from '%s': %r",
                               self.server_name, line[:200])
                continue
            if message.get("id") == expected_id:
                return message
            # Response to some earlier/other request or a notification - ignore.

    def _drain_stderr(self) -> str:
        process = self._process
        if process is None or process.stderr is None:
            return ""
        try:
            return process.stderr.read(2000) or ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_tools(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Return this server's tool definitions (name, description, inputSchema)."""
        if self._tools_cache is not None and not refresh:
            return self._tools_cache
        result = self._send_request("tools/list")
        tools = result.get("tools", [])
        self._tools_cache = tools
        return tools

    def call_tool(self, name: str, arguments: Dict[str, Any],
                  timeout: int = DEFAULT_CALL_TIMEOUT) -> str:
        """
        Call a tool and return its text output.

        Raises MCPClientError if the tool itself reported an error
        (isError: true in the result, e.g. a denied confirmation or an
        exception inside the tool) or if the protocol call failed.
        """
        result = self._send_request(
            "tools/call", {"name": name, "arguments": arguments}, timeout=timeout,
        )
        content = result.get("content", [])
        text = "\n".join(
            block.get("text", "") for block in content if block.get("type") == "text"
        )
        if result.get("isError"):
            raise MCPClientError(f"Tool '{name}' failed: {text or '(no message)'}")
        return text