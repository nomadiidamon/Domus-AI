# Domus-AI


## Description
This is meant to serve as tool for harnessing local AI models for development and testing purposes.

It provides a simple interface to run and interact with various AI models locally without relying on external APIs, although there are plans to allow integrations with tools such as Claude Code.

It is designed to be modular, allowing users to easily add support for new models and runtimes as they become available.

This project may be used as a package for other projects, or as a standalone tool for local AI model development and testing.

----------------------------------------------------

## Project Structure and Architecture
The main pieces that comprise Domus-AI are:
### Hestia - General Runtime
The hearth of Domus-AI. It is the main subsytem for operating with in Domus' local AI environment. It is responsible for Initializing subsytems, dependency injection and exposing a unified API that Domus-API wraps around. It is also the home for hardware and system detection. 

### Janus - Runtime State
The threshold users must cross for runtime capabilities. It is responsible for the runtime state, the CLI, Configuration laoding, other susbsystem lifecycles, startup and shutdown, and component registration.

### Mercurius - Event Bus
The messenger of the entire environment. It is tied directly to Janus and is instantiated when Janus starts its processes. It is responsible for sending messages, broadcasting events, subsystem coordination, and other lifecycle hooks.

### Custos - Security and MCP
The security guard of Domus-AI. It is the home for permissions, trusts, approvals and sandboxing. It also holds the Model Context Protocol(MCP) Manager that agents must work through when performing tasks actions, or gaining access to any systems.

### Mentis - Context and Memory
The memory and mind of the Domus environment. It is responsible for session management, persistent user and project memories, preferences, and contextual awareness.

### Lares - Agents
The spirits of the home (Domus). Is responsible for persistent helpers, personalized agents, specialized agents and general assistants.

### Faber - Actions
The actions, tools and workflows of the Lares. Handles no intelligence, thought or planning. Is only responsible for facilitating actions and executing work needed by the Lares. Can handle simple things like automation, scripting and external actions like Git.


-----------------------------------------------------

## Dependencies
### Required Dependencies
- Python: \t\t The primary programming language for running the runtime. Developed with python version 3.14.6
- Ollama: \t\t The primary runtime backend for running local AI models. Ensure you have the latest version installed.

### Required Python Packages
- psutil: \t\t v5.9.0 (or greater) for CPU, RAM, and GPU usage monitoring
- packaging: \t\t v23.0 (or greater) for version comparison in dependency checks
- nvidia-ml-py: \t\t v12.0.0 (or greater) for GPU monitoring (if using NVIDIA GPUs)

### Optional Dependencies
- Claude Code: \t\t For Claude models, or direct integration with Claude Code's CLI if desired.

-----------------------------------------------------