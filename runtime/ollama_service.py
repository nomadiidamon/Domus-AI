# Handles all the ollama commands. Delegates to models.py for model building and pulling, and to session.py for session management.
import subprocess
import logging
from typing import Optional
import time
from runtime.session import create_session, stop_session, get_session, remove_session

def start_ollama():
    existing = get_session("ollama_server")

    if existing:
        return existing

    process = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    create_session(
        name="ollama_server",
        process=process,
        session_type="service"
    )

    return process


def stop_ollama():

    return stop_session("ollama_server")