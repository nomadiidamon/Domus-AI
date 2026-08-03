# Determines pathing in the project. Util for finding the root of the project and other pathing needs.
from pathlib import Path

def find_root():

    current = Path(__file__).resolve()

    while current:

        if (current / ".ai-runtime").exists():

            return current


        current=current.parent


    raise Exception(
        "AI runtime not found"
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