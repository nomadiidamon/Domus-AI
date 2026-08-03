# Handles all the ollama commands. Delegates to models.py for model building and pulling, and to session.py for session management.

import subprocess
import models
import session
from claude import ollama_launch_claude


def start_ollama():

    subprocess.Popen(
        [
            "ollama",
            "serve"
        ]
    )

def start_model(model):

    subprocess.Popen(
        [
            "ollama",
            "run",
            model
        ]
    )

def launch_claude(model):
    ollama_launch_claude(model)