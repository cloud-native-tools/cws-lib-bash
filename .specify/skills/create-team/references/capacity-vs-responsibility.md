# Capacity vs Responsibility: which template set defines an agent

**Owner**: the team domain (`create-team` / `/speckit.team`). This file is the **single source of truth** for the division of labour between the two agent-template sets. Both `create-agent` and `create-team` link here instead of restating it.

Two skills author agent-shaped Markdown, and the recurring confusion is "which one do I edit?". The answer is a single axis:

| | `skills/create-agent/templates/` | `skills/create-team/templates/agents/` |
|---|---|---|
| **Center of gravity** | the **agent** | the **team** |
| **What it defines** | **capacity** — what this agent *can do* | **responsibility** — what this agent *is accountable for inside one team* |
| **Question answered** | "who is this professional?" | "what is this seat in the formation?" |
| **Scope of validity** | team-agnostic; valid in any team or standalone | valid only inside the team/run that instantiated it |
| **Typical lifecycle** | `persistent` — stored at `.specify/agents/<slug>.agent.md` | mostly `temporary` — lives in the orchestrator's context for one run |
| **Files** | `agent-capacity-<X>-template.md`, `agent-project-custom-template.md`, `agent-supervision-delegation.md`, `agent-skill-enablement.md` | `agent-team-supervisor-template.md`, `agent-stage-{executor,evaluator,optimizer}-template.md`, the `agent-*-orchestration-template.md` set, `agent-workflow-schema.md`; `teams/` stays in `templates/` |

## What belongs to capacity (create-agent)

Capacity is the agent's durable professional profile. It is declared once and reused by every team:

- **Enablement surface**: `tools:`, `skills:`, `model:`, `maxTurns:` frontmatter — the concrete affordances the agent may use.
- **Professional identity**: first-person `## Identity & Responsibilities` describing the *discipline* (architecture, testing, QA…), not a team seat.
- **`role-scope`** and the fixed role `color` — the stable name of the profession.
- **Domain method**: the role's own `## Workflow`, quality bar, and `## Output Format`.
- **Generic edges**: `## Upstream (Inputs)` / `## Downstream (Outputs)` stated as *role-level* expectations (what a designer generally consumes/produces), never as a named peer or a run-specific path.

## What belongs to responsibility (create-team)

Responsibility is the accountability the team assigns to a seat for one goal. It presumes capacity already exists:

- **Position in the model**: `Stage` (`executor` / `evaluator` / `optimizer`) and the derived `Type` (`Worker` / `Meta`).
- **Write scope / territory**: the exact paths this seat may write, plus its forbidden-write list.
- **Handoff contract**: concrete upstream/downstream *file paths*, `blockedBy` edges, and the run-workspace location.
- **Reporting obligation**: the mandatory output schema the aggregator parses (e.g. the evaluator's `[DIM]_SCORE` / `WEIGHTED_TOTAL` / `SUGGESTIONS` block).
- **Loop obligation**: statelessness across iterations, cycle budget, escalation and verification duties.

## Authoring rules (both directions)

1. **No cross-writing.** A responsibility template MUST NOT re-declare capacity (`skills:`, tool lists, professional expertise) — it references an agent that already has it, or a stage template that carries the minimum. A capacity template MUST NOT encode team position (stage assignment, territories, `blockedBy`, run-workspace paths, peer names).
2. **Capacity is referenced, responsibility is instantiated.** A team roster row points at a capacity artifact (`.specify/agents/<slug>.agent.md`) or at a stage template, then layers the run's responsibility on top via the roster fields (`role`, `stage`, `type`, `lifecycle`, `territory`, `blockedBy`, `angle`).
3. **Same role, many responsibilities.** One capacity artifact may occupy different seats in different teams (a `qa-engineer` as executor in one team, as independent verifier in another). Never fork the capacity artifact to express a new seat — express it in the roster.
4. **Edit routing.** "The agent lacks a tool / a skill / domain judgement" → `create-agent`. "The seat has the wrong scope / stage / handoff / reporting duty" → `create-team`.
5. **The Team Supervisor is the one legitimate overlap.** It is a *role* (capacity: coordination + gating) whose only meaningful responsibility is team management, so its template lives in the team domain. It is the exception, not a precedent.

## Related

- The three orthogonal dimensions (Role × Stage × Type) and the static/dynamic split: [`conceptual-model.md`](conceptual-model.md).
- Predefined team shapes that pre-assign responsibilities for a known goal: [`teams.md`](teams.md).
