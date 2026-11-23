"""
@example Janus_1_cli.py

Run Janus diagnostics, or select another read-only CLI command.
"""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("doctor", "status", "list"),
        default="doctor",
        help="read-only Janus command to run (default: doctor)",
    )
    args = parser.parse_args()

    # Equivalent to `janus doctor`; this example does not start a model.
    result = subprocess.run([sys.executable, "-m", "Janus", args.command], check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()