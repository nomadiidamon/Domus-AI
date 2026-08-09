"""
conftest.py - Shared pytest configuration and fixtures for the whole suite.

This file is auto-loaded by pytest before any test runs. Its two jobs:

1. Make the project's top-level packages (Hestia, Janus, Mentis, Faber,
   Custos, Mercurius, Lares, DomusAPI, utils) importable, the same way
   tests/smoke_test.py did it — by adding src/ to sys.path. Tests then
   just do `from Hestia.hardware import detect_hardware` etc.

2. Provide fixtures shared across every module's tests: an isolated,
   disposable "host project" directory (so nothing a test does ever
   writes into this repo or a real project), and fixtures that reset
   process-wide global/module-level state between tests so one test's
   side effects can't leak into another.

Everything here is intentionally boring — no test *behavior* lives in
this file, only shared plumbing. Module-specific fixtures belong in each
module's own conftest.py (e.g. tests/test_hestia/conftest.py).
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ---------------------------------------------------------------------------
# Isolated "host project" directory
# ---------------------------------------------------------------------------
# Several modules (Janus.paths, Mentis.context) write to a "host project"
# directory once initialized/started. We NEVER want that landing inside
# this repo. tmp_path (built into pytest) already gives each test its own
# throwaway directory; this fixture just also points LOCAL_AI_RUNTIME_HOST
# at it and creates the host marker file paths.py looks for, then cleans
# up the env var afterward so tests don't bleed into each other.
@pytest.fixture
def host_project_dir(tmp_path, monkeypatch):
    """A disposable directory pre-registered as the host project root."""
    host_dir = tmp_path / "host-project"
    host_dir.mkdir()
    monkeypatch.setenv("LOCAL_AI_RUNTIME_HOST", str(host_dir))

    # Reset Janus.paths' in-memory cache of the host root, if the module
    # has already been imported by an earlier test, so this test doesn't
    # inherit a stale value set via set_host_project_root().
    if "Janus.paths" in sys.modules:
        sys.modules["Janus.paths"]._host_project_root = None

    yield host_dir

    if "Janus.paths" in sys.modules:
        sys.modules["Janus.paths"]._host_project_root = None


@pytest.fixture
def isolated_runtime_root(tmp_path, monkeypatch):
    """
    A disposable directory pre-registered as the Domus-AI *runtime source*
    root (distinct from the host project root above), with a
    .domus-marker file already in place. Use this for tests that need
    Janus.paths.find_root() to resolve to a controlled, throwaway
    location instead of the real repo checkout.
    """
    root_dir = tmp_path / "runtime-root"
    root_dir.mkdir()
    (root_dir / ".domus-marker").touch()
    monkeypatch.setenv("LOCAL_AI_RUNTIME_ROOT", str(root_dir))
    yield root_dir


# ---------------------------------------------------------------------------
# Module-level cache resets
# ---------------------------------------------------------------------------
# Janus.config caches loaded config dicts at module level (_config_cache)
# and even auto-loads on import. That's convenient for the app but
# dangerous for tests: one test's config mutation (or config-dir
# monkeypatch) can silently leak into the next test. This fixture clears
# the cache before AND after every test; it's a no-op if Janus.config
# hasn't been imported yet.
@pytest.fixture(autouse=True)
def _reset_janus_config_cache():
    def _clear():
        if "Janus.config" in sys.modules:
            cache = sys.modules["Janus.config"]._config_cache
            for key in cache:
                cache[key] = None

    _clear()
    yield
    _clear()


# Faber.session keeps a module-level `_sessions` dict of everything
# "started" during a test (fake or real). Without resetting this,
# session names created in one test (e.g. "ollama_server") would appear
# already-running in the next test and short-circuit start_* logic.
@pytest.fixture(autouse=True)
def _reset_faber_sessions():
    def _clear():
        if "Faber.session" in sys.modules:
            sys.modules["Faber.session"]._sessions.clear()

    _clear()
    yield
    _clear()


# Faber.models keeps a module-level `_context` binding set via
# set_context(). Reset it so a RuntimeContext bound in one test doesn't
# silently receive load/unload callbacks triggered by a later test.
@pytest.fixture(autouse=True)
def _reset_faber_models_context():
    def _clear():
        if "Faber.models" in sys.modules:
            sys.modules["Faber.models"]._context = None

    _clear()
    yield
    _clear()


# Mentis.context keeps a module-level `_global_context` singleton, set by
# get_context()/initialize_context(). Reset it so a global RuntimeContext
# created in one test doesn't leak into another via get_context().
@pytest.fixture(autouse=True)
def _reset_mentis_global_context():
    def _clear():
        if "Mentis.context" in sys.modules:
            sys.modules["Mentis.context"]._global_context = None

    _clear()
    yield
    _clear()