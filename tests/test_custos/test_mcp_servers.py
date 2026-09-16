"""
Tests for the local MCP tool servers under mcp/ (filesystem, git, fetch)
and the shared stdio server host (mcp/server.py).

Everything is hermetic: filesystem tools run against tmp_path (via the
host_project_dir fixture's LOCAL_AI_RUNTIME_HOST), git tools run in a
throwaway git repo, and fetch never touches the network (urlopen mocked).
Protocol tests drive ToolServer.handle()/serve() directly - no real
subprocess is spawned.
"""

import io
import json

import pytest

pytestmark = pytest.mark.custos


# ---------------------------------------------------------------------------
# ToolServer protocol host
# ---------------------------------------------------------------------------

class _FakeTool:
    TOOL = {
        "name": "echo",
        "description": "echo back the 'text' argument",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }

    @staticmethod
    def call(arguments):
        return arguments["text"]


class _FailingTool:
    TOOL = {"name": "boom", "description": "always raises", "inputSchema": {}}

    @staticmethod
    def call(arguments):
        raise ValueError("kaboom")


@pytest.fixture
def server():
    from mcp.server import ToolServer
    return ToolServer("test-server", {"echo": _FakeTool, "boom": _FailingTool})


class TestToolServerProtocol:
    def test_initialize_returns_capabilities(self, server):
        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert response["id"] == 1
        assert response["result"]["serverInfo"]["name"] == "test-server"
        assert "tools" in response["result"]["capabilities"]

    def test_initialized_notification_gets_no_response(self, server):
        assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    def test_tools_list_exposes_tool_metadata(self, server):
        response = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in response["result"]["tools"]}
        assert names == {"echo", "boom"}

    def test_tools_call_returns_text_content(self, server):
        response = server.handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hello"}},
        })
        content = response["result"]["content"]
        assert content == [{"type": "text", "text": "hello"}]
        assert response["result"]["isError"] is False

    def test_unknown_tool_is_a_protocol_error(self, server):
        response = server.handle({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "ghost", "arguments": {}},
        })
        assert response["error"]["code"] == -32602

    def test_tool_exception_becomes_is_error_result(self, server):
        response = server.handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "boom", "arguments": {}},
        })
        assert response["result"]["isError"] is True
        assert "kaboom" in response["result"]["content"][0]["text"]

    def test_unknown_method_is_method_not_found(self, server):
        response = server.handle({"jsonrpc": "2.0", "id": 6, "method": "resources/list"})
        assert response["error"]["code"] == -32601

    def test_serve_round_trip_over_streams(self, server):
        requests = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": "echo", "arguments": {"text": "hi"}}}),
            "this is not json",
        ]) + "\n"

        stdout = io.StringIO()
        server.serve(stdin=io.StringIO(requests), stdout=stdout)

        responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
        assert len(responses) == 2  # notification + malformed line produce none
        assert responses[0]["id"] == 1
        assert responses[1]["result"]["content"][0]["text"] == "hi"


# ---------------------------------------------------------------------------
# Filesystem tools
# ---------------------------------------------------------------------------

class TestFilesystemTools:
    def test_read_file(self, host_project_dir):
        (host_project_dir / "note.txt").write_text("hello world")
        from mcp.filesystem.tools import read_file
        assert read_file.call({"path": "note.txt"}) == "hello world"

    def test_read_file_max_chars(self, host_project_dir):
        (host_project_dir / "big.txt").write_text("x" * 100)
        from mcp.filesystem.tools import read_file
        assert read_file.call({"path": "big.txt", "max_chars": 10}) == "x" * 10

    def test_read_file_missing_raises(self, host_project_dir):
        from mcp.filesystem.tools import read_file
        with pytest.raises(FileNotFoundError):
            read_file.call({"path": "nope.txt"})

    def test_list_directory(self, host_project_dir):
        (host_project_dir / "a.txt").write_text("a")
        (host_project_dir / "sub").mkdir()
        from mcp.filesystem.tools import list_directory
        assert list_directory.call({}) == "a.txt\nsub/"

    def test_search_files(self, host_project_dir):
        (host_project_dir / "src").mkdir()
        (host_project_dir / "src" / "main.py").write_text("")
        (host_project_dir / "readme.md").write_text("")
        from mcp.filesystem.tools import search_files
        assert search_files.call({"pattern": ".py"}) == "src/main.py"

    def test_write_file_creates_parents(self, host_project_dir):
        from mcp.filesystem.tools import write_file
        result = write_file.call({"path": "deep/nested/out.txt", "content": "data"})
        assert "out.txt" in result
        assert (host_project_dir / "deep/nested/out.txt").read_text() == "data"

    def test_path_escape_is_refused(self, host_project_dir):
        from mcp.filesystem.tools import read_file
        with pytest.raises(ValueError, match="escapes project root"):
            read_file.call({"path": "../../etc/hostname"})


