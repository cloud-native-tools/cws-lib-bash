<!--
  Shared "Skill Enablement" snippet — SINGLE SOURCE OF TRUTH.

  This file is NOT a standalone agent template. It is the canonical wording of the
  skill-preference protocol that every built-in role agent (`agents/*.agent.md`) and
  its generator (`agent-capacity-*-template.md`) composes into a `## Skill Enablement`
  section. Edit the protocol text HERE only; keep every agent/template copy identical
  so agent→skill guidance stays uniform and discoverable (FR-009, SC-005).

  The ONLY per-agent-varying part is the `| Skill | When to use |` table, whose skill
  set MUST equal that agent's `skills:` frontmatter list. Do not reword the shared
  protocol paragraph per agent (contract C-2).

  Capability → responsibility note (authoring guidance; do NOT copy into the body):
  an agent's declared `skills:` + `tools:` are its CAPACITY — what it can do. Capacity
  gates responsibility: an agent can only be assigned a team responsibility its capacity
  supports. In particular, the capacity to edit agent/skill/team definitions is what
  makes an agent a Meta agent, and only a Meta agent may take the team-management
  responsibilities (optimizer, process-evaluator, team-config editor). An agent with a
  read-only skill/tool set is confined to Worker responsibilities. See the capacity↔
  responsibility boundary in `.specify/skills/create-team/references/capacity-vs-responsibility.md`
  and the Type criterion in `.specify/skills/create-team/references/conceptual-model.md`.
-->

## Skill Enablement

Framework skills and agent definitions install together, so every skill I declare is guaranteed to be invocable. I therefore prefer an applicable framework skill over performing the same operation manually or ad-hoc, and I delegate the operation to the skill rather than reimplementing its logic inline. When more than one skill could apply, I choose the most role-specific one. When no relevant skill applies — or a relevant skill is unavailable or fails at runtime — I complete the operation directly and surface the failure rather than stalling or fabricating a skill reference. The skills below are my role-relevant, curated set; any other installed skill remains available as a fallback.

| Skill | When to use |
|-------|-------------|
| <!-- per-role rows; one per `skills:` slug --> | |
