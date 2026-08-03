# Handles all AI Runtime commands. Should be the main entry point for the CLI.
import sys

from ollama import start_ollama, start_model
from session import stop_session, show_status
from models import build_model
from doctor import full_diagnostic


def main():

    command = sys.argv[1]


    if command == "start":

        model = sys.argv[2]

        start_model(model)


    elif command == "stop":

        stop_session()


    elif command == "status":

        show_status()


    elif command == "build":

        model = sys.argv[2]

        build_model(model)


    elif command == "doctor":

        full_diagnostic()


    elif command == "mcp":

        # Add MCP-related functionality here
        pass


    else:

        print("Unknown command")


if __name__ == "__main__":
    main()