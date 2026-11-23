"""
@example Mentis_1_memory.py

Persist a conversation preference and a durable note with Mentis.
"""

from Mentis import RuntimeContext


def main() -> None:
    # startup creates managed state under the selected host directory.
    context = RuntimeContext(project_name="Example")
    if not context.startup(suggested_host=".", non_interactive=True):
        raise RuntimeError("Could not initialize the example host")

    try:
        context.update_ai_memory("user", "Prefer concise responses")
        context.store_conversation_note("This project uses pytest")
        context.remember_user_fact("preferred_test_runner", "pytest")
        print(context.ai_memory.recall("preferred_test_runner"))
    finally:
        context.shutdown()


if __name__ == "__main__":
    main()