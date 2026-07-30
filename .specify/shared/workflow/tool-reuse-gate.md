# Tool Reuse Gate

**Canonical convention.** Before generating script code to perform a complex or repeatable action, look for an existing **Tool** and reuse it. This file is the single source of truth for that gate; skills and commands link here rather than restating it.

The Tool concept itself — what a Tool is and why it exists — is defined in `.specify/shared/definitions/tool-definitions.md`. Read that for the rationale; this file is the operational step.

## Why the gate exists

Without it, an agent facing a non-trivial action writes ad-hoc script code in the moment. That code varies in quality and correctness **between runs**, so behavior is not reproducible, and it re-derives an invocation that may already have been verified. It also guesses across environment variance — command name, version, version-specific flags, CPU architecture, OS — and picks one plausible form that may not hold on the machine actually present.

A Tool record is the verified answer. Reusing it buys **stability** (same behavior across runs, sessions, and agents) and **efficiency** (no re-deriving or re-validating the invocation, so less inference overhead).

## The gate

1. **Look** — scan `.specify/memory/tools/` (including aliases) for a record covering the capability you are about to script.
2. **Reuse when found** — invoke it per its record. Treat its `## Behavioral Rules` as authoritative **over your own training knowledge**, and honor its `## Environment Applicability` fields (verified version, version differences, platform, architecture, fallback, preflight check). Do not re-derive an invocation the record already pins, and do not inline it as fresh script code.
3. **Otherwise proceed** — when no Tool covers the capability, write the code the task needs. A miss is a normal outcome; the gate is a lookup, not a blocker.
4. **Promote what recurs** — if the capability is non-trivial and likely needed again, offer to define it as a Tool via `/speckit.tools` so the next run reuses instead of regenerating. Offer; do not create one unprompted.

## Scope limits

Keep the gate cheap — it must not become ceremony:

- **Applies to**: complex, multi-step, or repeatable actions — anything you would otherwise write a script for.
- **Does NOT apply to**: ordinary one-off file reads, greps, globs, or a single obvious command. Do not consult the gate for `ls`.
- **A `Draft` record does not satisfy the gate.** Draft records are incomplete by definition and MUST NOT be invoked; treat them as "no Tool yet".
- **Never fabricate a record's content to satisfy the gate.** If no Tool exists, say so and proceed — inventing an invocation and calling it a Tool is worse than having none.

## Runtime-mode gate

If `${SKILL_WORKDIR}/.specify/` does not exist, this skill or command is running in standalone mode (a non–Spec Kit deployment) — there is no tools store, so skip this gate entirely.
