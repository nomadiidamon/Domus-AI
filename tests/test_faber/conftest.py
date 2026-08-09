"""Shared fixtures for Faber (session/process management) tests."""

import pytest


class FakeProcess:
    """
    Stand-in for subprocess.Popen matching the small surface Faber
    actually uses: .pid, .poll(), .terminate(). Using a real Popen in
    tests would mean actually spawning OS processes (slow, and Faber's
    real commands like "ollama serve" may not even be installed on the
    test machine) — this fixture keeps the tests fast and hermetic.
    """

    def __init__(self, pid=12345):
        self.pid = pid
        self.terminated = False
        self._running = True

    def poll(self):
        return None if self._running else 0

    def terminate(self):
        self.terminated = True
        self._running = False


@pytest.fixture
def fake_process():
    return FakeProcess()


@pytest.fixture
def fake_process_factory():
    """Factory for tests that need more than one distinct fake process."""
    def _make(pid=12345):
        return FakeProcess(pid=pid)
    return _make