"""
Tests for utils.py — shared helpers used by every subsystem.

utils.py is deliberately small (logging setup + JSON loading), so this
suite is small too, but it's the one module every other subsystem
depends on, so regressions here ripple everywhere.
"""

import json
import logging

import pytest

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
        fake_logger = logging.getLogger("test.load_json.missing")
        messages = []
        fake_logger.warning = lambda msg: messages.append(msg)

        utils.load_json(missing, default=None, logger=fake_logger)

        assert len(messages) == 1
        assert "nope.json" in messages[0]

    def test_logs_error_on_malformed_json(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not valid")
        fake_logger = logging.getLogger("test.load_json.broken")
        messages = []
        fake_logger.error = lambda msg: messages.append(msg)

        utils.load_json(path, default=None, logger=fake_logger)

        assert len(messages) == 1

    def test_no_logging_when_logger_omitted(self, tmp_path):
        """Should not raise even though no logger was passed for a missing file."""
        missing = tmp_path / "nope.json"
        utils.load_json(missing, default=[])  # must not raise


class TestConfigureLogging:
    def test_is_idempotent(self):
        """
        Calling configure_logging() multiple times must not raise and
        must not add duplicate handlers each time (matches
        logging.basicConfig's "only takes effect once" semantics).
        """
        root = logging.getLogger()
        handlers_before = list(root.handlers)

        utils.configure_logging()
        utils.configure_logging()
        utils.configure_logging()

        # We can't assert exact handler count (other tests/pytest itself
        # may configure logging), but a second/third call must not throw
        # and must not be the thing adding new handlers each time.
        handlers_after_first = len(root.handlers)
        utils.configure_logging()
        assert len(root.handlers) == handlers_after_first

    def test_accepts_custom_level_and_format(self):
        # Should not raise regardless of whether logging was already
        # configured elsewhere in the test run.
        utils.configure_logging(level=logging.DEBUG, fmt="%(message)s")