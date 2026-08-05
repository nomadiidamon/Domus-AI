# Local-AI-Runtime


## Description
This is meant to serve as tool for harnessing local AI models for development and testing purposes.
It provides a simple interface to run and interact with various AI models locally without relying on external APIs.

It is designed to be modular, allowing users to easily add support for new models and runtimes as they become available.

This project may be used as a package for other projects, or as a standalone tool for local AI model development and testing.


## Dependencies

### Required Dependencies
- Python           The primary programming language for running the runtime. Developed with python version 3.14.6
- Ollama           The primary runtime for running local AI models. Ensure you have the latest version installed.

### Required Python Packages
- psutil           v5.9.0 (or greater) for CPU, RAM, and GPU usage monitoring
- packaging        v23.0 (or greater) for version comparison in dependency checks
- nvidia-ml-py     v12.0.0 (or greater) for GPU monitoring (if using NVIDIA GPUs)

### Optional Dependencies
- Claude Code      For Claude models, or direct integration with Claude Code's CLI if desired.
