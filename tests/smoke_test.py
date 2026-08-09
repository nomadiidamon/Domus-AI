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
import os
import argparse
import shutil
import traceback
from pathlib import Path

# Make the project's top-level packages (Hestia, Janus, Mentis, Faber,
# Custos, Mercurius, Lares, DomusAPI, utils) importable regardless of
# where this script is invoked from, by adding src/ to sys.path — that's
# where all of them actually live. Each subpackage has its own __init__.py
# and uses relative imports internally; cross-package imports (e.g.
# Mentis/context.py importing Janus.paths) use absolute imports since
# sibling packages can't use relative imports across package boundaries.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# All writable output this test needs (a fake "host project" dir, temp files,
# etc.) goes here — NEVER inside PROJECT_ROOT. Wiped clean at the start of
# every run so tests stay isolated and repeatable.
TEST_OUTPUT_DIR = Path(__file__).resolve().parent / ".smoke_test_output"


def _tail(text: str, n: int = 800) -> str:
    """Return the last n chars of text — tracebacks/errors print at the END
    of output, so truncating from the front (as [:n] does) hides them."""
    return text if len(text) <= n else "..." + text[-n:]


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
    find_root() locates the Domus-AI repo itself (via the .ai-runtime-marker
    file) and is what config.py uses to find /config. get_config_dir(), by
    contrast, resolves the *host* project's config dir and requires
    initialize_host() to have been called first — that's a separate,
    stateful flow we don't exercise in a stateless smoke test.
    """
    from Janus.paths import find_root
    root = find_root()
    assert root.exists(), f"root does not exist: {root}"
    config_dir = root / "config"
    assert config_dir.exists(), f"repo config dir does not exist: {config_dir}"
    return f"root={root}, config={config_dir}"


def check_config_loads():
    from Janus import config
    models = config.load_models_config()
    runtime_cfg = config.load_runtime_config()
    claude_cfg = config.load_claude_config()
    return f"models={len(models)} keys, runtime_cfg={bool(runtime_cfg)}, claude_cfg={bool(claude_cfg)}"


def check_hardware_detection():
    from Hestia.hardware import detect_hardware
    profile = detect_hardware()
    assert profile is not None
    return f"accelerator={getattr(profile, 'accelerator', '?')}"


def check_model_catalog_import():
    import Hestia.model_catalog  # noqa: F401
    return "imported ok"


def check_session_lifecycle():
    """
    Exercise session.py without touching real OS processes, so this check
    works identically whether or not ollama/claude are installed, and on
    any OS. Uses a tiny fake process object matching the .poll()/.pid/
    .terminate() surface that session.py expects.
    """
    from Faber.session import create_session, get_session, stop_session, get_all_sessions

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


def check_utils_module():
    """utils.py lives at the project root, shared equally by every subsystem."""
    import utils
    assert hasattr(utils, "configure_logging")
    assert hasattr(utils, "load_json")

    # load_json: missing file returns the given default, no exception
    missing = utils.load_json(PROJECT_ROOT / "no_such_file.json", default={"x": 1})
    assert missing == {"x": 1}, f"expected default for missing file, got {missing}"

    # load_json: real file parses correctly
    real = utils.load_json(PROJECT_ROOT / "config" / "models.json", default=None)
    assert real is not None and isinstance(real, dict), "expected config/models.json to parse"

    return "configure_logging + load_json both work as expected"


def check_dependencies_module():
    from Janus.dependencies import DependencyChecker, PythonPackageDependency
    checker = DependencyChecker()
    checker.register_many([
        PythonPackageDependency("psutil", required=True, description="System monitoring"),
    ])
    results = checker.check_all()
    assert "psutil" in results
    return f"checked {len(results)} dependency record(s)"


def check_context_module():
    """context.py is state-heavy; just confirm it imports and constructs cleanly."""
    from Mentis import context
    assert hasattr(context, "RuntimeContext")
    assert hasattr(context, "get_context")
    return "imported ok"


def check_mcp_stub():
    from Custos import mcp
    assert hasattr(mcp, "MCPManager")
    return "imported ok"


def check_stub_packages_import():
    """
    Mercurius (event bus), Lares (agents), and DomusAPI (top-level wrapper)
    have no real implementation yet — this just confirms the package tree
    itself is well-formed (each has a valid __init__.py) so the target
    structure holds together even before the real code lands.
    """
    import Mercurius
    import Lares
    import DomusAPI
    assert hasattr(Mercurius, "__all__")
    assert hasattr(Lares, "__all__")
    assert hasattr(DomusAPI, "__all__")
    return "Mercurius, Lares, DomusAPI import ok (stubs, no behavior yet)"


def check_cli_module_imports():
    """
    Janus/main.py is the CLI entry point (invoked as `python -m Janus`).
    Importing it only proves its top-level imports resolve — it does NOT
    exercise lazy/inline imports inside its functions (e.g.
    `from Mentis.context import ...` called only when a command runs).
    So beyond importing, we also invoke it with the side-effect-free
    "help" command via subprocess to catch import errors that only surface
    at call time.

    NOTE: this runs `python -m Janus` in a genuinely separate subprocess,
    which does NOT inherit this script's own sys.path — so this check
    fails with "No module named Janus" if src/ isn't reachable some other
    way. We set PYTHONPATH explicitly below so this works whether or not
    `pip install -e .` has been run yet.

    IMPORTANT: running main.py triggers RuntimeContext.startup(), which
    creates a .ai-runtime/ working directory (cache, logs, models, memory,
    config, sessions) inside whatever it considers the "host project."
    We must NEVER let that land inside this repo's own project root or any
    subsystem package. We redirect it via LOCAL_AI_RUNTIME_HOST to an
    isolated, disposable directory under TEST_OUTPUT_DIR instead.
    """
    from Janus import main  # noqa: F401
    assert hasattr(main, "main")

    host_dir = TEST_OUTPUT_DIR / "host-project"
    host_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["LOCAL_AI_RUNTIME_HOST"] = str(host_dir)
    # `python -m Janus` only resolves if src/ is on the subprocess's own
    # PYTHONPATH — it does NOT inherit sys.path from this (parent) process.
    # Normally `pip install -e .` (see pyproject.toml) puts src/ on the
    # path permanently; this covers the case where the package hasn't
    # been installed yet, so the smoke test doesn't depend on install
    # order.
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(SRC_DIR) if not existing_pythonpath
        else f"{SRC_DIR}{os.pathsep}{existing_pythonpath}"
    )

    import subprocess
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "Janus", "help"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        raise AssertionError(f"timed out (possible unhandled interactive prompt): {_tail(out)}")

    combined = (proc.stdout or "") + (proc.stderr or "")
    assert "No module named" not in combined, f"import error at call time: {_tail(combined)}"
    assert proc.returncode == 0, f"exit code {proc.returncode}: {_tail(combined)}"

    # Sanity check: confirm host output actually landed in the isolated
    # test dir and NOT inside the real project. Checks both the proper
    # ".ai-runtime" working-dir name AND the bare directory names
    # (cache/logs/models/memory/config/sessions) in case some code path
    # bypasses paths.py and writes them directly into a package dir.
    suspects = ["cache", "logs", "models", "memory", "config", "sessions", ".ai-runtime"]
    subsystem_dirs = [
        SRC_DIR / name
        for name in ("Hestia", "Janus", "Mentis", "Faber", "Custos", "Mercurius", "Lares", "DomusAPI")
    ]
    leaked = []
    for base in [PROJECT_ROOT, *subsystem_dirs]:
        for name in suspects:
            candidate = base / name
            # "config" and "models" legitimately exist as real project dirs
            # at PROJECT_ROOT; only flag them elsewhere (a subsystem dir
            # should never have its own bare cache/config/models/etc.).
            if name in ("config", "models") and base == PROJECT_ROOT:
                continue
            if candidate.exists():
                leaked.append(str(candidate))
    assert not leaked, f"host directories leaked into the real project: {leaked}"

    return f"imported ok; CLI ran with host redirected to {host_dir}"


def check_full_diagnostic():
    """Opt-in: requires ollama/git/etc. to actually be installed on this machine."""
    from Janus.doctor import full_diagnostic
    ok = full_diagnostic()
    return f"full_diagnostic() returned {ok}"


CORE_CHECKS = [
    ("Janus.paths.find_root", check_paths_resolve),
    ("Janus.config.* loads config/*.json", check_config_loads),
    ("utils.configure_logging / load_json", check_utils_module),
    ("Hestia.hardware.detect_hardware", check_hardware_detection),
    ("Hestia.model_catalog imports", check_model_catalog_import),
    ("Janus.dependencies.DependencyChecker", check_dependencies_module),
    ("Faber.session create/get/stop cycle", check_session_lifecycle),
    ("Mentis.context module imports", check_context_module),
    ("Custos.mcp.MCPManager stub imports", check_mcp_stub),
    ("Mercurius/Lares/DomusAPI stub packages import", check_stub_packages_import),
    ("Janus (python -m Janus) CLI", check_cli_module_imports),
]

FULL_ONLY_CHECKS = [
    ("Janus.doctor.full_diagnostic (real system check)", check_full_diagnostic),
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
    print(f"Subsystems:   Hestia, Janus, Mentis, Faber, Custos, Mercurius, Lares, DomusAPI")
    print(f"Test output:  {TEST_OUTPUT_DIR} (isolated, wiped each run)")
    print("-" * 60)

    # Stale __pycache__ from before a restructure step can shadow current
    # source (Python may load an old .pyc instead of recompiling), causing
    # confusing failures that don't reproduce after a clean checkout. Since
    # this repo is under active restructuring, clear caches every run so
    # failures always reflect the current source on disk.
    cleared = []
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        if TEST_OUTPUT_DIR in pycache.parents:
            continue
        shutil.rmtree(pycache, ignore_errors=True)
        cleared.append(str(pycache))
    if cleared:
        print(f"Cleared {len(cleared)} stale __pycache__ dir(s) before running")
        print("-" * 60)

    # Start every run from a clean, isolated output directory so nothing
    # leaks into the real project and nothing from a previous run leaks in.
    if TEST_OUTPUT_DIR.exists():
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True)

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