class TestEditFile:
    def test_replaces_single_line(self, host_project_dir):
        target = host_project_dir / "code.py"
        target.write_text("line1\nline2\nline3\n")

        from mcp.filesystem.tools import edit_file
        result = edit_file.call({
            "path": "code.py", "start_line": 2, "end_line": 2,
            "content": "replaced",
        })

        assert target.read_text() == "line1\nreplaced\nline3\n"
        assert "lines 2-2" in result

    def test_replaces_range_with_multiple_lines(self, host_project_dir):
        target = host_project_dir / "f.txt"
        target.write_text("a\nb\nc\nd\n")

        from mcp.filesystem.tools import edit_file
        edit_file.call({
            "path": "f.txt", "start_line": 2, "end_line": 3,
            "content": "x\ny\nz",
        })

        assert target.read_text() == "a\nx\ny\nz\nd\n"

    def test_rejects_invalid_ranges(self, host_project_dir):
        target = host_project_dir / "f.txt"
        target.write_text("a\nb\n")

        from mcp.filesystem.tools import edit_file
        with pytest.raises(ValueError, match=">= 1"):
            edit_file.call({"path": "f.txt", "start_line": 0, "end_line": 1, "content": "x"})
        with pytest.raises(ValueError, match=">= start_line"):
            edit_file.call({"path": "f.txt", "start_line": 2, "end_line": 1, "content": "x"})
        with pytest.raises(ValueError, match="beyond end of file"):
            edit_file.call({"path": "f.txt", "start_line": 1, "end_line": 99, "content": "x"})

    def test_missing_file_raises(self, host_project_dir):
        from mcp.filesystem.tools import edit_file
        with pytest.raises(FileNotFoundError):
            edit_file.call({"path": "ghost.txt", "start_line": 1, "end_line": 1, "content": "x"})

    def test_cannot_escape_project_root(self, host_project_dir):
        from mcp.filesystem.tools import edit_file
        with pytest.raises(ValueError, match="escapes project root"):
            edit_file.call({"path": "../../tmp/evil.txt", "start_line": 1, "end_line": 1, "content": "x"})


