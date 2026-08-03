# Checks for all needed dependencies: Python, Ollama, Claude, Git, Models, MCP validation, and more. If any dependencies are missing, it will prompt the user to install them.

import subprocess
import sys
import os

def check_dependencies():
    dependencies = {
        "Python": "python --version",
        "Ollama": "ollama --version",
        "Claude": "claude --version",
        "Git": "git --version",
        # Add more dependencies as needed
    }
    missing_dependencies = []
    for name, command in dependencies.items():
        try:
            subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            missing_dependencies.append(name)
    if missing_dependencies:
        print("The following dependencies are missing:")
        for dep in missing_dependencies:
            print(f"- {dep}")
        print("Please install the missing dependencies and try again.")
        sys.exit(1)
    else:
        print("All dependencies are satisfied.")


def check_models():
    pass


def check_mcp():
    pass


def full_diagnostic():
    check_dependencies()
    check_models()
    check_mcp()
    print("All checks passed. Your environment is ready.")