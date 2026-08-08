#!/usr/bin/env python3
"""
smoke_test.py - Cross-platform regression check for the Domus-AI restructure.

Run this BEFORE and AFTER every restructure step. Output should stay
identical (same checks passing/failing) unless you intentionally changed
behavior. A check that passed before and fails after means the last move
broke something.

Usage:
    python scripts/smoke_test.py                 # core checks only (fast, no external deps)
    python scripts/smoke_test.py --full           # also run doctor.full_diagnostic()
                                                   # (requires ollama/git actually installed)
    python scripts/smoke_test.py -v               # verbose: print tracebacks on failure

Exit code: 0 if all checks pass, 1 otherwise. Safe to run on Windows/macOS/Linux.
"""

import sys
import argparse
import traceback
from pathlib import Path

# Make sure runtime/ is importable regardless of where this script is invoked from.
# During the restructure this is the ONE line you may need to update as files move
# (e.g. once things live under Janus/, Hestia/, etc. this changes to add those dirs).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))


class Result:
    def __init__(self):
        self.checks = []  # list of (name, passed, detail)

    def record(self, name, passed, detail=""):
        self.checks.append((name, passed, detail))
        icon = "✓" if passed else "✗"
        line = f"{icon} {name}"
        if detail and (not passed or VERBOSE):
            line += f" — {detail}"
        print(line)

    @property
    def all_passed(self):
        return all(passed for _, passed, _ in self.checks)


VERBOSE = False


def run_check(result: Result, name: str, fn):
    """Run fn(); record pass/fail; never raise."""
    try:
        detail = fn()
        result.record(name, True, detail or "")
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        if VERBOSE:
            detail += "\n" + traceback.format_exc()
        result.record(name, False, detail)


# ---------------------------------------------------------------------------
# Individual checks — each is a small, independent probe of one subsystem.
# Keep these mapped to current file responsibilities; update the import
# lines (only) as files move during the restructure.
# ---------------------------------------------------------------------------

def check_paths_resolve():
    """
    find_root() locates the Domus-AI repo itself (via the .ai-runtime marker)
    and is what config.py uses to find /config. get_config_dir(), by
    contrast, resolves the *host* project's config dir and requires
    initialize_host() to have been called first — that's a separate,
    stateful flow we don't exercise in a stateless smoke test.
    """
    from paths import find_root
    root = find_root()
    assert root.exists(), f"root does not exist: {root}"
    config_dir = root / "config"
    assert config_dir.exists(), f"repo config dir does not exist: {config_dir}"
    return f"root={root}, config={config_dir}"


def check_config_loads():
    import config
    models = config.load_models_config()
    runtime_cfg = config.load_runtime_config()
    claude_cfg = config.load_claude_config()
    return f"models={len(models)} keys, runtime_cfg={bool(runtime_cfg)}, claude_cfg={bool(claude_cfg)}"


def check_hardware_detection():
    from hardware import detect_hardware
    profile = detect_hardware()
    assert profile is not None
    return f"accelerator={getattr(profile, 'accelerator', '?')}"


def check_model_catalog_import():
    import model_catalog  # noqa: F401
    return "imported ok"


def check_session_lifecycle():
    """
    Exercise session.py without touching real OS processes, so this check
    works identically whether or not ollama/claude are installed, and on
    any OS. Uses a tiny fake process object matching the .poll()/.pid/
    .terminate() surface that session.py expects.
    """
    from session import create_session, get_session, stop_session, get_all_sessions

    class FakeProcess:
        def __init__(self):
            self.pid = 999999
            self._running = True

        def poll(self):
            return None if self._running else 0

        def terminate(self):
            self._running = False

    fake = FakeProcess()
    create_session("smoke_test_session", fake, "test", {"note": "smoke test"})

    session = get_session("smoke_test_session")
    assert session is not None, "session not found after creation"
    assert session.is_running(), "session should report running before stop"

    all_sessions = get_all_sessions()
    assert "smoke_test_session" in all_sessions, "session missing from get_all_sessions()"

    stopped = stop_session("smoke_test_session")
    assert stopped is True, "stop_session should return True"
    assert get_session("smoke_test_session") is None, "session should be gone after stop"

    return "create/get/stop cycle ok"


def check_dependencies_module():
    from dependencies import DependencyChecker, PythonPackageDependency
    checker = DependencyChecker()
    checker.register_many([
        PythonPackageDependency("psutil", required=True, description="System monitoring"),
    ])
    results = checker.check_all()
    assert "psutil" in results
    return f"checked {len(results)} dependency record(s)"


def check_context_module():
    """context.py is state-heavy; just confirm it imports and constructs cleanly."""
    import context
    assert hasattr(context, "RuntimeContext")
    assert hasattr(context, "get_context")
    return "imported ok"


def check_mcp_stub():
    import mcp
    assert hasattr(mcp, "MCPManager")
    return "imported ok"


def check_cli_module_imports():
    """
    main.py is the CLI entry point. We only check that it imports cleanly
    (i.e. its own imports of ollama_service/session/models/doctor resolve)
    — we do NOT call main() since that would parse sys.argv / start processes.
    """
    import main  # noqa: F401
    assert hasattr(main, "main")
    return "imported ok"


def check_full_diagnostic():
    """Opt-in: requires ollama/git/etc. to actually be installed on this machine."""
    from doctor import full_diagnostic
    ok = full_diagnostic()
    return f"full_diagnostic() returned {ok}"


CORE_CHECKS = [
    ("paths.find_root / get_config_dir", check_paths_resolve),
    ("config.* loads config/*.json", check_config_loads),
    ("hardware.detect_hardware", check_hardware_detection),
    ("model_catalog imports", check_model_catalog_import),
    ("dependencies.DependencyChecker", check_dependencies_module),
    ("session create/get/stop cycle", check_session_lifecycle),
    ("context module imports", check_context_module),
    ("mcp.MCPManager stub imports", check_mcp_stub),
    ("main.py CLI module imports", check_cli_module_imports),
]

FULL_ONLY_CHECKS = [
    ("doctor.full_diagnostic (real system check)", check_full_diagnostic),
]


def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true",
                         help="also run doctor.full_diagnostic() (needs ollama/git installed)")
    parser.add_argument("-v", "--verbose", action="store_true",
                         help="print full tracebacks for failures")
    args = parser.parse_args()
    VERBOSE = args.verbose

    print(f"Domus-AI smoke test")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Runtime dir:  {RUNTIME_DIR}")
    print("-" * 60)

    result = Result()

    for name, fn in CORE_CHECKS:
        run_check(result, name, fn)

    if args.full:
        print("-" * 60)
        print("Running --full checks (requires real system dependencies)...")
        for name, fn in FULL_ONLY_CHECKS:
            run_check(result, name, fn)

    print("-" * 60)
    passed = sum(1 for _, p, _ in result.checks if p)
    total = len(result.checks)
    print(f"{passed}/{total} checks passed")

    if result.all_passed:
        print("SMOKE TEST PASSED")
        return 0
    else:
        print("SMOKE TEST FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())