class TestReadExternalFile:
    """read_external_file must never run on the model's say-so: approval
    comes from the human (TTY prompt) or the DOMUS_APPROVED_EXTERNAL_READS
    env allowlist - never from the request's own arguments."""

    def test_reads_absolute_path_when_human_approves(self, tmp_path, monkeypatch):
        external = tmp_path / "outside.txt"
        external.write_text("external content")
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: True)

        from mcp.filesystem.tools import read_external_file
        assert read_external_file.call({"path": str(external)}) == "external content"

    def test_denied_when_human_says_no(self, tmp_path, monkeypatch):
        external = tmp_path / "secret.txt"
        external.write_text("must not leak")
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: False)

        from mcp.filesystem.tools import read_external_file
        with pytest.raises(PermissionError, match="User denied"):
            read_external_file.call({"path": str(external)})

    def test_confirm_argument_alone_is_not_enough(self, tmp_path, monkeypatch):
        """A model-supplied confirm:true must NOT bypass the human prompt."""
        external = tmp_path / "secret.txt"
        external.write_text("must not leak")
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: False)

        from mcp.filesystem.tools import read_external_file
        with pytest.raises(PermissionError):
            read_external_file.call({"path": str(external), "confirm": True})

    def test_preapproved_via_env_var_skips_prompt(self, tmp_path, monkeypatch):
        external = tmp_path / "approved.txt"
        external.write_text("pre-approved")
        monkeypatch.setenv("DOMUS_APPROVED_EXTERNAL_READS", str(external))
        monkeypatch.setattr(
            "mcp.confirmation.request_confirmation",
            lambda prompt: pytest.fail("prompt should not run for pre-approved paths"),
        )

        from mcp.filesystem.tools import read_external_file
        assert read_external_file.call({"path": str(external)}) == "pre-approved"

    def test_env_var_matches_exact_paths_only(self, tmp_path, monkeypatch):
        approved = tmp_path / "approved.txt"
        approved.write_text("x")
        other = tmp_path / "other.txt"
        other.write_text("y")
        monkeypatch.setenv("DOMUS_APPROVED_EXTERNAL_READS", str(approved))
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: False)

        from mcp.filesystem.tools import read_external_file
        read_external_file.call({"path": str(approved)})  # allowed
        with pytest.raises(PermissionError):
            read_external_file.call({"path": str(other)})

    def test_rejects_relative_path(self):
        from mcp.filesystem.tools import read_external_file
        with pytest.raises(ValueError, match="absolute path"):
            read_external_file.call({"path": "relative/file.txt"})

    def test_missing_file_raises(self, tmp_path):
        from mcp.filesystem.tools import read_external_file
        with pytest.raises(FileNotFoundError):
            read_external_file.call({"path": str(tmp_path / "nope.txt")})


class TestConfirmationModule:
    def test_preapproval_requires_exact_membership(self, monkeypatch):
        import os
        from mcp.confirmation import is_preapproved
        monkeypatch.setenv("DOMUS_APPROVED_EXTERNAL_READS",
                           os.pathsep.join(["/a.txt", "/b.txt"]))
        assert is_preapproved("/a.txt") is True
        assert is_preapproved("/c.txt") is False

    def test_prompt_accepts_only_explicit_yes(self, monkeypatch):
        from mcp import confirmation
        answers = iter(["y\n", "yes\n", "n\n", "\n", "whatever\n"])
        monkeypatch.setattr("sys.stdin.readline", lambda: next(answers))
        monkeypatch.setattr("os.path.exists", lambda p: False)  # force stdin path

        assert confirmation.request_confirmation("q1") is True   # y
        assert confirmation.request_confirmation("q2") is True   # yes
        assert confirmation.request_confirmation("q3") is False  # n
        assert confirmation.request_confirmation("q4") is False  # empty (default N)
        assert confirmation.request_confirmation("q5") is False  # anything else


