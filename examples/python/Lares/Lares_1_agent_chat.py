"""
@example Lares_1_agent_chat.py

Use a Lares Agent for one model-bound conversation turn.
"""

from Faber import Message
from Lares import Agent


def main() -> None:
    # Requires a reachable Ollama server and an installed mercury model.
    agent = Agent("Mercury")
    history = [Message("user", "What is the role of Lares?")]
    response = agent.chat(history)
    print(response.content)


if __name__ == "__main__":
    main()