# Conceptual Model: Role × Stage × Type + Team/Loop

**Owner**: the team domain (`create-team` / `/speckit.team`). This file is the **single source of truth** for the multi-agent conceptual model (FR-011, FR-012, SC-006). Single-agent skills (`create-agent`, `improve-agent`) MUST link here rather than re-defining any part of this model.

## The three orthogonal dimensions

Every agent participating in a team is described by three orthogonal dimensions:

- **Role** — the responsibility/perspective (e.g. `system-designer`, `test-engineer`, `team-supervisor`); a Role is a **seat** filled by an agent whose **Capacity** is defined in a `agent-capacity-<X>-template.md` (create-agent) or, for the sole Meta role, `agent-team-supervisor-template.md` (create-team). Role is the responsibility; Capacity is what the filling agent can do (see `capacity-vs-responsibility.md`).
- **Stage** — one of `executor`, `evaluator`, `optimizer` (canonical names; the deprecated dimension name "SubRole" and stage name "improver" are removed).
- **Type** — `Worker` or `Meta`, **judged independently by what the agent operates on** (see the criterion below). Stage does NOT determine Type; it only supplies a default tendency.

## Type criterion: judged by operating object, not by stage

Stage and Type are **orthogonal**: Stage answers "which station of the collaboration flow is it at?" (horizontal division of labour); Type answers "what abstraction level does it operate on?" (vertical layering). Binding them was a modeling error — the former **Type-follows-Stage** rule (spec 023 contract C3: `evaluator → Meta`, `optimizer → Meta`) is **superseded** by this criterion; it systematically mislabeled business-level evaluators as Meta.

The criterion:

- **Meta** — the agent's operating objects are **other agents, skills, or the project configuration that defines agents/skills**. It does not touch concrete business information.
- **Worker** — the agent's operating objects are **business artifacts and business information themselves**.

Stage supplies only a **default**, overridden whenever the criterion says otherwise:

| Stage | Default | How to judge |
|-------|---------|--------------|
| `executor` | Worker | Executors act on business artifacts in nearly every team |
| `evaluator` | judge by object | Evaluating **business artifacts** (a repo's state, a rendered diagram, a document) → **Worker**. Evaluating **agent performance / team structure / conclusion evidence-form** → **Meta** |
| `optimizer` | judge by object | Optimizing **agents, skills, prompts, or agent/skill-defining configuration** → **Meta**. Optimizing a **business artifact** directly → **Worker**. The **Team Supervisor is always Meta** — its operating objects are inherently the agent system (this half of the old coupling was correct and is retained) |

Worked examples (from a real misclassification): a `consistency-checker` judging repos' branch policy, working-tree dirt, and artifact freshness operates on **business information** → evaluator-stage **Worker**. A `team-supervisor` spot-checking subAgent conclusions' evidence form and dispatching/rejecting subAgents operates on **agents and the meta-properties of their outputs** → **Meta**.

### Meta and write authority: a one-way implication

`Meta` is not a label — it is the **authority gate** for a specific class of writes. Only a `Meta` agent may modify:

- the **team's own configuration** (`team.md`: roster, pattern config, thresholds, budget),
- **agent definitions** (`.specify/agents/<slug>.agent.md`, role/stage templates),
- **skill definitions** (`SKILL.md`, its references and templates).

This is the real reason the retired coupling *felt* compulsory: in a complex team, the agent that performs continuous improvement usually does rewrite prompts, agent definitions, or skill guides — and such an agent must indeed be `Meta`. That observation is correct; generalizing it into "evaluator/optimizer ⇒ Meta" was not.

**The implication runs one way only:**

> **modifies team config / agent definitions / skill definitions ⇒ MUST be `Meta`** (necessary).
> **holds an evaluator / optimizer / "continuous improvement" role ⇏ is `Meta`** (not sufficient).

There is **no if-and-only-if** between a role (or stage) and `Meta`. Two inferences to avoid:

- ❌ *"This team has a continuous-improvement agent, so that agent is Meta."* — Only if what it improves **is the agent system**. An agent that continuously improves a *business artifact* (tightening a spec, refactoring product code, polishing a document) is a `Worker`, however iterative or long-lived its loop.
- ❌ *"This agent is Meta, so it may not touch business artifacts."* — Type describes the agent's **operating object**, and the gate above constrains a class of writes; being `Worker` is what forbids editing agent/skill definitions, not the reverse. State each member's write scope explicitly rather than inferring it from Type alone.

So the practical rule when building a roster: decide **what the member writes to**, then let that determine Type — never the role name. If a member needs to modify team config, agent definitions, or skill definitions, it must be `Meta`; if it only reads and reports on those things without writing them, judge it by its operating object like any other member.

## Static vs Dynamic structure

- **Team (static structure)** — a **Role × Stage × Type** matrix describing the roster: which agents participate, in what role, at what stage, and of what type. This is what a persisted team's `## Static Structure` section renders.
- **Loop (dynamic structure)** — the runtime collaboration pattern: how the roster executes (parallel / serial / iteration / continuous), its parallelism/DAG/iteration/operating settings, and the execution flow (dispatch → handoff → loop edges). This is what a persisted team's `## Dynamic Structure` section renders.

## The Team Supervisor (single Meta role)

- **Team Supervisor** is the single **Meta role** — Meta at all stages, and it never performs real project tasks.
- It is the merge of the former **Meta-Coordinator** (task decomposition + worker dispatch) and the **Team Supervisor** (quality gating + iteration control). There is **no separate Meta-Coordinator** role.
- An `iteration` or `continuous` team MUST include **exactly one** Team Supervisor; a `parallel`/`serial` team MAY use one as the Lead / quality gate.

## Collaboration patterns (the dynamic structure)

The team domain has **four** collaboration patterns. Each encodes a different **priority**; the goal decides which one fits. The first three are **bounded** (they run once and stop); `continuous` is **unbounded** (it operates indefinitely on a cadence).

| Pattern | Priority | Static shape | Dynamic behavior | Lifecycle |
|---------|----------|--------------|------------------|-----------|
| **parallel** | 效率优先 (throughput) | independent Workers with disjoint territories | dispatched together (one response, many delegations); conflict-free write scopes | bounded — ends when all territories complete and results aggregate |
| **serial** | 质量优先 (quality) | an ordered chain of stages/roles | each stage's output feeds the next via file-path-only handoff; DAG, no cycles; a **simple verification between each step and its predecessor** guards every handoff | bounded — slower, but ends only when the final stage passes its gate |
| **iteration** | 目标收敛 (converge) | Workers + exactly one Team Supervisor | Supervisor decomposes → Workers execute → Supervisor scores → iterate until threshold or cap | bounded — converges to the goal, then delivers and stops |
| **continuous** | 长期运营 (operate) | Workers + exactly one Team Supervisor + operating discipline | runs on a **cadence**; each cycle reads constraints + budget, acts, **independently verifies**, scores, critiques, and updates a cross-run state spine | unbounded — runs indefinitely at a maturity level (L1→L2→L3), bounded per cycle by budget / circuit-breaker / kill-switch |

- **`continuous`** is the long-lived operating form — its discipline lives in [`operating-loops.md`](operating-loops.md).
- `iteration` maps to a **one-time** optimization goal; `continuous` maps to a **continuous** one (see [`optimization-goals.md`](optimization-goals.md)).

## Lifecycle: temporary vs persistent members

- **temporary** — a worker/stage agent instantiated for a single run from a stage/worker template; discarded when the run ends. Lives only in the orchestrator's context.
- **persistent** — a reusable agent stored at `.specify/agents/<slug>.agent.md` and symlinked into each supported tool.

## Template home

The multi-agent authoring templates (team-supervisor, the three EEI stages, and the parallel/serial/triad orchestration templates + workflow schema) live in `skills/create-team/templates/agents/` (installed mirror: `.specify/skills/create-team/templates/agents/`). The single-agent **capacity** templates (`agent-capacity-<X>-template.md`) and the custom/project-custom scaffolds remain in `skills/create-agent/templates/`. The `continuous` operating discipline is documented in [`operating-loops.md`](operating-loops.md).
