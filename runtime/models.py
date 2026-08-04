# Handles all model pulling and building commands
import subprocess
from session import get_session, create_session, stop_session

def start_model(model):

    existing = get_session(model)

    if existing:
        return existing


    process = subprocess.Popen(
        [
            "ollama",
            "run",
            model
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


    create_session(
        name=model,
        process=process,
        session_type="model",
        metadata={
            "model": model
        }
    )

    return process

def stop_model(model):

    return stop_session(model)

def pull_model(model):
    pass

def build_model(model):
    pass

def list_models():
    pass

def remove_model(model):
    pass