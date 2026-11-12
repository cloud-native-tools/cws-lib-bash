# Conceptual Model: Role × Stage × Type + Team/Loop

**Owner**: the team domain (`create-team` / `/speckit.team`). This file is the **single source of truth** for the multi-agent conceptual model (FR-011, FR-012, SC-006) and for the **team side of the binding model** — the team's binding application, its lifecycle value pair, `handoff_ref`, and the construction-crew notion. The **binding record's meaning** (its keys, value domains, `origin` semantics) and the goal-side lifecycle are owned by `.specify/shared/definitions/goal-definitions.md` § Archive Layers / § The Binding Record; this file cites them by path and section and must not restate them. Single-agent skills (`create-agent`, `improve-agent`) MUST link here rather than re-defining any part of this model.

## The three orthogonal dimensions

Every agent participating in a team is described by three orthogonal dimensions:

- **Role** — the responsibility/perspective (e.g. `system-designer`, `test-engineer`, `team-supervisor`); a Role is a **seat** filled by an agent whose **Capacity** is defined in a `agent-capacity-<X>-template.md` (create-agent) or, for the sole Meta role, `agent-team-supervisor-template.md` (create-team). Role is the responsibility; Capacity is what the filling agent can do (see `capacity-vs-responsibility.md`).
- **Stage** — one of `executor`, `evaluator`, `optimizer` (canonical names; the deprecated dimension name "SubRole" and stage name "improver" are removed). 本 Stage 维度**不是** SDD 阶段名册:SDD 的阶段名册(阶段链与其顺序、哨兵、状态脊)仍由驱动所有,唯一真源是 `.specify/skills/sdd-loop-driver/SKILL.md`,本维度只按路径抵达它、不复述也不枚举;本维度不重命名、不重载任何取值,任何 SDD 阶段名都 MUST NOT 被当作一个 team Stage 取值使用。
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
- **agent definitions** (`.specify/agents/{templates,instances}/<slug>.agent.md`, role/stage templates),
- **skill definitions** (`SKILL.md`, its references and templates).

This is the real reason the retired coupling *felt* compulsory: in a complex team, the agent that performs continuous improvement usually does rewrite prompts, agent definitions, or skill guides — and such an agent must indeed be `Meta`. That observation is correct; generalizing it into "evaluator/optimizer ⇒ Meta" was not.

**The implication runs one way only:**

> **modifies team config / agent definitions / skill definitions ⇒ MUST be `Meta`** (necessary).
> **holds an evaluator / optimizer / "continuous improvement" role ⇏ is `Meta`** (not sufficient).

There is **no if-and-only-if** between a role (or stage) and `Meta`. Two inferences to avoid:

- ❌ *"This team has a continuous-improvement agent, so that agent is Meta."* — Only if what it improves **is the agent system**. An agent that continuously improves a *business artifact* (tightening a spec, refactoring product code, polishing a document) is a `Worker`, however iterative or long-lived its loop.
- ❌ *"This agent is Meta, so it may not touch business artifacts."* — Type describes the agent's **operating object**, and the gate above constrains a class of writes; being `Worker` is what forbids editing agent/skill definitions, not the reverse. State each member's write scope explicitly rather than inferring it from Type alone.

So the practical rule when building a roster: decide **what the member writes to**, then let that determine Type — never the role name. If a member needs to modify team config, agent definitions, or skill definitions, it must be `Meta`; if it only reads and reports on those things without writing them, judge it by its operating object like any other member.

### 消解条款:「每席皆 Worker」vs canonical 写权(本节为该消解的唯一真源)

一个 pattern 的**每个执行席位都是 Worker**(serial 链的常态,见 `.specify/templates/agents/agent-serial-orchestration-template.md`)与上面的写权门并不冲突,因为二者约束的是**不同的写目标**。消解规则:

- **Worker 只产补丁到工作区** —— 交付物落在业务路径或运行工作区(`.specify/teams/.work/<slug>/`);这是 Worker 的合法写面,不需要 Meta 身份。
- **交付物本身就是 agent / skill / team 定义时**,花名册 MUST 含**唯一 Meta supervisor**(Team Supervisor),由它把 Worker 产出的补丁落到 canonical 路径;Worker MUST NOT 直接写 canonical 定义文件。
- 因此「每席皆 Worker」的模板只在交付物为**业务制品**时成立;交付物为定义类文件时,模板里的 Lead 席位不再是可选质量门,而是**必需的 Meta 落盘者**。缺它时该 team 无法合法完成交付,应在 create 阶段补齐,而不是让某个 Worker 越权写 canonical。

## Static vs Dynamic structure

- **Team (static structure)** — a **Role × Stage × Type** matrix describing the roster: which agents participate, in what role, at what stage, and of what type. This is what a persisted team's `## Static Structure` section renders.
- **Loop (dynamic structure)** — the runtime collaboration pattern: how the roster executes (parallel / serial / iteration / continuous), its parallelism/DAG/iteration/operating settings, and the execution flow (dispatch → handoff → loop edges). This is what a persisted team's `## Dynamic Structure` section renders.

