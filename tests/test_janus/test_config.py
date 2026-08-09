"""
Tests for Janus/config.py

config.py caches loaded config dicts in a module-level `_config_cache`
and auto-loads on import. The root conftest's autouse
`_reset_janus_config_cache` fixture clears that cache before/after every
test, so each test here can assume load_*_config() will actually hit
disk rather than returning a stale cached value from import time or a
previous test.

_get_config_dir() resolves via Janus.paths.find_root() when possible, so
these tests point LOCAL_AI_RUNTIME_ROOT at a disposable directory with
its own config/*.json files rather than touching the real repo's config/.
"""

import json

import pytest

from Janus import config

pytestmark = pytest.mark.janus


@pytest.fixture
def fake_config_root(isolated_runtime_root):
    """isolated_runtime_root with a config/ directory ready to populate."""
    config_dir = isolated_runtime_root / "config"
    config_dir.mkdir()
    return isolated_runtime_root


class TestGetConfigDir:
    def test_resolves_via_find_root(self, isolated_runtime_root):
        (isolated_runtime_root / "config").mkdir()
        result = config._get_config_dir()
        assert result == isolated_runtime_root / "config"


class TestLoadModelsConfig:
    def test_loads_and_parses_file(self, fake_config_root):
        models_file = fake_config_root / "config" / "models.json"
        models_file.write_text(json.dumps({"Mercury": {"base": "test:1b"}}))

        result = config.load_models_config()

        assert result == {"Mercury": {"base": "test:1b"}}

    def test_returns_empty_dict_when_file_missing(self, fake_config_root):
        result = config.load_models_config()
        assert result == {}

    def test_caches_result_across_calls(self, fake_config_root):
        models_file = fake_config_root / "config" / "models.json"
        models_file.write_text(json.dumps({"A": {}}))

        first = config.load_models_config()

        # Mutate the file after the first load — cached call should NOT
        # pick up the change, demonstrating the cache is actually in effect.
        models_file.write_text(json.dumps({"B": {}}))
        second = config.load_models_config()

        assert first == second == {"A": {}}


class TestLoadClaudeConfig:
    def test_loads_and_parses_file(self, fake_config_root):
        claude_file = fake_config_root / "config" / "claude.json"
        claude_file.write_text(json.dumps({"api_key_env": "TEST_KEY"}))

        result = config.load_claude_config()

        assert result == {"api_key_env": "TEST_KEY"}

    def test_returns_empty_dict_when_file_missing(self, fake_config_root):
        assert config.load_claude_config() == {}


class TestLoadRuntimeConfig:
    def test_loads_and_parses_file(self, fake_config_root):
        runtime_file = fake_config_root / "config" / "runtime.json"
        runtime_file.write_text(json.dumps({"mode": "development"}))

        result = config.load_runtime_config()

        assert result == {"mode": "development"}

    def test_returns_empty_dict_when_file_missing(self, fake_config_root):
        assert config.load_runtime_config() == {}


class TestGetModelConfig:
    def test_returns_config_for_known_model(self, fake_config_root):
        models_file = fake_config_root / "config" / "models.json"
        models_file.write_text(json.dumps({"Mercury": {"base": "test:1b"}}))

        result = config.get_model_config("Mercury")

        assert result == {"base": "test:1b"}

    def test_returns_none_for_unknown_model(self, fake_config_root):
        (fake_config_root / "config" / "models.json").write_text(json.dumps({}))
        assert config.get_model_config("DoesNotExist") is None


class TestGetEnv:
    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("TEST_DOMUS_VAR", "hello")
        assert config.get_env("TEST_DOMUS_VAR") == "hello"

    def test_returns_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_DOMUS_VAR_UNSET", raising=False)
        assert config.get_env("TEST_DOMUS_VAR_UNSET", default="fallback") == "fallback"

    def test_default_is_empty_string_when_not_specified(self, monkeypatch):
        monkeypatch.delenv("TEST_DOMUS_VAR_UNSET", raising=False)
        assert config.get_env("TEST_DOMUS_VAR_UNSET") == ""


class TestLoadEnv:
    def test_returns_false_when_env_file_missing(self, fake_config_root):
        assert config.load_env() is False

    def test_returns_true_and_loads_when_env_file_present(self, fake_config_root):
        env_file = fake_config_root / "config" / "ollama.env"
        env_file.write_text("TEST_DOMUS_OLLAMA_VAR=loaded_value\n")

        result = config.load_env()

        assert result is True
        assert config.get_env("TEST_DOMUS_OLLAMA_VAR") == "loaded_value"


class TestLoadAllConfig:
    def test_returns_true_when_any_config_present(self, fake_config_root):
        (fake_config_root / "config" / "models.json").write_text(json.dumps({"A": {}}))
        assert config.load_all_config() is True

    def test_returns_false_when_nothing_present(self, fake_config_root):
        assert config.load_all_config() is False