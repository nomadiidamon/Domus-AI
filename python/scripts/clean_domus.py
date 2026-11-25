#!/usr/bin/env python3
"""
clean_domus.py - Uninstall Domus-AI/Janus and remove build and Python artifacts.

Steps:
    1. Uninstall the domus-ai package if it is installed.
    2. List every artifact found (including those in sub packages).
    3. Prompt before deleting them.

Usage:
    python scripts/clean_domus.py
"""

import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "domus-ai"

# Directories that are never scanned (virtualenvs, VCS metadata).
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules"}

ARTIFACT_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    "build",
    "dist",
    "htmlcov",
}
ARTIFACT_DIR_SUFFIXES = (".egg-info", ".egg")
ARTIFACT_FILE_SUFFIXES = (".pyc", ".pyo", ".pyd")
ARTIFACT_FILE_NAMES = {"test-output.log", ".coverage"}


def python_interpreters() -> list[Path]:
    """Return the active Python and this checkout's virtualenv Python."""
    local_venv = REPO_ROOT.parent / ".venv"
    local_python = local_venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    candidates = [Path(sys.executable), local_python]
    interpreters: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen and resolved.is_file():
            seen.add(resolved)
            interpreters.append(resolved)
    return interpreters


def uninstall() -> None:
    found = False
    for interpreter in python_interpreters():
        check = subprocess.run(
            [str(interpreter), "-m", "pip", "show", PACKAGE_NAME],
            capture_output=True, text=True,
        )
        if check.returncode != 0:
            continue
        found = True
        print(f"Uninstalling {PACKAGE_NAME} from {interpreter}...")
        result = subprocess.run(
            [str(interpreter), "-m", "pip", "uninstall", "-y", PACKAGE_NAME]
        )
        if result.returncode != 0:
            print(f"Warning: pip uninstall exited with code {result.returncode} for {interpreter}.")
    if not found:
        print(f"{PACKAGE_NAME} is not installed in the active Python or this checkout's .venv.")


def find_artifacts() -> list[Path]:
    found: list[Path] = []

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir()):
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in SKIP_DIRS:
                    continue
                if entry.name in ARTIFACT_DIR_NAMES or entry.name.endswith(
                    ARTIFACT_DIR_SUFFIXES
                ):
                    found.append(entry)
                    continue
                walk(entry)
            elif entry.name in ARTIFACT_FILE_NAMES or entry.name.endswith(
                ARTIFACT_FILE_SUFFIXES
            ):
                found.append(entry)

    walk(REPO_ROOT)
    return found


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    uninstall()

    artifacts = find_artifacts()
    if not artifacts:
        print("No artifacts found.")
        return 0

    print(f"\nFound {len(artifacts)} artifact(s):")
    for path in artifacts:
        suffix = "/" if path.is_dir() else ""
        print(f"  {path.relative_to(REPO_ROOT)}{suffix}")

    answer = input("\nRemove these artifacts? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("Nothing removed.")
        return 0

    failures = 0
    for path in artifacts:
        try:
            remove(path)
        except OSError as exc:
            failures += 1
            print(f"Failed to remove {path.relative_to(REPO_ROOT)}: {exc}")

    print(f"Removed {len(artifacts) - failures} artifact(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