class TestToolConfirmationFlow:
    """Through the server host: a confirmation-gated tool publishes
    TOOL_CONFIRMATION_REQUIRED when invoked, and a human denial surfaces
    as a denied TOOL_RESULT (not a silent success)."""

    @pytest.fixture
    def external_server(self):
        from mcp.filesystem.tools import read_external_file
        from mcp.server import ToolServer
        return ToolServer("test-fs", {"read_external_file": read_external_file})

    def _invoke(self, server, arguments, request_id=1):
        return server.handle({
            "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": "read_external_file", "arguments": arguments},
        })

    def test_denial_returns_denied_result(self, external_server, tmp_path, monkeypatch):
        target = tmp_path / "secret.txt"
        target.write_text("should never be read")
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: False)

        response = self._invoke(external_server, {"path": str(target)})

        assert response["result"]["isError"] is True
        assert response["result"]["denied"] is True
        assert "Denied" in response["result"]["content"][0]["text"]
        assert "should never be read" not in response["result"]["content"][0]["text"]

    def test_approval_runs_the_tool(self, external_server, tmp_path, monkeypatch):
        target = tmp_path / "secret.txt"
        target.write_text("now readable")
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: True)

        response = self._invoke(external_server, {"path": str(target)})

        assert response["result"]["isError"] is False
        assert response["result"]["content"][0]["text"] == "now readable"

    def test_confirmation_gated_tool_publishes_bus_event(self, external_server, tmp_path, monkeypatch):
        import Mercurius
        # Approval happens inside the tool; the event must fire only after the
        # human has actually approved - so approve here.
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: True)
        (tmp_path / "x.txt").write_text("data")
        bus = Mercurius.initialize_bus()
        received = []
        bus.subscribe(Mercurius.EventType.TOOL_CONFIRMATION_REQUIRED, received.append)
        try:
            self._invoke(external_server, {"path": str(tmp_path / "x.txt")})
        finally:
            bus.stop(drain=True)
            Mercurius.shutdown_bus(drain=False)

        assert len(received) == 1
        assert received[0].payload["tool"] == "read_external_file"
        assert received[0].payload["approved"] is True
        assert received[0].source == "test-fs"

    def test_denied_confirmation_does_not_publish_approval_event(self, external_server, tmp_path, monkeypatch):
        import Mercurius
        monkeypatch.setattr("mcp.confirmation.request_confirmation", lambda prompt: False)
        (tmp_path / "x.txt").write_text("data")
        bus = Mercurius.initialize_bus()
        confirmations, results = [], []
        bus.subscribe(Mercurius.EventType.TOOL_CONFIRMATION_REQUIRED, confirmations.append)
        bus.subscribe(Mercurius.EventType.TOOL_RESULT, results.append)
        try:
            self._invoke(external_server, {"path": str(tmp_path / "x.txt")})
        finally:
            bus.stop(drain=True)
            Mercurius.shutdown_bus(drain=False)

        assert confirmations == []  # human never approved
        assert results[0].payload["denied"] is True

    def test_regular_tools_publish_invoked_and_result(self, host_project_dir):
        import Mercurius
        from mcp.filesystem.tools import read_file
        from mcp.server import ToolServer

        target = host_project_dir / "in.txt"
        target.write_text("data")
        server = ToolServer("test-fs", {"read_file": read_file})

        bus = Mercurius.initialize_bus()
        invoked, results = [], []
        bus.subscribe(Mercurius.EventType.TOOL_INVOKED, invoked.append)
        bus.subscribe(Mercurius.EventType.TOOL_RESULT, results.append)
        try:
            server.handle({
                "jsonrpc": "2.0", "id": 9, "method": "tools/call",
                "params": {"name": "read_file", "arguments": {"path": "in.txt"}},
            })
        finally:
            bus.stop(drain=True)
            Mercurius.shutdown_bus(drain=False)

        assert [e.payload["tool"] for e in invoked] == ["read_file"]
        assert results[0].payload["is_error"] is False
        assert "data" in results[0].payload["output_preview"]

    def test_tool_failure_publishes_error_result(self):
        import Mercurius
        from mcp.server import ToolServer

        class Failing:
            TOOL = {"name": "fail", "description": "", "inputSchema": {}}
            @staticmethod
            def call(arguments):
                raise ValueError("nope")

        server = ToolServer("test-fs", {"fail": Failing})
        bus = Mercurius.initialize_bus()
        results = []
        bus.subscribe(Mercurius.EventType.TOOL_RESULT, results.append)
        try:
            server.handle({
                "jsonrpc": "2.0", "id": 10, "method": "tools/call",
                "params": {"name": "fail", "arguments": {}},
            })
        finally:
            bus.stop(drain=True)
            Mercurius.shutdown_bus(drain=False)

        assert results[0].payload["is_error"] is True
        assert "nope" in results[0].payload["error"]