## Seat territories judged at binding time (席位写领地,绑定期判定)

A seat's **territory** — the path set it may write and read — is a property of the static structure, and it is judged when the roster is **bound**, not left for the run to avoid collisions at runtime. The judgement is a gate of the create-team roster step; `run-team` re-checks it before dispatch.

- **Undeclared is red.** Every seat MUST declare its territory. A seat with no territory declaration is `territory-undeclared` and red — it MUST NOT be read as "no territory, therefore no intersection". (Measured 2026-11-09 in this repository: 2 of the 12 team definitions declare no territory anywhere in their tree.)
- **Intersection is red before any run.** Two seats' write territories MUST NOT intersect (`territory-intersect`); a declared shared read-only resource is the only permitted overlap.
- **File-level, not directory-level.** A territory is a file-level path set (the same form as a unit's write domain); a directory-level entry declares a region rather than a path set and is red for that reason.
- **Capability bounds the roster.** The team is not instantiated with more concurrent members than its stated concurrency capability supports; the instantiation step reads the per-agent capability verdict (from the existing `capability-tools` frontmatter key) and reports the reduction when it applies.

The obligation's three-part statement, the class table and the slot/reserve values are reached by pointer — `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation and `.specify/shared/declarations/facts/` ([[STR-001]]/[[STR-008]] class and roots entries, `concurrency-slot-and-reserve.yaml`); this section restates none of their values.

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
- **persistent** — a reusable agent stored at `.specify/agents/templates/<slug>.agent.md` (role Template) or `.specify/agents/instances/<slug>.agent.md` (Instance) and symlinked into each supported tool.

## The Team Definition and the Binding Model

A team is a **persisted definition** in the one team archive layer: `.specify/teams/<slug>/team.md`, with its run reports accumulating under `.specify/teams/<slug>/runs/`. There is no second team store: a spec directory holds no current team definition, and a leftover spec-local tree is a migration source only. The binding record's meaning — its three keys, their value domains, `origin` semantics and the goal-side lifecycle — is owned by `.specify/shared/definitions/goal-definitions.md` § Archive Layers / § The Binding Record; this section owns the team's side of that model and restates none of the goal side's value domains.

- **Binding on a team.** A team definition carries the same binding record every goal carries (written only by the engine / `create-team` persistence path, never hand-edited). Ownership and writability are answered by that record, never by where the file sits. The team's own binding says which run created it, independently of whether the goal it serves has since been bound by another line.
- **`goal_slug` — identity, not content.** A team serves exactly one goal by declaring `goal_slug`; the binding is N teams : 1 goal, and the team stores the identity reference only — never a copy of the goal's objective or criteria. Several teams bound to one goal are a legal, first-class shape.
- **`handoff_ref` — the reverse key.** When a spec-side handoff contract hands construction work to this team, the team definition carries `handoff_ref`, a spec-dir-relative path back to that contract. It is written by the engine's binding action; the contract and the two definitions form a three-way key pair. The contract's shape is owned by `.specify/skills/internal/create-team/references/handoff-contract-template.md`.
- **Team lifecycle.** The team's lifecycle is its own pair — `active` / `archived` — never the goal's three values. An `archived` team is refused by `run-team`; reviving it is an explicit modify, never a side effect.
- **The construction crew (施工队).** A team bound to a goal under an active handoff contract is the **construction crew** of the design-vs-construction split: the spec side keeps design authority (`requirements.md`, `tasks.md`, `verification.md` and the contract itself are spec-side writes), the crew executes inside its declared territory and writes back one record per completed task. The two lines are peers; neither requires the other, and the handoff is the only documented collaboration shape.
- **Creation timing** is read from `.specify/shared/declarations/facts/goal-team-handoff-threshold.yaml`: a direct run creates no team, a handoff run creates it after `tasks` U4, and a command run declares its creation moment in its command template. This section does not restate the threshold or the timing labels.
- **Stage dimension is not the SDD stage roster**: the Team's own `Stage` values remain `executor` / `evaluator` / `optimizer`. The canonical SDD stages exist only as `stage_seats` keys, each carrying its seats and `max_parallel`.
- **Dynamic roster**: the number and type of agents per stage are implementation details decided by the work-package benefit test, effective concurrency, and checkpoint evidence. No fixed per-stage count is a contract.
- **One definition per slug**: multiple runs append `runs/` and checkpoints rather than creating new team directories.

## Template home

The multi-agent authoring templates (team-supervisor, the three EEI stages, and the parallel/serial/triad orchestration templates + workflow schema) live in `.specify/skills/internal/create-team/templates/agents/` (installed mirror: `.specify/skills/internal/create-team/templates/agents/`). The single-agent **capacity** templates (`agent-capacity-<X>-template.md`) and the custom/project-custom scaffolds remain in `.specify/skills/internal/create-agent/templates/`. The `continuous` operating discipline is documented in [`operating-loops.md`](operating-loops.md).
