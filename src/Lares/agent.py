"""
Lares.agent - the Agent facade.

An Agent is one model plus everything Lares knows about how to run a
chat turn with it well: its AgentProfile (tool-usage/response-pattern
quirks, see Lares.profiles), its MCP permissions (Lares.permissions),
and the response policy that papers over its known bad habits
(Lares.response_policy). Faber.messaging.chat() remains the only thing
that actually talks to Ollama - Agent sits directly above it and makes
the three decisions Faber deliberately doesn't:

  1. Should this model be offered tools at all this session?
     (AgentPermissions.tools_allowed - a model whose base has no native
     tool-call support should never see a `tools` array.)
  2. Which MCP server(s) should be launched to back those tools?
     (the "filesystem" launch Janus.main._setup_filesystem_tools used
     to do ad hoc is now Agent.setup_tools, reusable by anything.)
  3. Was the reply actually good, or does it match a known bad pattern
     for this model that's worth one corrective retry?
     (Lares.response_policy, gated per-profile.)

Getting a new model working end to end is: add an AgentProfile (and,
if it needs filesystem/git/fetch tools, an mcp/profiles/<Model>.json -
unchanged, Custos still owns that file), then `Agent(model_name)`.
Nothing else needs touching.
"""

import logging
from typing import List, Optional, Tuple

from Custos.mcp import MCPConfigError, filter_tools_for_model, mcp_tools_to_ollama_tools
from Custos.mcp_client import MCPClient, MCPClientError
from Faber.messaging import ChatResponse, Message, chat as faber_chat

from Lares.permissions import AgentPermissions
from Lares.profiles import AgentProfile, get_profile
from Lares.response_policy import apply_response_policy

logger = logging.getLogger(__name__)

__all__ = ["Agent"]

# The only MCP server Agent.setup_tools currently knows how to launch -
# matches what Janus.main._setup_filesystem_tools did before this moved
# here. Expanding to git/fetch is a matter of generalizing this list,
# not a design change; kept narrow for now rather than speculatively
# wiring servers nothing in this codebase launches yet.
_SUPPORTED_TOOL_SERVERS = ("filesystem",)


