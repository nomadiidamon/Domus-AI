"""
@example DomusAPI_2_messaging.py

Start a model and send one prompt through the stable package API.
"""

import DomusAPI


def main() -> None:
    # Requires Ollama and the mercury model; start_model starts Ollama if needed.
    initialized = False
    model_started = False
    try:
        DomusAPI.init(suggested_host=".")
        initialized = True
        DomusAPI.start_model("mercury")
        model_started = True
        print(DomusAPI.ask("mercury", "Summarize what DomusAPI is for."))
    finally:
        if model_started:
            DomusAPI.stop_model("mercury")
        if initialized:
            DomusAPI.shutdown()


if __name__ == "__main__":
    main()