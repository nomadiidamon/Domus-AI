"""
Tests for utils.py - shared helpers used by every subsystem.

utils.py is deliberately small (logging setup + JSON loading), so this
suite is small too, but it's the one module every other subsystem
depends on, so regressions here ripple everywhere.
"""

import json
from unittest.mock import Mock

import pytest
import platformdirs
from Auctor.Livy import Livy
from platformdirs import macos, unix, windows

import utils

pytestmark = pytest.mark.utils


class TestLoadJson:
    def test_returns_default_when_file_missing(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        result = utils.load_json(missing, default={"x": 1})
        assert result == {"x": 1}

    def test_returns_none_default_when_not_specified(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        assert utils.load_json(missing) is None

    def test_parses_valid_json_file(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"a": 1, "b": [1, 2, 3]}))

        result = utils.load_json(path, default=None)

        assert result == {"a": 1, "b": [1, 2, 3]}

    def test_returns_default_on_malformed_json(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not valid json")

        result = utils.load_json(path, default={"fallback": True})

        assert result == {"fallback": True}

    def test_accepts_string_path(self, tmp_path):
        """load_json should Path()-coerce string paths, not just accept Path objects."""
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"ok": True}))

        result = utils.load_json(str(path), default=None)

        assert result == {"ok": True}

    def test_logs_warning_when_file_missing(self, tmp_path):
        missing = tmp_path / "nope.json"
        fake_logger = Mock()
        messages = []
        fake_logger.warning = lambda msg: messages.append(msg)

        utils.load_json(missing, default=None, logger=fake_logger)

        assert len(messages) == 1
        assert "nope.json" in messages[0]

    def test_logs_error_on_malformed_json(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not valid")
        fake_logger = Mock()
        messages = []
        fake_logger.error = lambda msg: messages.append(msg)

        utils.load_json(path, default=None, logger=fake_logger)

        assert len(messages) == 1

    def test_no_logging_when_logger_omitted(self, tmp_path):
        """Should not raise even though no logger was passed for a missing file."""
        missing = tmp_path / "nope.json"
        utils.load_json(missing, default=[])  # must not raise


class TestConfigureLogging:
    @pytest.fixture
    def isolated_livy(self, monkeypatch):
        instance = Livy("DomusTests")
        monkeypatch.setattr(utils, "livy", instance)
        yield instance
        instance.shutdown()

    def test_categories_share_instance_and_track_failures(self, isolated_livy, tmp_path):
        log_file = tmp_path / "domus.log"
        utils.configure_logging(log_file)
        janus = utils.get_log_category("Janus.main")
        assert janus is utils.get_log_category("Janus.config")
        mentis = utils.get_log_category("Mentis.context")
        assert janus is not mentis
        janus.info("started")
        mentis.error("failed", operation="startup")
        assert mentis.get_last_failure().category == "Mentis"
        assert janus.get_last_failure() is None
        text = log_file.read_text()
        assert "[Janus] started" in text
        assert "[Mentis] failed operation='startup'" in text

    def test_switches_destination_without_replacing_categories(self, isolated_livy, tmp_path):
        first = tmp_path / "first.log"
        second = tmp_path / "second.log"
        utils.configure_logging(first)
        category = utils.get_log_category("Faber.models")
        category.info("first")
        utils.configure_logging(second)
        utils.configure_logging(second)
        assert category is utils.get_log_category("Faber.messaging")
        category.info("second")
        assert "[Faber] first" in first.read_text()
        assert "[Faber] second" in second.read_text()

    def test_failed_switch_restores_previous_destination(self, isolated_livy, tmp_path):
        previous = tmp_path / "previous.log"
        utils.configure_logging(previous)
        category = utils.get_log_category("Custos")
        blocked = tmp_path / "not-a-directory"
        blocked.write_text("file")
        with pytest.raises(RuntimeError, match="Livy initialization failed"):
            utils.configure_logging(blocked / "new.log")
        category.warning("still available")
        assert "[Custos] still available" in previous.read_text()

    def test_default_path_can_be_configured(self, isolated_livy, tmp_path, monkeypatch):
        log_file = tmp_path / "custom.log"
        monkeypatch.setenv("DOMUS_LOG_PATH", str(log_file))
        utils.get_log_category("DomusAPI").info("ready")
        assert "[DomusAPI] ready" in log_file.read_text()

    @pytest.mark.parametrize("backend,subdirectory", [
        (unix.Unix, ("domus-ai", "log")),
        (macos.MacOS, ("domus-ai",)),
        (windows.Windows, ("domus-ai", "Logs")),
    ])
    def test_platform_default_log_paths(self, isolated_livy, tmp_path, monkeypatch, backend, subdirectory):
        monkeypatch.delenv("DOMUS_LOG_PATH", raising=False)
        monkeypatch.setattr(platformdirs, "PlatformDirs", backend)
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        monkeypatch.setattr(macos, "expand_user", lambda path: str(tmp_path))
        monkeypatch.setattr(windows, "get_win_folder", lambda name: str(tmp_path))
        utils.get_log_category("Janus").info("ready")
        log_file = tmp_path.joinpath(*subdirectory, "domus.log")
        assert "[Janus] ready" in log_file.read_text()