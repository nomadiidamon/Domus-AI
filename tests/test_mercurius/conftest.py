"""Shared fixtures for Mercurius (event bus) tests."""

import pytest


@pytest.fixture(autouse=True)
def _reset_mercurius_bus():
    """Ensure the module-level singleton bus never leaks between tests."""
    import Mercurius

    Mercurius.shutdown_bus(drain=False)
    yield
    Mercurius.shutdown_bus(drain=False)


@pytest.fixture
def bus():
    """A fresh, started EventBus that is always stopped after the test."""
    from Mercurius import EventBus

    b = EventBus()
    b.start()
    yield b
    b.stop(drain=False)
