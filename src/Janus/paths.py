# Determines pathing in the project. Util for finding the root of the project and other pathing needs.
import os
from pathlib import Path

_DOMUS_MARKER_NAME = ".domus-marker"
# ---------------------------------------------------------------------------
# Runtime source root  (read-only - the Local-AI-Runtime installation itself)
# ---------------------------------------------------------------------------
def find_root():
    """
    Find the root directory of the Domus-AI project.
    
    Searches for a .domus-marker file starting from the current script
    and working upward through parent directories.
    
    Returns:
        Path: Root directory of the Domus-AI project
        
    Raises:
        RuntimeError: If .domus-marker file is not found
    """

    env_root = os.environ.get("LOCAL_AI_RUNTIME_ROOT")
    if env_root:
        root = Path(env_root).resolve()
        if not (root / _DOMUS_MARKER_NAME).exists():
            raise RuntimeError(
                f"LOCAL_AI_RUNTIME_ROOT is set to '{root}' but no .domus-marker was found there."
            )
        return root

    current = Path(__file__).resolve()

    while current != current.parent:
        if (current / _DOMUS_MARKER_NAME).exists():
            return current
        current=current.parent

    raise RuntimeError(
        "Domus-AI project root not found. Make sure you're running from within the Domus-AI project "
        "and that a .domus-marker file exists in the project root."
    )

# ---------------------------------------------------------------------------
# Runtime source paths  (read-only, inside the Local-AI-Runtime install)
# ---------------------------------------------------------------------------
def get_modelfiles_path():
    root = find_root()
    return root / "Modelfiles"

def get_mcp_path():
    root = find_root()
    return root / "mcp"

def get_python_requirements_path():
    root = find_root()
    return root / "requirements.txt"


_HOST_MARKER_NAME = ".domus-host-marker"

# ---------------------------------------------------------------------------
# Host project root  (where writable output goes - the project using this runtime)
# ---------------------------------------------------------------------------
_host_project_root: Path | None = None

def set_host_project_root(path: str | Path) -> None:
    """
    Set the host project root and ensure the .domus-host-marker file exists there.

    Should only be called after the user has confirmed the location via
    initialize_host(). Do not call this directly from main.py.

    Args:
        path: Root directory of the host project.
    """
    global _host_project_root
    resolved = Path(path).resolve()
    _ensure_host_marker(resolved)
    _host_project_root = resolved

def get_host_project_root() -> Path:
    """
    Return the confirmed host project root.

    Resolution order:
      1. Explicit set_host_project_root() call (requires prior confirmation)
      2. LOCAL_AI_RUNTIME_HOST environment variable
      3. Raises RuntimeError - no silent fallback to cwd

    Raises:
        RuntimeError: If the host root has not been set yet.
    """
    if _host_project_root is not None:
        return _host_project_root

    env = os.environ.get("LOCAL_AI_RUNTIME_HOST")
    if env:
        resolved = Path(env).resolve()
        _ensure_host_marker(resolved)
        return resolved

    raise RuntimeError(
        "Host project root has not been set. "
        "Call initialize_host() before accessing host directories."
    )

def is_host_initialized() -> bool:
    """Return True if the host project root has been confirmed and set."""
    try:
        get_host_project_root()
        return True
    except RuntimeError:
        return False

# ---------------------------------------------------------------------------
# Host project paths  (writable, created inside the host project)
# ---------------------------------------------------------------------------
def get_ai_runtime_dir() -> Path:
    """The .domus-AI/ working directory inside the host project.

    Note: this is a directory, distinct from the .domus-host-marker file
    (a plain empty file) used both to mark the runtime's own repo root
    (find_root()) and the host project root (_ensure_host_marker()).
    """
    return get_host_project_root() / ".domus-AI"

def get_cache_dir() -> Path:
    return get_ai_runtime_dir() / "cache"

def get_logs_dir() -> Path:
    return get_ai_runtime_dir() / "logs"

def get_models_dir() -> Path:
    return get_ai_runtime_dir() / "models"

def get_memory_dir() -> Path:
    return get_ai_runtime_dir() / "memory"

def get_config_dir() -> Path:
    return get_ai_runtime_dir() / "config"

