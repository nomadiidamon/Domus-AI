"""
install.py - Entry point for Local AI Runtime installation.

Run this once before using the runtime:
    python install.py

Optional flags:
    --check-only    Check dependencies without attempting auto-repair.
    --no-repair     Same as --check-only.
"""

import sys
from pathlib import Path

# Ensure src/ (parent of Janus/) is on the path so `Janus` can be imported
# as a package, letting installer.py's relative imports (e.g.
# `from .dependencies import ...`) resolve.
_src_dir = Path(__file__).resolve().parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from Janus.installer import run_install


def main() -> int:
    args = sys.argv[1:]
    auto_repair = "--check-only" not in args and "--no-repair" not in args

    success = run_install(auto_repair=auto_repair)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())