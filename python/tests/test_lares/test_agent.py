"""
Tests for Lares/agent.py - Agent.

setup_tools()/close_tools() are tested against the tmp_path-backed
mcp_dir/manager fixtures with MCPClient mocked (never a real subprocess -
see test_custos's own convention for the same reason). chat() is tested
with Faber.messaging.chat (imported into Lares.agent as faber_chat)
mocked, since Agent.chat's whole job is orchestration around that call,
not re-testing Faber's own tool loop (already covered in test_faber).
"""

from unittest.mock import MagicMock, patch

import pytest

from Faber.messaging import ChatResponse, Message
from Lares.agent import Agent
from Lares.permissions import AgentPermissions
from Lares.profiles import AgentProfile

pytestmark = pytest.mark.lares


def _agent(model, manager, **profile_kwargs):
    profile = AgentProfile(name=model, **profile_kwargs)
    permissions = AgentPermissions(model, profile, manager=manager)
    return Agent(model, profile=profile, permissions=permissions)


class TestAgentConstruction:
    def test_default_permissions_use_registered_profile(self):
        agent = Agent("Mercury")
        assert agent.profile.name == "Mercury"
        assert agent.permissions.profile is agent.profile

    def test_injected_permissions_override_the_default(self, manager):
        profile = AgentProfile(name="ToolModel", supports_tool_calls=True)
        permissions = AgentPermissions("ToolModel", profile, manager=manager)
        agent = Agent("ToolModel", profile=profile, permissions=permissions)
        assert agent.permissions is permissions
        assert agent.permissions.manager is manager


class TestSetupToolsPermissionGating:
    def test_returns_no_tools_when_model_does_not_support_tool_calls(self, manager):
        agent = _agent("ToolModel", manager, supports_tool_calls=False)
        clients, tools = agent.setup_tools()
        assert clients == []
        assert tools is None

    def test_returns_no_tools_when_no_mcp_profile(self, manager):
        agent = _agent("NoSuchModel", manager, supports_tool_calls=True)
        clients, tools = agent.setup_tools()
        assert clients == []
        assert tools is None


