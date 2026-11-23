"""
Lares.roles - agent roles and traits.

STUB: not yet implemented.

The intended scope (not built yet): a Role would describe a *behavioral*
identity layered on top of an AgentProfile's capability flags (Lares.
profiles) - things like a persona/system-prompt fragment, a set of
traits (e.g. terse vs. explanatory, cautious vs. proactive about
destructive tool calls), and which roles a given model is allowed to be
assigned. This is deliberately separate from AgentProfile: a profile
says what a model *can* do (tool support, known quirks); a role would
say how it *should* behave while doing it. The Modelfiles/ SYSTEM blocks
currently do this job by hand (see e.g. Modelfiles/Analyst) - Role
would eventually give that a structured, composable, runtime-editable
form instead of a fixed string baked into the Modelfile.

Not building this now because: the current four agents each have one
fixed persona apiece, baked into their Modelfile - there's no present
need to vary persona/traits independently of the model, or to reuse one
role across multiple models, so a Role abstraction would be speculative
rather than solving an observed problem. Revisit once there's an actual
case for one model to carry more than one role, or one role to apply
across more than one model.
"""

__all__: list = []