"""
Tests for Faber/session.py

session.py tracks running processes in a module-level `_sessions` dict.
The `_reset_faber_sessions` autouse fixture in the root conftest clears
that dict before/after every test, so tests here can assume a clean
slate without needing to know about that global themselves.
"""

import pytest

from Faber.session import (
    Session,
    create_session,
    get_session,
    get_session_by_pid,
    get_all_sessions,
    get_status,
    stop_session,
    remove_session,
)

pytestmark = pytest.mark.faber


class TestCreateAndGetSession:
    def test_create_session_returns_session_instance(self, fake_process):
        session = create_session("test1", fake_process, "test", {"k": "v"})
        assert isinstance(session, Session)
        assert session.name == "test1"
        assert session.session_type == "test"
        assert session.metadata == {"k": "v"}

    def test_create_session_defaults_metadata_to_empty_dict(self, fake_process):
        session = create_session("test1", fake_process, "test")
        assert session.metadata == {}

    def test_get_session_returns_created_session(self, fake_process):
        create_session("test1", fake_process, "test")
        assert get_session("test1") is not None
        assert get_session("test1").name == "test1"

    def test_get_session_returns_none_for_unknown_name(self):
        assert get_session("does_not_exist") is None

    def test_get_session_by_pid(self, fake_process):
        create_session("test1", fake_process, "test")
        found = get_session_by_pid(fake_process.pid)
        assert found is not None
        assert found.name == "test1"

    def test_get_session_by_pid_returns_none_when_not_found(self):
        assert get_session_by_pid(999999) is None

    def test_get_all_sessions_returns_copy(self, fake_process):
        create_session("test1", fake_process, "test")
        all_sessions = get_all_sessions()
        assert "test1" in all_sessions

        # Mutating the returned dict must not affect the internal store.
        all_sessions["test2"] = "should not leak in"
        assert get_session("test2") is None


class TestSessionIsRunning:
    def test_is_running_true_while_process_alive(self, fake_process):
        session = create_session("test1", fake_process, "test")
        assert session.is_running() is True

    def test_is_running_false_after_process_exits(self, fake_process):
        session = create_session("test1", fake_process, "test")
        fake_process._running = False
        assert session.is_running() is False


class TestStopSession:
    def test_stop_session_terminates_process(self, fake_process):
        create_session("test1", fake_process, "test")
        result = stop_session("test1")
        assert result is True
        assert fake_process.terminated is True

    def test_stop_session_removes_from_registry(self, fake_process):
        create_session("test1", fake_process, "test")
        stop_session("test1")
        assert get_session("test1") is None

    def test_stop_session_returns_false_for_unknown_session(self):
        assert stop_session("does_not_exist") is False


class TestRemoveSession:
    def test_remove_session_deletes_entry(self, fake_process):
        create_session("test1", fake_process, "test")
        remove_session("test1")
        assert get_session("test1") is None

    def test_remove_session_is_noop_for_unknown_name(self):
        remove_session("does_not_exist")  # must not raise


class TestGetStatus:
    def test_get_status_empty_when_no_sessions(self):
        assert get_status() == []

    def test_get_status_reports_each_session(self, fake_process_factory):
        p1 = fake_process_factory(pid=111)
        p2 = fake_process_factory(pid=222)
        create_session("s1", p1, "model", {"model": "a"})
        create_session("s2", p2, "service")

        status = get_status()

        assert len(status) == 2
        names = {entry["name"] for entry in status}
        assert names == {"s1", "s2"}
        for entry in status:
            assert set(entry.keys()) == {"name", "type", "running", "pid", "started"}

    def test_get_status_reflects_running_state(self, fake_process):
        create_session("s1", fake_process, "model")
        fake_process._running = False

        status = get_status()

        assert status[0]["running"] is False


class TestSessionIsolationBetweenTests:
    """
    Sanity check on the autouse _reset_faber_sessions fixture itself:
    confirms the registry really does start empty each test, i.e. that a
    session created in one test can't leak into another.
    """

    def test_registry_starts_empty(self):
        assert get_all_sessions() == {}