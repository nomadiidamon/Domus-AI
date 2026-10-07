"""
Tests for packaged runtime data (DomusData, DomusMCP) and how Janus.paths
locates it.

Janus.paths resolves bundled data with importlib.resources unless
LOCAL_AI_RUNTIME_ROOT overrides it. These tests cover the default branch
(what a non-editable install uses) and the contents of a built wheel.
"""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from Janus import config, paths

pytestmark = pytest.mark.janus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

CONFIG_FILES = ["claude.json", "models.json", "runtime.json", "ollama.env"]


@pytest.fixture
def no_override(monkeypatch):
    monkeypatch.delenv("LOCAL_AI_RUNTIME_ROOT", raising=False)


class TestPackagedLookup:
    def test_get_config_path_uses_domusdata(self, no_override):
        result = paths.get_config_path()
        assert result.name == "config" and result.parent.name == "DomusData"
        assert result.is_dir()

    def test_get_modelfiles_path_uses_domusdata(self, no_override):
        result = paths.get_modelfiles_path()
        assert result.name == "Modelfiles" and result.parent.name == "DomusData"
        assert result.is_dir()

    def test_get_mcp_path_uses_domusmcp(self, no_override):
        result = paths.get_mcp_path()
        assert result.name == "DomusMCP"
        assert (result / "servers.json").is_file()

    def test_config_dir_matches_paths(self, no_override):
        assert config._get_config_dir() == paths.get_config_path()


class TestOverridePrecedence:
    def test_env_root_wins_over_packaged_data(self, isolated_runtime_root):
        assert paths.get_config_path() == isolated_runtime_root / "config"
        assert paths.get_modelfiles_path() == isolated_runtime_root / "Modelfiles"
        assert paths.get_mcp_path() == isolated_runtime_root / "mcp"


class TestPackagedDataComplete:
    @pytest.mark.parametrize("name", CONFIG_FILES)
    def test_config_file_present(self, no_override, name):
        assert (paths.get_config_path() / name).is_file()

    def test_every_model_has_a_bundled_modelfile(self, no_override):
        models = json.loads((paths.get_config_path() / "models.json").read_text())
        for model in models:
            modelfile = paths.get_modelfiles_path() / model / f"Modelfile.{model}"
            assert modelfile.is_file(), f"missing bundled Modelfile for {model}"

    def test_every_model_has_an_mcp_profile(self, no_override):
        models = json.loads((paths.get_config_path() / "models.json").read_text())
        for model in models:
            assert (paths.get_mcp_path() / "profiles" / f"{model}.json").is_file()


@pytest.fixture(scope="module")
def wheel_names(tmp_path_factory):
    out = tmp_path_factory.mktemp("wheel")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(PROJECT_ROOT),
         "--no-deps", "-w", str(out), "-q"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"wheel build unavailable: {result.stderr.strip()[-300:]}")
    wheel = next(out.glob("domus_ai-*.whl"))
    return set(zipfile.ZipFile(wheel).namelist())


@pytest.mark.slow
class TestBuiltWheel:
    @pytest.mark.parametrize("name", CONFIG_FILES)
    def test_wheel_has_config(self, wheel_names, name):
        assert f"DomusData/config/{name}" in wheel_names

    def test_wheel_has_modelfiles(self, wheel_names):
        for model in ["Analyst", "Mercury", "Minerva", "Vulcan"]:
            assert f"DomusData/Modelfiles/{model}/Modelfile.{model}" in wheel_names

    def test_wheel_has_mcp_servers_and_profiles(self, wheel_names):
        assert "DomusMCP/servers.json" in wheel_names
        for server in ["filesystem", "git", "fetch"]:
            assert f"DomusMCP/{server}/__main__.py" in wheel_names
        for model in ["Analyst", "Mercury", "Minerva", "Vulcan"]:
            assert f"DomusMCP/profiles/{model}.json" in wheel_names

    def test_wheel_has_no_top_level_mcp(self, wheel_names):
        assert not any(n.startswith("mcp/") for n in wheel_names)
