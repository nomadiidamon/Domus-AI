"""
install.py - Entry point for Local AI Runtime installation.

Run this once before using the runtime:
    python install.py

Optional flags:
    --check-only    Check dependencies without attempting auto-repair.
    --no-repair     Same as --check-only.
"""

import sys
import importlib.util
from pathlib import Path

# Ensure src/ (parent of Janus/) is on the path so relative imports work
_src_dir = Path(__file__).resolve().parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Load installer.py directly without loading Janus/__init__.py.
# This avoids importing config.py (which requires dotenv) before we can
# check if dotenv is installed.
_installer_path = _src_dir / "Janus" / "installer.py"
_spec = importlib.util.spec_from_file_location("installer", _installer_path)
_installer_module = importlib.util.module_from_spec(_spec)
sys.modules["installer"] = _installer_module
_spec.loader.exec_module(_installer_module)

run_install = _installer_module.run_install


def main() -> int:
    args = sys.argv[1:]
    auto_repair = "--check-only" not in args and "--no-repair" not in args

    success = run_install(auto_repair=auto_repair)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())