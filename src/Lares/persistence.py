"""
Lares.persistence - durable agent state.

STUB: not yet implemented.

The intended scope (not built yet): where an Agent's own state would be
saved/restored across process restarts - which AgentProfile overrides
were made at runtime (as opposed to the built-in registrations in
Lares.profiles), per-agent notes or preferences distinct from the
general conversation memory, and eventually persisted Role assignments
(see Lares.roles) once roles exist. This is intentionally not
conversation history or project memory - Mentis.AIMemory /
RuntimeContext already own that, persist it to disk, and are already
wired into Janus.main.handle_chat; this module would only ever cover
state that is specifically about the agent itself, not the
conversation.

Not building this now because: Lares.profiles' registry is in-memory
and code-defined (register_profile calls at import time), which matches
how the project's other config is handled today (Modelfiles/ and
mcp/profiles/*.json are files edited by hand, not runtime-mutated) -
there's no current workflow that mutates an AgentProfile at runtime and
needs that mutation to survive a restart. Revisit once such a workflow
exists (e.g. a `janus agent tune <model> ...` command), at which point
this should likely follow Janus.paths' existing get_config_dir()
convention for where the file(s) live, rather than inventing a new
location.
"""

__all__: list = []