"""
DomusAPI - Stable, top-level API for the Domus-AI package.

A simple wrapper around the finer-grained subsystem APIs (Hestia, Janus,
Mentis, Faber, Custos, Mercurius, Lares), meant for consumers who want a
stable surface without needing the fine-grained control those subsystems
expose directly to developers building more intensive integrations.

STUB: not yet implemented. No wrapper functions exist yet - this package
exists so the module tree matches the target structure ahead of the
actual implementation. For now, import directly from the owning
subsystem package (e.g. `from Hestia import detect_hardware`).
"""

__all__: list = []