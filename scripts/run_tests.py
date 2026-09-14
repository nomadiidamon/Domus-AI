#!/usr/bin/env python3
"""
run_tests.py - Cross-platform test runner for Domus-AI.

Runs the full pytest suite (via `python -m pytest` so it works the same
on Linux, macOS, and Windows) and streams the output to the console while
also saving a full copy to a log file for easy sharing/review.

Usage:
    python scripts/run_tests.py [pytest args...]

Examples:
    python scripts/run_tests.py                 # run the whole suite
    python scripts/run_tests.py -k hardware     # run tests matching "hardware"
    python scripts/run_tests.py -m janus -v     # run only the "janus" marker, verbosely
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "test-output.log"


def main() -> int:
    command = [sys.executable, "-m", "pytest", *sys.argv[1:]]

    header = (
        f"Running: {' '.join(command)}\n"
        f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'=' * 70}\n"
    )
    print(header, end="")

    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write(header)
        log.flush()

        # Merge stderr into stdout so the log/console capture the full picture in order.
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            print(line, end="")
            log.write(line)

        process.wait()

    print(f"\nFull output saved to: {LOG_FILE}")
    return process.returncode


if __name__ == "__main__":
    sys.exit(main())