class Agent:
    """
    A model, ready to chat, with its profile/permissions/response-policy
    already applied.

    Args:
        model: The model name (as known to Ollama and to
               mcp/profiles/<Model>.json).
        profile: Override the registered AgentProfile (mainly for
                 tests). Defaults to Lares.profiles.get_profile(model).
        permissions: Override the AgentPermissions this agent uses
                     (mainly for tests, or for a caller that needs a
                     non-default MCPManager/mcp_dir). Defaults to a
                     fresh AgentPermissions(model, profile).
    """

    def __init__(self, model: str, profile: Optional[AgentProfile] = None,
                 permissions: Optional[AgentPermissions] = None):
        self.model = model
        self.profile = profile or get_profile(model)
        self.permissions = permissions or AgentPermissions(self.model, self.profile)
        self._mcp_clients: List[MCPClient] = []
        # Which client owns a given (live) tool name, so call_tool() can
        # route without the caller (e.g. Janus.main) needing to know
        # which MCP server backs which tool.
        self._tool_owners: dict = {}

    # ------------------------------------------------------------------
    # Tool setup
    # ------------------------------------------------------------------
    def setup_tools(self) -> Tuple[List[MCPClient], Optional[List[dict]]]:
        """
        Launch whichever supported MCP servers this agent is permitted to
        use, and build the Ollama-format tools array for them.

        Returns (clients, ollama_tools): clients is the list of started
        MCPClients (caller is responsible for closing them, e.g. via
        close_tools() or its own try/finally - Agent does not auto-close
        since a chat session spans many turns); ollama_tools is None if
        the agent shouldn't be offered tools at all (profile says it
        doesn't support tool calls, no MCP profile, or no permitted
        tools among the supported servers) - None (not []) specifically
        so callers can pass it straight through to
        Faber.messaging.chat(tools=...), where None means "don't
        advertise tools" and [] would still (harmlessly) send an empty
        tools array.

        Never raises for an unavailable/misconfigured server - that
        degrades to "chat without tools" exactly like
        Janus.main._setup_filesystem_tools used to, since a tool outage
        shouldn't fail the whole chat session.
        """
        if not self.permissions.tools_allowed():
            return [], None

        all_tools: List[dict] = []
        clients: List[MCPClient] = []
        self._tool_owners = {}

        for server in _SUPPORTED_TOOL_SERVERS:
            allowed = self.permissions.get_tools().get(server)
            if not allowed:
                continue
            try:
                server_config = self.permissions.get_server_config(server)
                client = MCPClient(server, server_config)
                client.start()
                live_tools = client.list_tools()
                permitted = filter_tools_for_model(
                    live_tools, server, self.profile.effective_mcp_profile_name(),
                    self.permissions.manager,
                )
                if not permitted:
                    client.close()
                    continue
                clients.append(client)
                converted = mcp_tools_to_ollama_tools(permitted)
                all_tools.extend(converted)
                for tool in converted:
                    self._tool_owners[tool["function"]["name"]] = client
            except (MCPConfigError, MCPClientError) as e:
                logger.warning(
                    "Agent '%s': MCP server '%s' unavailable (%s) - "
                    "continuing without it", self.model, server, e,
                )
                continue

        self._mcp_clients = clients
        if not all_tools:
            return clients, None
        return clients, all_tools

    def close_tools(self) -> None:
        """Close every MCP client this agent's setup_tools() launched."""
        for client in self._mcp_clients:
            client.close()
        self._mcp_clients = []
        self._tool_owners = {}

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Invoke `tool_name` on whichever MCP client setup_tools() recorded
        as its owner, so callers (e.g. Janus.main's tool_executor) never
        need to know which server backs which tool - there's exactly one
        client today (filesystem), but this keeps that an implementation
        detail rather than something every caller has to track.

        Raises KeyError if tool_name isn't one setup_tools() actually
        advertised - callers should already be checking
        permitted_tool_names()/the model's own allowlist before calling
        this, so this is a programming-error guard, not the permission
        check itself.
        """
        client = self._tool_owners.get(tool_name)
        if client is None:
            raise KeyError(
                f"No MCP client owns tool '{tool_name}' for agent '{self.model}' - "
                f"was it returned by this agent's setup_tools()?"
            )
        return client.call_tool(tool_name, arguments)

    def permitted_tool_names(self, ollama_tools: Optional[List[dict]]) -> set:
        """Convenience: the set of tool names in an ollama_tools list (as
        returned by setup_tools), for a tool_executor's own allowlist
        check at call time - see Janus.main's tool_executor for why that
        check happens again there and not just at advertisement time."""
        if not ollama_tools:
            return set()
        return {t["function"]["name"] for t in ollama_tools}

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def chat(
        self,
        history: List[Message],
        *,
        tools: Optional[List[dict]] = None,
        tool_executor=None,
        **kwargs,
    ) -> ChatResponse:
        """
        Run one chat turn for this agent, then apply its response policy
        (Lares.response_policy) - retrying once if the reply looks empty
        or looks like it ignored a tool result it just received, per
        this agent's profile.

        Recording into Mentis AIMemory is always the caller's job, never
        Faber.messaging's own record=True path - this method always
        calls faber_chat(record=False) internally, on both the initial
        attempt and any retry. This isn't just a style preference: a
        retry calls faber_chat a second time with a *longer* history
        (the original messages plus the rejected reply plus the nudge -
        see retried_history below), and record=True records every
        message passed in, not just the new turn. Letting Faber record
        would mean every message from the first attempt gets written to
        AIMemory twice - once from the initial call, again from the
        retry - exactly the duplicate-recording bug
        Janus.main.handle_chat's own record=False already works around
        for its normal (non-retried) turns. A record=True kwarg isn't
        accepted here at all, rather than accepted and overridden, so
        this can't be quietly reintroduced by a future caller passing
        record=True through **kwargs.

        `history` is mutated-by-convention the same way
        Janus.main.handle_chat already treats it: this method appends
        the retry nudge (if any) to its own working copy, not to the
        list the caller passed in, so a rejected/retried turn doesn't
        leave a stray synthetic message in the caller's history on
        return - only the final accepted response is the caller's
        concern. tool_trace on the returned ChatResponse covers tool
        activity from the *last* attempt only (matching
        Faber.messaging's own per-call contract).

        Tool calls are only offered if `tools` is given AND this
        profile's permissions actually allow tools - callers should
        still gate on Agent.permissions.tools_allowed() / pass
        tools=None themselves when they don't want tools at all this
        turn (e.g. --no-tools), the same way Janus.main does; this
        method does not second-guess an explicit tools=None.
        """
        if "record" in kwargs:
            raise TypeError(
                "Agent.chat() does not accept record= - recording is always "
                "the caller's responsibility, never Faber's own record=True "
                "path (see this method's docstring for why a retry makes "
                "record=True actively harmful here, not just redundant)."
            )

        effective_tools = tools if (tools and self.permissions.tools_allowed()) else None
        effective_executor = tool_executor if effective_tools else None

        response = faber_chat(
            self.model, history, record=False,
            tools=effective_tools, tool_executor=effective_executor,
            **kwargs,
        )

        def _retry(nudge: Message) -> ChatResponse:
            retried_history = list(history) + [response.message, nudge]
            return faber_chat(
                self.model, retried_history, record=False,
                tools=effective_tools, tool_executor=effective_executor,
                **kwargs,
            )

        result = apply_response_policy(response, self.profile, _retry)
        if result.retried:
            logger.info(
                "Agent '%s': accepted retried reply after '%s'",
                self.model, result.reason,
            )
        return result.response