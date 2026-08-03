# Handles the Claude Code intergration.
import subprocess


def ollama_launch_claude(model):
    subprocess.Popen(
        [
            "ollama",
            "launch",
            "claude",
            "--model",
            model
        ]
    ) 