# Handles installing dependencies. Ollama Installed? Claude Code Installed? Python Installed? Git Installed?
# Called from install.py in root directory.

"""
installer.py - Installation logic for Local AI Runtime.

Checks all required dependencies, attempts auto-repair where possible,
and reports what still needs manual action. Called from install.py at the
project root.

Relies on DependencyChecker, PythonPackageDependency, and
SystemCommandDependency from dependencies.py — no duplicate logic here.
"""

import sys
import logging
import platform
import subprocess
from pathlib import Path
from typing import Tuple

from dependencies import (
    DependencyChecker,
    DependencyStatus,
    PythonPackageDependency,
    SystemCommandDependency,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Manual install URLs — shown when auto-repair is not possible
# ---------------------------------------------------------------------------

INSTALL_URLS = {
    "ollama":  "https://ollama.com/download",
    "git":     "https://git-scm.com/downloads",
    "claude":  "https://github.com/anthropics/claude-code",
    "python":  "https://www.python.org/downloads/",
}


# ---------------------------------------------------------------------------
# Dependency registry
# ---------------------------------------------------------------------------
def _build_checker() -> DependencyChecker:
    """
    Register all dependencies the runtime needs.

    Required:
      - Python packages: psutil, packaging
      - Python package: pynvml (NVIDIA GPU monitoring)
      - System commands: python, ollama, git

    Optional:
      - System command: claude (Claude Code integration)
    """
    checker = DependencyChecker()

    checker.register_many([
        # Python packages
        PythonPackageDependency(
            "psutil",
            min_version="5.9.0",
            required=True,
            description="CPU, RAM, and process monitoring",
        ),
        PythonPackageDependency(
            "packaging",
            min_version="23.0",
            required=True,
            description="Version comparison for dependency checks",
        ),
        PythonPackageDependency(
            "pynvml",
            min_version="12.0.0",
            required=True,
            description="NVIDIA GPU monitoring (required only for NVIDIA GPUs)",
        ),
        PythonPackageDependency(
            "python-dotenv",
            min_version="1.0.0",
            required=True,
            description=".env file support for config loading",
        ),

        # System commands
        SystemCommandDependency(
            "ollama",
            required=True,
            description="Ollama model runtime",
        ),
        SystemCommandDependency(
            "git",
            required=True,
            description="Git version control",
        ),
        SystemCommandDependency(
            "claude",
            required=False,
            description="Claude Code integration (optional)",
        ),
    ])

    return checker


# ---------------------------------------------------------------------------
# Core install flow
# ---------------------------------------------------------------------------

def check_and_repair(auto_repair: bool = True) -> Tuple[bool, dict]:
    """
    Check all dependencies and attempt to repair failures.

    Args:
        auto_repair: If True, attempt automatic installation/repair.

    Returns:
        Tuple of (all_required_satisfied, results_dict)
    """
    checker = _build_checker()

    print("\n📦 Checking dependencies...")
    print("-" * 50)
    results = checker.check_all()

    _print_check_results(checker, results)

    # Attempt repairs on failures
    if auto_repair:
        failed = {
            name: result
            for name, result in results.items()
            if not result.is_healthy
        }

        if failed:
            print("\n🔧 Attempting auto-repair...")
            print("-" * 50)
            repair_results = checker.repair_failures(auto_repair=True)

            for name, (success, message) in repair_results.items():
                icon = "✓" if success else "✗"
                print(f"  {icon} {name}: {message}")

            # Re-check after repair
            print("\n🔄 Re-checking after repair...")
            print("-" * 50)
            results = checker.check_all()
            _print_check_results(checker, results)

    summary = checker.get_summary()
    all_required_ok = _all_required_satisfied(checker, results)

    return all_required_ok, results

def _print_check_results(checker: DependencyChecker, results: dict) -> None:
    """Print a formatted dependency check table."""
    for name, result in results.items():
        dep = checker.dependencies[name]

        if result.is_healthy:
            version_str = f"  ({result.version})" if result.version else ""
            print(f"  ✓ {name}{version_str}")
        elif not dep.required:
            print(f"  ⚠ {name}: NOT FOUND (optional)")
            print(f"      → {dep.get_install_instructions()}")
            if name in INSTALL_URLS:
                print(f"      → {INSTALL_URLS[name]}")
        else:
            print(f"  ✗ {name}: {result.message}")
            print(f"      → {dep.get_install_instructions()}")
            if name in INSTALL_URLS:
                print(f"      → {INSTALL_URLS[name]}")

def _all_required_satisfied(checker: DependencyChecker, results: dict) -> bool:
    """Return True only if every required dependency is healthy."""
    for name, result in results.items():
        dep = checker.dependencies[name]
        if dep.required and not result.is_healthy:
            return False
    return True


# ---------------------------------------------------------------------------
# Full install entry point
# ---------------------------------------------------------------------------
def run_install(auto_repair: bool = True) -> bool:
    """
    Run the full installation process.

    Checks all dependencies, attempts repairs, then prints a final summary
    telling the user exactly what (if anything) still needs manual action.

    Args:
        auto_repair: Whether to automatically install/repair where possible.

    Returns:
        bool: True if all required dependencies are satisfied after install.
    """
    _print_banner()

    all_ok, results = check_and_repair(auto_repair=auto_repair)

    _print_summary(all_ok)

    return all_ok

def _print_banner() -> None:
    print("\n" + "=" * 50)
    print("🚀 Local AI Runtime — Installer")
    print("=" * 50)
    print(f"Python:   {sys.version.split()[0]}")
    print(f"Platform: {platform.system()} {platform.release()}")

def _print_summary(all_ok: bool) -> None:
    print("\n" + "=" * 50)
    print("📊 Installation Summary")
    print("=" * 50)

    if all_ok:
        print("✓ All required dependencies are satisfied.")
        print("✓ Local AI Runtime is ready to use.\n")
        print("  Run:  python runtime/main.py help")
    else:
        print("✗ Some required dependencies could not be installed automatically.")
        print("  Please install the items marked ✗ above, then re-run:\n")
        print("      python install.py\n")