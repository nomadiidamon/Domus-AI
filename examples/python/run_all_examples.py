#!/usr/bin/env python3
"""Run all Python examples grouped by module/topic."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


GROUPS = [
    ("Custos", "Custos"),
    ("DomusAPI", "DomusAPI"),
    ("DomusEvents", "DomusEvents"),
    ("Faber", "Faber"),
    ("Janus", "Janus"),
    ("Lares", "Lares"),
    ("Mentis", "Mentis"),
]


def collect_examples(base_dir: Path, relative_dir: str) -> list[Path]:
    """Return sorted Python example files in a group directory."""
    group_dir = base_dir / relative_dir
    return sorted(path for path in group_dir.glob("*.py") if path.is_file())


def run_example(script_path: Path, repo_root: Path) -> int:
    """Run one example using the current Python interpreter."""
    env = os.environ.copy()
    source_dir = str(repo_root / "python" / "src")
    existing_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (source_dir, existing_path)))
    process = subprocess.run([sys.executable, str(script_path)], cwd=repo_root, env=env)
    return process.returncode


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    repo_root = base_dir.parents[1]

    failures: list[tuple[str, Path, int]] = []
    total_groups = len(GROUPS)

    for group_index, (header, relative_dir) in enumerate(GROUPS, start=1):
        scripts = collect_examples(base_dir, relative_dir)
        print(f"\n{'=' * 72}")
        print(f"[GROUP {group_index}/{total_groups}] {header}")
        print(f"{'=' * 72}")

        if not scripts:
            print("  No example scripts found.")
            continue

        total_scripts = len(scripts)
        for script_index, script_path in enumerate(scripts, start=1):
            print(f"\n  [{script_index}/{total_scripts}] Running {script_path.name}", flush=True)
            exit_code = run_example(script_path, repo_root)
            if exit_code == 0:
                print("  -> PASS")
            else:
                print(f"  -> FAIL (exit code {exit_code})")
                failures.append((header, script_path, exit_code))

    print(f"\n{'=' * 72}")
    print("RUN SUMMARY")
    print(f"{'=' * 72}")

    if not failures:
        print("All example scripts completed successfully.")
        return 0

    print(f"{len(failures)} script(s) failed:")
    for header, script_path, exit_code in failures:
        print(f"- {header}: {script_path.name} (exit code {exit_code})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
