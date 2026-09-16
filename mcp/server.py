"""
server.py - Minimal MCP-over-stdio server host (JSON-RPC 2.0).

Implements just enough of the Model Context Protocol to expose locally
written Python tools: initialize handshake, tools/list, tools/call, and
notifications. One process serves one tool package.

A tool is any module with a call(arguments: dict) -> str function.
Tool metadata (name, description, inputSchema) comes from a module-level
TOOL dict:

    TOOL = {
        "name": "read_file",
        "description": "Read the contents of a file",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    }

    def call(arguments):
        ...

The server reads newline-delimited JSON-RPC messages on stdin and writes
responses on stdout. Anything a tool prints must go to stderr - stdout is
protocol-only.
"""

import json
import logging
import sys
import traceback

from Mercurius import EventType as BusEventType

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"

METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ToolServer:
    """Serves a dict of {tool_name: tool_module} over MCP stdio."""

    def __init__(self, name: str, tools: dict):
        self.name = name
        self.tools = tools

    def _publish(self, event_type, **payload) -> None:
        """Publish a tool event to the Mercurius bus if one is running.

        The bus lives in the parent runtime process - a stdio server is a
        child process - so this only reaches a bus when the server runs
        in-process (tests, embedded use). It must never break the protocol.
        """
        try:
            from Mercurius import publish_event
            publish_event(event_type, source=self.name, payload=payload)
        except Exception:
            logger.debug("Mercurius bus unavailable; tool event not published",
                         exc_info=True)

    def serve(self, stdin=None, stdout=None):
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line: %r", line[:200])
                continue

            response = self.handle(request)
            # Notifications (no "id") get no response
            if response is not None:
                stdout.write(json.dumps(response) + "\n")
                stdout.flush()

    def handle(self, request: dict):
        method = request.get("method", "")
        request_id = request.get("id")
        is_notification = "id" not in request

        if method == "initialize":
            return self._result(request_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.name, "version": "0.1.0"},
            })
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return self._result(request_id, {})
        if method == "tools/list":
            return self._result(request_id, {
                "tools": [module.TOOL for module in self.tools.values()]
            })
        if method == "tools/call":
            return self._call_tool(request_id, request.get("params") or {})

        if is_notification:
            return None
        return self._error(request_id, METHOD_NOT_FOUND, f"Unknown method: {method}")

    def _call_tool(self, request_id, params: dict):
        name = params.get("name", "")
        arguments = params.get("arguments") or {}

        module = self.tools.get(name)
        if module is None:
            return self._error(request_id, INVALID_PARAMS, f"Unknown tool: {name}")

        # Confirmation is enforced inside the tool itself (mcp/confirmation.py
        # asks the human on their TTY). The REQUIRES_CONFIRMATION marker only
        # controls the post-approval TOOL_CONFIRMATION_REQUIRED event below.
        confirmation_gated = getattr(module, "REQUIRES_CONFIRMATION", False)

        self._publish(BusEventType.TOOL_INVOKED, tool=name, arguments=arguments)

        try:
            output = module.call(arguments)
        except PermissionError as e:
            logger.info("Tool %s denied by user: %s", name, e)
            self._publish(BusEventType.TOOL_RESULT, tool=name,
                          is_error=True, error=str(e), denied=True)
            return self._result(request_id, {
                "content": [{"type": "text", "text": f"Denied: {e}"}],
                "isError": True,
                "denied": True,
            })
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            self._publish(BusEventType.TOOL_RESULT, tool=name,
                          is_error=True, error=str(e))
            return self._result(request_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

        if confirmation_gated:
            # Only now has the human actually approved (inside module.call) -
            # publish before this point would imply approval that never happened.
            self._publish(BusEventType.TOOL_CONFIRMATION_REQUIRED,
                          tool=name, arguments=arguments, approved=True)

        self._publish(BusEventType.TOOL_RESULT, tool=name, is_error=False,
                      output_preview=str(output)[:200])
        return self._result(request_id, {
            "content": [{"type": "text", "text": str(output)}],
            "isError": False,
        })

    @staticmethod
    def _result(request_id, result):
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id, code, message):
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": code, "message": message}}


def run_server(name: str, tool_package: str):
    """
    Entry point for per-server __main__ modules. Imports every module in
    the given package that defines TOOL + call(), then serves them.
    """
    import importlib
    import pkgutil

    package = importlib.import_module(tool_package)
    tools = {}
    for info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{tool_package}.{info.name}")
        if hasattr(module, "TOOL") and hasattr(module, "call"):
            tools[module.TOOL["name"]] = module
        else:
            logger.warning("Skipping %s: no TOOL/call defined", info.name)

    ToolServer(name, tools).serve()
