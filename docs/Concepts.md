@page concepts Concepts

# Domus-AI Concepts

This page defines the key ideas both language implementations should follow. Concepts describe design intent; semantics define exact behavior.

## Core Ideas

- Local-first AI runtime: run and manage local model workflows without cloud-only dependencies.
- Modular subsystems: separate responsibilities into clear packages and APIs.
- Shared contract, native style: keep behavior equivalent while respecting each language ecosystem.
- Explicit boundaries: each subsystem owns a focused concern and exposes a narrow public surface.

## Subsystem Concepts

- Janus: user entry point for CLI lifecycle, diagnostics, and runtime orchestration.
- DomusAPI: stable, package-level integration facade for library consumers.
- Mentis: runtime context and durable memory model.
- Faber: model process actions and messaging execution.
- Lares: agent and profile layer for model-aware behavior.
- Custos: permission and MCP client boundary.
- DomusEvents: shared event vocabulary and publish/subscribe model.
- DomusMCP: local MCP server implementations and tool surfaces.
- DomusData: bundled default configuration and model assets.

## Architectural Principles

- Keep shared metadata centralized.
- Keep implementation tooling language-local.
- Prefer explicit contracts over implicit coupling.
- Separate policy (what is allowed) from execution (what is done).
- Keep documentation close to source, and keep shared guidance under docs.

## API and CLI Design Principles

- Public names should be discoverable and stable.
- Similar capabilities should be named consistently across modules.
- Errors should communicate action, cause, and next step.
- Defaults should be safe and practical for local development.

## Evolution Guidance

- Add new features behind existing subsystem boundaries when possible.
- Update Concepts when design intent changes.
- Update Semantics when user-visible behavior changes.
- Keep examples aligned with current public interfaces.
