"""Shared fixtures for DomusAPI tests."""


import pytest


@pytest.fixture(autouse=True)
def _reset_domusapi_state():
    """DomusAPI keeps a module-level _context; reset it around each test."""
    import DomusAPI
    DomusAPI._context = None
    yield
    DomusAPI._context = None
