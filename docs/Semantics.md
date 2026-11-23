@page semantics Semantics

# Domus-AI Semantics

This page defines the behavior contract that both language implementations should follow. Python is the active implementation. C++ should align with this contract as it is implemented.

## Goals

- Keep user-facing behavior equivalent across language implementations.
- Allow language-specific internals without changing external behavior.
- Preserve compatibility for docs, examples, and automation that depend on stable behavior.

## Contract Surface

The shared semantic contract covers:

- Runtime lifecycle: initialize, start services, perform work, shutdown.
- Model actions: start, stop, build, pull, list, remove, and status reporting.
- Messaging: one-shot prompt/response and multi-turn chat behavior.
- Eventing: stable event categories and payload shape for publish/subscribe workflows.
- Memory: short-term context, durable notes, and user facts behavior.
- MCP/tooling boundaries: permission checks before tool dispatch and deterministic error paths.

## Cross-Language Rules

- Equivalent operations should produce equivalent outcomes for success and failure.
- Public API and CLI names may follow language conventions, but meaning must remain aligned.
- Error cases must be explicit and predictable.
- Long-running actions must expose progress or status in a consistent way.
- Configuration keys should be shared unless a language-specific key is required.
- Defaults should be behaviorally equivalent.

## Error and State Semantics

- Invalid input should fail fast with actionable messages.
- Missing dependencies should report what is missing and how to resolve it.
- Runtime state transitions should be linear and observable: initialized, running, stopping, stopped.
- Partial failure should not silently corrupt runtime state.

## Compatibility Policy

- Backward-incompatible behavior changes must be documented here before implementation.
- Behavior changes should include test updates and examples updates.
- Deprecated behavior should include a transition period when practical.

## Implementation Notes

Python is the current reference implementation for semantic behavior. As C++ is implemented, parity gaps should be tracked and resolved against this page.
