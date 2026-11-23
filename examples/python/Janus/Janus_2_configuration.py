"""
@example Janus_2_configuration.py

Read bundled model configuration through Janus.
"""

from Janus.config import get_model_config, load_models_config


def main() -> None:
    models = load_models_config()
    print(sorted(models))
    print(get_model_config("Mercury"))


if __name__ == "__main__":
    main()