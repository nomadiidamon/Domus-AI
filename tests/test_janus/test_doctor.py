"""
Tests for Janus/doctor.py

doctor.py orchestrates DependencyChecker (already covered by
test_dependencies.py), an HTTP health check against a local Ollama
server, an `ollama list` subprocess call, and MCP config file reading.
Every external touchpoint (urllib, subprocess, the dependency checker
itself) is mocked so these tests never depend on Ollama, git, or any
other tool actually being installed on the machine running the suite.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from Janus import doctor

pytestmark = pytest.mark.janus


class TestBuildChecker:
    def test_registers_expected_dependency_names(self):
        checker = doctor._build_checker()
        assert set(checker.dependencies.keys()) == {
            "psutil", "packaging", "python-dotenv", "nvidia-ml-py",
            "python", "ollama", "git", "claude",
        }

    def test_claude_is_optional(self):
        checker = doctor._build_checker()
        assert checker.dependencies["claude"].required is False

    def test_git_is_required(self):
        checker = doctor._build_checker()
        assert checker.dependencies["git"].required is True


class TestCheckDependencies:
    def test_all_satisfied_true_when_everything_healthy(self):
        fake_checker = MagicMock()
        fake_dep = MagicMock(required=True)
        fake_checker.dependencies = {"pkg": fake_dep}
        fake_checker.check_all.return_value = {
            "pkg": MagicMock(is_healthy=True, version="1.0", message="ok"),
        }
        fake_checker.get_summary.return_value = {}

        with patch("Janus.doctor._build_checker", return_value=fake_checker):
            all_ok, status = doctor.check_dependencies()

        assert all_ok is True
        assert status == {"pkg": True}

    def test_all_satisfied_false_when_required_dep_missing(self):
        fake_checker = MagicMock()
        fake_dep = MagicMock(required=True)
        fake_dep.get_install_instructions.return_value = "pip install pkg"
        fake_checker.dependencies = {"pkg": fake_dep}
        fake_checker.check_all.return_value = {
            "pkg": MagicMock(is_healthy=False, version=None, message="missing"),
        }
        fake_checker.get_summary.return_value = {}

        with patch("Janus.doctor._build_checker", return_value=fake_checker):
            all_ok, status = doctor.check_dependencies()

        assert all_ok is False
        assert status == {"pkg": False}

    def test_optional_missing_dep_does_not_fail_overall_check(self):
        fake_checker = MagicMock()
        fake_dep = MagicMock(required=False)
        fake_dep.get_install_instructions.return_value = "brew install claude"
        fake_checker.dependencies = {"claude": fake_dep}
        fake_checker.check_all.return_value = {
            "claude": MagicMock(is_healthy=False, version=None, message="missing"),
        }
        fake_checker.get_summary.return_value = {}

        with patch("Janus.doctor._build_checker", return_value=fake_checker):
            all_ok, status = doctor.check_dependencies()

        assert all_ok is True
        assert status == {"claude": False}


class TestCheckOllamaServerRunning:
    def test_true_when_urlopen_succeeds(self):
        with patch("urllib.request.urlopen", return_value=MagicMock()):
            assert doctor._check_ollama_server_running() is True

    def test_false_on_url_error(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            assert doctor._check_ollama_server_running() is False

    def test_false_on_unexpected_exception(self):
        with patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
            assert doctor._check_ollama_server_running() is False


class TestCheckModels:
    def test_returns_false_empty_when_server_not_running(self):
        with patch("Janus.doctor._check_ollama_server_running", return_value=False):
            found, models = doctor.check_models()
        assert found is False
        assert models == []

    def test_parses_model_names_from_ollama_list_output(self):
        fake_output = "NAME\tID\tSIZE\nmercury:latest\tabc123\t4GB\nvulcan:latest\tdef456\t8GB\n"
        fake_result = MagicMock(returncode=0, stdout=fake_output, stderr="")

        with patch("Janus.doctor._check_ollama_server_running", return_value=True), \
             patch("subprocess.run", return_value=fake_result):
            found, models = doctor.check_models()

        assert found is True
        assert models == ["mercury:latest", "vulcan:latest"]

    def test_returns_false_when_no_models_installed(self):
        fake_result = MagicMock(returncode=0, stdout="NAME\tID\tSIZE\n", stderr="")

        with patch("Janus.doctor._check_ollama_server_running", return_value=True), \
             patch("subprocess.run", return_value=fake_result):
            found, models = doctor.check_models()

        assert found is False
        assert models == []

    def test_returns_false_when_ollama_list_nonzero_exit(self):
        fake_result = MagicMock(returncode=1, stdout="", stderr="error")

        with patch("Janus.doctor._check_ollama_server_running", return_value=True), \
             patch("subprocess.run", return_value=fake_result):
            found, models = doctor.check_models()

        assert found is False
        assert models == []

    def test_returns_false_when_ollama_not_found(self):
        with patch("Janus.doctor._check_ollama_server_running", return_value=True), \
             patch("subprocess.run", side_effect=FileNotFoundError):
            found, models = doctor.check_models()

        assert found is False
        assert models == []

    def test_returns_false_on_timeout(self):
        import subprocess as sp
        with patch("Janus.doctor._check_ollama_server_running", return_value=True), \
             patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="ollama", timeout=5)):
            found, models = doctor.check_models()

        assert found is False
        assert models == []


class TestCheckMcp:
    def test_returns_false_when_config_file_missing(self, tmp_path):
        with patch("Janus.paths.get_mcp_path", return_value=tmp_path):
            ok, config = doctor.check_mcp()
        assert ok is False
        assert config == {}

    def test_returns_true_and_config_when_servers_present(self, tmp_path):
        servers_file = tmp_path / "servers.json"
        servers_file.write_text(json.dumps({"filesystem": {}, "github": {}}))

        with patch("Janus.paths.get_mcp_path", return_value=tmp_path):
            ok, config = doctor.check_mcp()

        assert ok is True
        assert config == {"filesystem": {}, "github": {}}

    def test_returns_false_when_config_is_empty(self, tmp_path):
        servers_file = tmp_path / "servers.json"
        servers_file.write_text(json.dumps({}))

        with patch("Janus.paths.get_mcp_path", return_value=tmp_path):
            ok, config = doctor.check_mcp()

        assert ok is False
        assert config == {}

    def test_returns_false_on_malformed_json(self, tmp_path):
        servers_file = tmp_path / "servers.json"
        servers_file.write_text("{not valid json")

        with patch("Janus.paths.get_mcp_path", return_value=tmp_path):
            ok, config = doctor.check_mcp()

        assert ok is False
        assert config == {}


class TestFullDiagnostic:
    def test_returns_true_when_dependencies_ok(self):
        with patch("Janus.doctor.check_dependencies", return_value=(True, {})), \
             patch("Janus.doctor.check_models", return_value=(True, ["mercury"])), \
             patch("Janus.doctor.check_mcp", return_value=(True, {})):
            result = doctor.full_diagnostic()
        assert result is True

    def test_returns_false_when_dependencies_fail_even_if_models_and_mcp_ok(self):
        with patch("Janus.doctor.check_dependencies", return_value=(False, {})), \
             patch("Janus.doctor.check_models", return_value=(True, [])), \
             patch("Janus.doctor.check_mcp", return_value=(True, {})):
            result = doctor.full_diagnostic()
        assert result is False

    def test_true_even_if_models_or_mcp_have_warnings(self):
        """Only dependency status is treated as pass/fail; models/MCP are advisory."""
        with patch("Janus.doctor.check_dependencies", return_value=(True, {})), \
             patch("Janus.doctor.check_models", return_value=(False, [])), \
             patch("Janus.doctor.check_mcp", return_value=(False, {})):
            result = doctor.full_diagnostic()
        assert result is True