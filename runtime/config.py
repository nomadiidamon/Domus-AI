# Reads all configuration files - models.json, ollama.env, claude.json, and runtime.json.
from dotenv import load_dotenv

load_dotenv(
    "config/ollama.env"
)