def get_sessions_dir() -> Path:
    return get_ai_runtime_dir() / "sessions"


# ---------------------------------------------------------------------------
# Host initialization - prompting and validation
# ---------------------------------------------------------------------------
def _ensure_host_marker(path: Path) -> None:
    """
    Ensure the .domus-host-marker file exists at the given path.
    Creates it if missing. Raises if the path is not a valid directory.

    Args:
        path: Directory to check or initialize.

    Raises:
        RuntimeError: If the path does not exist or is not a directory.
    """
    if not path.exists():
        raise RuntimeError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise RuntimeError(f"Path is not a directory: {path}")

    marker = path / _HOST_MARKER_NAME

    if not marker.exists():
        marker.touch()

def _prompt_for_path(suggested: Path) -> Path:
    """
    Interactively prompt the user to confirm or change the host project root.

    Args:
        suggested: The path to suggest as the default.

    Returns:
        Path: The validated, confirmed path chosen by the user.

    Raises:
        RuntimeError: If the user cancels or provides an invalid path.
    """
    print("\n" + "=" * 50)
    print("[DIR]  Host Project Initialization")
    print("=" * 50)
    print(
        "The Local AI Runtime needs to know which project it is working inside.\n"
        "A .domus-host-marker file and .ai-runtime/ working directory will be created there.\n"
    )

    while True:
        print(f"Suggested location:  {suggested}")
        choice = input("Use this location? [Y]es / [N]o, enter a different path / [C]ancel: ").strip().lower()

        if choice in ("y", "yes", ""):
            return suggested

        if choice in ("c", "cancel"):
            raise RuntimeError("Host project initialization cancelled by user.")

        # User wants a different path
        raw = input("Enter the full path to your project root: ").strip()

        if not raw:
            print("[!] No path entered, please try again.\n")
            continue

        candidate = Path(raw).resolve()

        if not candidate.exists():
            print(f"[X] Path does not exist: {candidate}\n")
            continue

        if not candidate.is_dir():
            print(f"[X] Path is not a directory: {candidate}\n")
            continue

        # Confirm the new path before accepting
        confirm = input(f"Set '{candidate}' as the host project root? [Y/N]: ").strip().lower()

        if confirm in ("y", "yes"):
            return candidate

        print("[RETRY] Let's try again.\n")

def initialize_host(suggested: Path | None = None, non_interactive: bool = False) -> Path:
    """
    Confirm and initialize the host project root.

    If the host is already set (env var or prior call), this is a no-op.
    Otherwise prompts the user to confirm or change the location, then
    creates the marker file and sets the host root.

    Args:
        suggested:       Path to suggest. Defaults to cwd.
        non_interactive: Accept the suggested path without prompting.

    Returns:
        Path: The confirmed host project root.

    Raises:
        RuntimeError: If the user cancels, or the path is invalid.
    """
    if is_host_initialized():
        return get_host_project_root()

    suggested = Path(suggested).resolve() if suggested else Path.cwd()

    if non_interactive:
        if not suggested.exists() or not suggested.is_dir():
            raise RuntimeError(f"Non-interactive init failed: invalid path '{suggested}'")
        set_host_project_root(suggested)
        return suggested

    confirmed = _prompt_for_path(suggested)
    set_host_project_root(confirmed)

    print(f"\n[OK] Host project root set to: {confirmed}")
    print(f"[OK] Host marker created at:   {confirmed / _HOST_MARKER_NAME}")
    print()

    return confirmed

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _host_dirs() -> list[Path]:
    """All writable directories that should exist in the host project."""
    return [
        get_ai_runtime_dir(),
        get_cache_dir(),
        get_logs_dir(),
        get_models_dir(),
        get_memory_dir(),
        get_config_dir(),
        get_sessions_dir(),
    ]

def ensure_host_dirs() -> None:
    """Create all writable runtime directories inside the host project."""
    for directory in _host_dirs():
        directory.mkdir(parents=True, exist_ok=True)

def get_directory_report() -> dict:
    """Return an existence and write-access report for host project directories."""
    return {
        str(d): {
            "exists": d.exists(),
            "writable": os.access(d, os.W_OK) if d.exists() else False,
        }
        for d in _host_dirs()
    }