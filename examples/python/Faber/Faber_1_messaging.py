"""
@example Faber_1_messaging.py

Send a multi-turn conversation directly through Faber messaging.
"""

from Faber.messaging import Message, chat


def main() -> None:
    # Requires a reachable Ollama server and an installed mercury model.
    response = chat(
        "mercury",
        [
            Message("system", "Answer in one sentence."),
            Message("user", "What does Faber handle in Domus-AI?"),
        ],
    )
    print(response.content)


if __name__ == "__main__":
    main()