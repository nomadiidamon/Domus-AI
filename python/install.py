"""
install.py - Install Domus-AI for development and check runtime prerequisites.

From the repository root, install the package in editable mode with development
dependencies using:
    python python/install.py

Run this script to check and optionally repair external runtime prerequisites:
    python python/install.py

Optional flags:
    --check-only    Check prerequisites without installing or repairing packages.
    --no-repair     Same as --check-only.
"""

import sys
import importlib.util
import subprocess
from pathlib import Path

# Ensure src/ (parent of Janus/) is on the path so relative imports work
_src_dir = Path(__file__).resolve().parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

def run_install(auto_repair: bool = True) -> bool:
    """Load Hestia's checker only after the package install has run."""
    installer_path = _src_dir / "Janus" / "installer.py"
    spec = importlib.util.spec_from_file_location("installer", installer_path)
    installer_module = importlib.util.module_from_spec(spec)
    sys.modules["installer"] = installer_module
    try:
        spec.loader.exec_module(installer_module)
    except ImportError as error:
        print(f"Cannot load the Hestia installer: {error}", file=sys.stderr)
        print('Install its prerequisite with: python -m pip install "hestia-system>=0.5.0"', file=sys.stderr)
        return False
    return installer_module.run_install(auto_repair=auto_repair)


def main() -> int:
    args = sys.argv[1:]
    auto_repair = "--check-only" not in args and "--no-repair" not in args

    if auto_repair:
        package_root = Path(__file__).resolve().parent
        print(f"Installing Domus-AI from {package_root}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", f"{package_root}[dev]"]
        )
        if result.returncode != 0:
            print("[X] Could not install Domus-AI from this checkout.", file=sys.stderr)
            return result.returncode

    success = run_install(auto_repair=auto_repair)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())