# ---------------------------------------------------------------------------
# Git tools
# ---------------------------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """A throwaway git repo set as the host project root."""
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "tracked.txt").write_text("v1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)
    monkeypatch.setenv("LOCAL_AI_RUNTIME_HOST", str(repo))
    return repo


class TestGitTools:
    def test_git_status_clean(self, git_repo):
        from mcp.git.tools import git_status
        output = git_status.call({})
        assert "##" in output  # branch line from --branch

    def test_git_status_shows_untracked(self, git_repo):
        (git_repo / "new.txt").write_text("new")
        from mcp.git.tools import git_status
        assert "new.txt" in git_status.call({})

    def test_git_diff_no_changes(self, git_repo):
        from mcp.git.tools import git_diff
        assert git_diff.call({}) == "(no changes)"

    def test_git_diff_shows_change(self, git_repo):
        (git_repo / "tracked.txt").write_text("v2\n")
        from mcp.git.tools import git_diff
        assert "+v2" in git_diff.call({})

    def test_git_log(self, git_repo):
        from mcp.git.tools import git_log
        assert "initial" in git_log.call({"count": 5})

    def test_git_add_and_commit(self, git_repo):
        from mcp.git.tools import git_add, git_commit, git_log
        (git_repo / "added.txt").write_text("content")
        git_add.call({"paths": ["added.txt"]})
        git_commit.call({"message": "add a file"})
        assert "add a file" in git_log.call({})

    def test_git_failure_raises(self, git_repo):
        from mcp.git import run_git
        with pytest.raises(RuntimeError, match="git .* failed"):
            run_git("rev-parse", "--verify", "nonexistent-ref")


# ---------------------------------------------------------------------------
# Fetch tool
# ---------------------------------------------------------------------------

class TestFetchTool:
    def test_fetch_returns_body(self):
        from unittest.mock import MagicMock, patch
        body = MagicMock()
        body.read.return_value = b"<html>hi</html>"
        body.__enter__ = lambda s: s
        body.__exit__ = MagicMock(return_value=False)

        from mcp.fetch.tools import fetch
        with patch("urllib.request.urlopen", return_value=body) as mock_open:
            result = fetch.call({"url": "https://example.com"})

        assert result == "<html>hi</html>"
        assert mock_open.call_args[0][0].full_url == "https://example.com"

    def test_fetch_rejects_non_http(self):
        from mcp.fetch.tools import fetch
        with pytest.raises(ValueError, match="http"):
            fetch.call({"url": "file:///etc/passwd"})

    def test_fetch_truncates_at_max_chars(self):
        from unittest.mock import MagicMock, patch
        body = MagicMock()
        body.read.return_value = b"y" * 50
        body.__enter__ = lambda s: s
        body.__exit__ = MagicMock(return_value=False)

        from mcp.fetch.tools import fetch
        with patch("urllib.request.urlopen", return_value=body):
            result = fetch.call({"url": "https://example.com", "max_chars": 10})

        assert result.startswith("y" * 10)
        assert "truncated" in result


# ---------------------------------------------------------------------------
# servers.json points at the local servers
# ---------------------------------------------------------------------------

class TestServersJsonMatchesLocalServers:
    def test_every_server_command_is_a_local_module(self):
        import json as _json
        from pathlib import Path

        servers = _json.loads(
            (Path(__file__).resolve().parents[2] / "mcp" / "servers.json").read_text()
        )["servers"]

        for name, spec in servers.items():
            assert spec["command"] == "python", f"{name} should run locally"
            module = spec["args"][-1]
            assert module == f"mcp.{name}", f"{name}: args should invoke its package"
            package_dir = Path(__file__).resolve().parents[2] / "mcp" / name
            assert (package_dir / "__main__.py").is_file(), f"{name}: missing __main__.py"

    def test_every_profile_tool_has_a_matching_implementation(self):
        import json as _json
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        profiles_dir = root / "mcp" / "profiles"

        for profile_file in profiles_dir.glob("*.json"):
            profile = _json.loads(profile_file.read_text())
            for server, tools in profile["allowed_tools"].items():
                if tools == ["*"]:
                    continue
                for tool in tools:
                    module = root / "mcp" / server / "tools" / f"{tool}.py"
                    assert module.is_file(), (
                        f"{profile_file.name}: tool '{tool}' has no implementation "
                        f"at mcp/{server}/tools/{tool}.py"
                    )
