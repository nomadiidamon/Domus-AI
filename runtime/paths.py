# Determines pathing in the project. Util for finding the root of the project and other pathing needs.
from pathlib import Path

def find_root():
    """
    Find the root directory of the AI runtime project.
    
    Searches for a .ai-runtime marker file starting from the current script
    and working upward through parent directories.
    
    Returns:
        Path: Root directory of the AI runtime project
        
    Raises:
        RuntimeError: If .ai-runtime marker file is not found
    """

    current = Path(__file__).resolve()

    # Traverse up the directory tree until we find the marker or hit root
    while current != current.parent: # Stop at filesystem root
        if (current / ".ai-runtime").exists():
            return current
        current=current.parent

    raise RuntimeError(
        "AI runtime not found. Make sure you're running from within the Local-AI-Runtime project "
        "and that a .ai-runtime marker file exists in the project root."
    )

def get_modelfiles_path():
    root = find_root()
    return root / "Modelfiles"


def get_mcp_path():
    root = find_root()
    return root / "mcp"

def get_python_requirements_path():
    root = find_root()
    return root / "requirements.txt"