class TestSetupToolsLaunchesPermittedServers:
    def test_launches_filesystem_and_converts_tools(self, manager):
        fake_client = MagicMock()
        fake_client.list_tools.return_value = [
            {"name": "read_file", "description": "Read a file",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
            {"name": "list_directory", "description": "List a dir", "inputSchema": {}},
            {"name": "write_file", "description": "Write", "inputSchema": {}},
        ]
        agent = _agent("ToolModel", manager, supports_tool_calls=True)

        with patch("Lares.agent.MCPClient", return_value=fake_client):
            clients, tools = agent.setup_tools()

        fake_client.start.assert_called_once()
        assert clients == [fake_client]
        names = {t["function"]["name"] for t in tools}
        # write_file isn't in ToolModel's allowed_tools (see conftest) -
        # only read_file/list_directory should survive the filter.
        assert names == {"read_file", "list_directory"}

    def test_closes_client_and_returns_none_when_nothing_permitted(self, manager):
        fake_client = MagicMock()
        fake_client.list_tools.return_value = [{"name": "some_other_tool", "inputSchema": {}}]
        agent = _agent("ToolModel", manager, supports_tool_calls=True)

        with patch("Lares.agent.MCPClient", return_value=fake_client):
            clients, tools = agent.setup_tools()

        fake_client.close.assert_called_once()
        assert clients == []
        assert tools is None

    def test_degrades_gracefully_when_server_fails_to_launch(self, manager):
        from Custos.mcp_client import MCPClientError
        fake_client = MagicMock()
        fake_client.start.side_effect = MCPClientError("failed to launch")
        agent = _agent("ToolModel", manager, supports_tool_calls=True)

        with patch("Lares.agent.MCPClient", return_value=fake_client):
            clients, tools = agent.setup_tools()

        assert clients == []
        assert tools is None


class TestCloseTools:
    def test_closes_every_launched_client(self, manager):
        fake_client = MagicMock()
        fake_client.list_tools.return_value = [
            {"name": "read_file", "description": "", "inputSchema": {}},
        ]
        agent = _agent("ToolModel", manager, supports_tool_calls=True)
        with patch("Lares.agent.MCPClient", return_value=fake_client):
            agent.setup_tools()

        agent.close_tools()
        fake_client.close.assert_called_once()
        assert agent._mcp_clients == []

    def test_close_tools_is_a_noop_when_nothing_was_launched(self, manager):
        agent = _agent("ToolModel", manager, supports_tool_calls=False)
        agent.close_tools()  # must not raise


class TestPermittedToolNames:
    def test_extracts_names_from_ollama_tools(self, manager):
        agent = _agent("ToolModel", manager)
        tools = [
            {"type": "function", "function": {"name": "read_file"}},
            {"type": "function", "function": {"name": "list_directory"}},
        ]
        assert agent.permitted_tool_names(tools) == {"read_file", "list_directory"}

    def test_empty_set_for_none(self, manager):
        agent = _agent("ToolModel", manager)
        assert agent.permitted_tool_names(None) == set()

    def test_empty_set_for_empty_list(self, manager):
        agent = _agent("ToolModel", manager)
        assert agent.permitted_tool_names([]) == set()


class TestAgentChatBasic:
    def test_delegates_to_faber_chat(self, manager):
        agent = _agent("ToolModel", manager, supports_tool_calls=False)
        expected = ChatResponse(model="ToolModel", message=Message("assistant", "hi there"))

        with patch("Lares.agent.faber_chat", return_value=expected) as mock_chat:
            response = agent.chat([Message("user", "hello")])

        assert response is expected
        mock_chat.assert_called_once()
        _, kwargs = mock_chat.call_args
        assert kwargs["tools"] is None
        assert kwargs["tool_executor"] is None

    def test_always_calls_faber_chat_with_record_false(self, manager):
        """Agent.chat must never let Faber record - see its docstring for
        why a retry with record=True would double-record every earlier
        message in history, not just redundantly re-record it once."""
        agent = _agent("ToolModel", manager, supports_tool_calls=False)
        expected = ChatResponse(model="ToolModel", message=Message("assistant", "hi"))

        with patch("Lares.agent.faber_chat", return_value=expected) as mock_chat:
            agent.chat([Message("user", "hello")])

        assert mock_chat.call_args.kwargs["record"] is False

    def test_rejects_an_explicit_record_kwarg(self, manager):
        agent = _agent("ToolModel", manager, supports_tool_calls=False)
        with pytest.raises(TypeError, match="record"):
            agent.chat([Message("user", "hello")], record=True)

    def test_tools_withheld_when_permissions_disallow_even_if_passed(self, manager):
        """A caller might still pass a tools= list, but Agent.chat must
        not forward it to Faber if this agent's permissions say no -
        this is the Vulcan/Minerva safety net at the chat() call site,
        not just at setup_tools()."""
        agent = _agent("ToolModel", manager, supports_tool_calls=False)
        some_tools = [{"type": "function", "function": {"name": "read_file"}}]
        expected = ChatResponse(model="ToolModel", message=Message("assistant", "ok"))

        with patch("Lares.agent.faber_chat", return_value=expected) as mock_chat:
            agent.chat([Message("user", "hi")], tools=some_tools, tool_executor=lambda *a: "x")

        _, kwargs = mock_chat.call_args
        assert kwargs["tools"] is None
        assert kwargs["tool_executor"] is None

    def test_tools_forwarded_when_permitted(self, manager):
        agent = _agent("ToolModel", manager, supports_tool_calls=True)
        some_tools = [{"type": "function", "function": {"name": "read_file"}}]
        executor = lambda *a: "x"
        expected = ChatResponse(model="ToolModel", message=Message("assistant", "ok"))

        with patch("Lares.agent.faber_chat", return_value=expected) as mock_chat:
            agent.chat([Message("user", "hi")], tools=some_tools, tool_executor=executor)

        _, kwargs = mock_chat.call_args
        assert kwargs["tools"] == some_tools
        assert kwargs["tool_executor"] is executor


class TestAgentChatResponsePolicyIntegration:
    def test_retries_through_faber_chat_on_empty_reply(self, manager):
        agent = _agent("Analyst", manager, retry_on_empty_reply=True,
                        supports_tool_calls=False)
        empty = ChatResponse(model="Analyst", message=Message("assistant", ""))
        real = ChatResponse(model="Analyst", message=Message("assistant", "the real answer"))

        with patch("Lares.agent.faber_chat", side_effect=[empty, real]) as mock_chat:
            response = agent.chat([Message("user", "hi")])

        assert response.content == "the real answer"
        assert mock_chat.call_count == 2

        # The retried call's history must include the nudge as a new
        # trailing user message, appended after the model's own (empty)
        # turn - not mutating/duplicating the caller's original history.
        second_call_history = mock_chat.call_args_list[1].args[1]
        assert [m.role for m in second_call_history] == ["user", "assistant", "user"]

    def test_caller_history_list_is_not_mutated_by_a_retry(self, manager):
        agent = _agent("Analyst", manager, retry_on_empty_reply=True,
                        supports_tool_calls=False)
        empty = ChatResponse(model="Analyst", message=Message("assistant", ""))
        real = ChatResponse(model="Analyst", message=Message("assistant", "answer"))
        original_history = [Message("user", "hi")]

        with patch("Lares.agent.faber_chat", side_effect=[empty, real]):
            agent.chat(original_history)

        # The caller's own list must be exactly as they passed it in -
        # no nudge or assistant turn leaked into it.
        assert len(original_history) == 1
        assert original_history[0].content == "hi"

    def test_no_retry_when_profile_disables_it(self, manager):
        agent = _agent("ToolModel", manager, retry_on_empty_reply=False,
                        supports_tool_calls=False)
        empty = ChatResponse(model="ToolModel", message=Message("assistant", ""))

        with patch("Lares.agent.faber_chat", return_value=empty) as mock_chat:
            response = agent.chat([Message("user", "hi")])

        assert response.content == ""
        assert mock_chat.call_count == 1