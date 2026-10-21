# Goal Definitions Reference

Canonical definition of the **Goal** concept in Spec Kit, its boundary against **Requirement**, the criteria authority rule, the singularity rule, the **Target** decomposition, and the Goal–Team binding. This file is the single source of truth for the Goal concept; other documents (`/speckit.team`, `skills/internal/create-team`, the glossary) link here rather than re-defining it. It sits alongside the other concept anchors: `tool-definitions.md`, `agent-definitions.md`, `subagent-definitions.md`.

## What a Goal Is

A **Goal** is a **project-level, first-class concept**: an **authored fact source** (never a derived artifact) that states a desired end state and how to tell it has been reached. Its **object is unrestricted**: a Goal may describe any desired outcome in any dimension — it is not limited to what the project's code implements (see Goal Dimensions below). It is persisted under `.specify/goal/<goal-slug>/` and is composed of exactly three parts:

1. **Goal narrative** — the desired end **outcome** (north star). Outcome, not steps: a Goal MUST NOT be written as a task list, an implementation plan, or a sequence of phases.
2. **Verifiable success criteria** — thresholds / satisfaction conditions that an evaluator (a program or a scoring agent) can measure progress against.
3. **Lifecycle state** — `active` / `achieved` / `abandoned`. Terminal Goals are retained, never deleted (see Goal Archive).

A Goal MAY additionally carry a **Target decomposition** (see Target Decomposition below). Like timestamps, Targets are an **annex** around the concept — never a fourth composition part.

Also annexes, on the same footing as Targets and timestamps — optional, never composition parts:

- **Readable title** — a presentation-layer heading. **Identity stays the directory slug**: a title is never a second identifier, never takes part in resolution, binding, or reference, and its absence simply leaves the slug as the heading.
- **Boundaries** — the exclusions the author states as out of scope for this Goal. They narrow *interpretation*, never the objective, and never substitute for a Target: an exclusion is what the Goal is not, a Target is a slice of what it is. An absent Boundaries annex records that no exclusion was stated — not that nothing is excluded.

Two operating properties follow:

- **Measured by degree**: a Goal is *pursued*; its verification is progress-shaped (percentage, threshold attainment, evaluator scores) — not a per-clause pass/fail.
- **Modified deliberately**: changing a Goal is a strategic act — the change is recorded and history is preserved; silent drift is prohibited.

### Goal Dimensions (illustrative, not a closed taxonomy)

Goals and Requirements live on **different planes** (decided 2026-08-04): a Requirement describes what the **current project's source code or configuration** must implement (a feature); a Goal may target **any dimension** of desired outcome, including ones no Requirement could ever express. Illustrative dimensions:

| Dimension | Example Goal | Why it is not a Requirement |
|-----------|--------------|-----------------------------|
| **Framework / harness itself** | "I want the spec-kit framework this project uses to stay continuously updated" | Its object is the toolchain, not this project's code — no FR on this repo can implement it |
| **Codebase-wide convention convergence** | "I want all project source code to be standard-idiomatic Golang" | A cross-cutting end state pursued by degree across the whole codebase, not a per-feature clause |
| **Delivered-capability outcome** | "I want feature X to run on platform Y" | An outcome about a capability in a target environment; Requirements specify the implementation, the Goal states the environmental end state being pursued |

Boundary note: when a dimension-2-style desire is frozen into a **binding rule** enforced by gates, it belongs to the **Constitution** (a governance principle); when it binds one deliverable as a testable clause, it is a **Requirement**; when it is a desired end state pursued and measured **by degree**, it is a **Goal**. The same sentence can move between the three homes only by deliberately changing its nature.

## Goal vs Requirement

**Goal** and **Requirement** are independent, parallel first-class concepts on **different planes** — **there is no necessary hierarchy between them** (decided 2026-08-04). A Requirement's object is fixed: this project's source code / configuration and the feature they implement. A Goal's object is free: any dimension of desired outcome.

| Dimension | Goal (目标) | Requirement (需求) |
|-----------|------------|--------------------|
| Object (作用对象) | Unrestricted — framework/harness, codebase conventions, delivered-capability outcomes, … (any dimension) | The project's source code / configuration — what feature they must implement |
| Essence | Desired end state + attainment criteria | Binding clauses on a deliverable |
| Question answered | *why / whither* — toward what, to what degree | *what / how-correct* — what MUST hold, what counts as done right |
| Home | `.specify/goal/<goal-slug>/` (authored fact source) | `.specify/specs/<ID>-<slug>/requirements.md` (bound to one Feature) |
| Shape | Singular narrative + criteria per Goal | Enumerated clauses (FR-xxx / SC-xxx) |
| Verification | By degree — progress, thresholds, evaluator scoring | Binary — per-clause pass/fail against tests and acceptance scenarios |
| Change discipline | Deliberate modification with recorded history (no silent drift) | Clarification/revision flow (Clarifications sessions, re-gated spec) |
| Failure semantics | Not yet attained → keep iterating / adjust strategy / deliberately re-scope | Not satisfied → implementation non-conforming, delivery blocked |
| Anti-pattern | Written as a task list / implementation steps | Written as an untestable aspiration |

**No structural link (decided)**: a requirements spec carries **no** Goal field — `requirements.md` does not reference a `goal-slug`, and a Goal never enumerates the FRs "under" it. When work on a Feature happens to advance a Goal, that connection surfaces **observationally** — in evaluation results, team summaries, and run reports — never as a mandatory field in either artifact. Neither concept derives from, contains, or validates the other.

**Litmus tests** (when writing a sentence, decide where it belongs):

1. **Deletion test** — deleting it loses *direction* → Goal; loses a *contract* → Requirement.
2. **Verification test** — verifying it needs scoring/progress → Goal criterion; needs a pass/fail check → Requirement clause.
3. **Change test** — changing it is a strategic decision with history → Goal; a clarification + spec revision → Requirement.
4. **Subject test** — the sentence's subject is an executing subject ("the team reaches …") → Goal; a system/deliverable ("the system MUST …") → Requirement.
5. **Object test** — it constrains what this project's source/config implements → Requirement; its object lies beyond the implementation surface (the framework itself, codebase-wide convergence, runtime/platform outcomes) → Goal.

## Criteria Authority Boundary

Success-shaped statements exist in both worlds; their authority is disjoint (decided 2026-08-04):

- **SC-xxx** (Success Criteria in a requirements spec) serve **only their own Feature** — they measure that Feature's delivery and nothing broader.
- **Goal success criteria** are **cross-feature** — they measure the end state regardless of which Features contributed.
- Criteria MUST NOT be copied between the two stores. Cross-feature aggregation happens at the **evaluation/summary layer** (evaluators, team summaries), with each side citing its own source — never by restating one store's criteria inside the other.

## 判据主体指代形 (Criterion Subject Reference)

一条 goal 成功判据常常是对**一组同类制品**的断言(「每个绘图技能都……」)。把成员逐个打进判据文本,判据就会随目录增删而失真:本仓唯一真实的枚举型判据正是这样被反复改写的——`.specify/goal/draw-two-layer-structure/goal.md` 的 `## History` 里留着「六个绘图技能」与「七个绘图技能」两个前值,改的都是同一条判据。故判据 MAY 改用**指代形**,让主体集合在**解析那一刻**由仓库现状导出,而不是取自判据文本里的成员枚举:

`[subjects: <glob>]`

- **相对仓根**解析,命中集 = 各命中路径相对仓根的名字,已排序去重。
- 指代形写在判据文本内、位置不限;一条判据 MAY 含零个或一个指代形(含两个即落入下面的冲突档)。
- **纯枚举判据的解析行为完全不变**:不含指代形的判据不导出任何集合,解析器对其返回值与引入本节前逐字段一致,既有 goal 定义无需迁移即可继续解析。
- 导出是**解析期的只读动作**:它读仓库现状,不写任何文件,也不改判据文本。

### 两档失败,互相可区分

导出为空**不是**通过——「零个主体全部满足」是空真,故两档都报错;而两档报的**不是同一件事**,修法相反,所以 MUST 分档而不是合并成一个「无主体」:

| 档 | 触发条件 | 报告前缀 | 通常的修法 |
|---|---|---|---|
| 路径不存在 | 字面前缀(第一个通配段之前的那段路径)在仓内不存在 | `SUBJECT MISSING:` | 多半是写错或目录已迁移——改指代形 |
| 导出集为空 | 字面前缀存在,但命中 0 条 | `SUBJECT EMPTY:` | 目录真的空了,或指代形过窄——去看目录 |

两档都使 `goal-utils.py validate` 判为不通过(退出码 `4`)。把它们分开的是**报告前缀**,不是退出码:退出码相同而前缀不同,作者据此知道该改指代形还是该去补目录。

### 冲突,与其不可机械判定的边界

一条判据同时携带指代形与**花括号展开记号**(`{a,b}` 一类)时 MUST 报 `SUBJECT CONFLICT:`——同一主体集既有导出来源又有手打副本,静默择一会让二者悄悄分叉,而分叉是不可见的。

**诚实边界**:判据里的**散文枚举**(「所有绘图技能」「draw-diagram 与其余六个」)不带任何机器可辨记号,与指代形同现时**检不出**,因为自由散文里的枚举不可机械判定。故本节的冲突规则**只**覆盖花括号展开记号这一种可判定形态,MUST NOT 被读成「枚举与指代形共存已被守卫」。散文枚举与指代形同现时,以指代形导出的集合为准,散文部分只是给人读的叙述——这不是守卫,是取舍。

### 第二个解析器的处置

`.specify/skills/internal/create-team/scripts/build-summary-input.py` 有自己的**本地** goal 判据读取器,其 `load_goal_definition` 的注释明写:该脚本与 `.specify/scripts/python/goal-utils.py` 分属两棵镜像树(`skills/` 与 `.specify/scripts/`)且相对深度不同,跨树 import 在安装到消费项目后即断,故刻意本地解析。**处置:让它同样理解指代形**——就地做同一导出,并把指代形渲染成成员名再交给总结,使读者不会看到一个自己无从解析的裸标记;MUST NOT 靠加一个 import 来解决。**代价明示**:于是仓内并存两处导出实现,二者的一致性由 `tests/contract/test_criterion_subject.py` 对同一输入断言两侧成员一致来钉住,而不是靠人记得同步——把同步交给记忆,正是本节要消灭的失效模式。

### 退出码约定在本仓并不统一

同一份 `build-summary-input.py` 另有自己的退出码表(`EXIT_OK, EXIT_INPUT_ERROR, EXIT_NO_MATERIAL = 0, 2, 3` 与 `EXIT_SERIALIZED = 4`),其 `3` / `4` 与 `goal-utils.py` 的 `EXIT_NOT_FOUND` / `EXIT_INVALID` **语义相左**——即仓内并存第五套退出码约定。本节记录该分歧而**不**统一它(统一超出本概念文档的职权,且会改动一个已安装脚本的对外契约):读某一处退出码表 MUST NOT 被当作通吃全仓。

## Singularity Rule

One Goal = one objective (decided 2026-08-04):

- **Per Goal definition**: a Goal MUST NOT bundle several objectives into one composite definition — split them into separate `goal-slug`s, each with its own directory and lifecycle.
- **Per executing subject**: a team binds to exactly **one** Goal at a time (see Binding below). A team that "pursues two goals" is either two teams or a Goal that needs deliberate re-scoping.
- The **project** may hold multiple `active` Goals concurrently — each is its own `goal-slug`, each advanced by its own team(s).
- Decomposing one objective into **Targets** (see Target Decomposition below) does not breach singularity: Targets are slices of the same objective, never additional objectives.

## Target Decomposition (目标切片)

A **Target** is a **sub-outcome under exactly one Goal**: an independently advanceable, completion-judgeable **scope slice** of the same end state (decided 2026-08-11; operational surface specified by requirement `038-goal-target`). Targets give the Goal — a large, slow-moving concept — a **run-sized control point**: a team run can be pointed at one Target without touching the Goal–Team binding, the Goal's identity, or the summary delivery directory.

```
Goal (authored end state)  1 ── N  Target (run-assignable scope slice)  1 ── N  runs / work items (TI-xxxx)
```

Four defining properties:

1. **An annex, never a fourth part.** The decomposition is optional: a Goal without Targets is fully valid and behaves exactly as if the mechanism did not exist. Adding Targets changes neither the narrative, nor the criteria, nor the lifecycle.
2. **Outcome-shaped, recursively.** GD-2 applies at Target scale: each Target states a sub-**outcome** ("log component split complete"), never a step. The Target set is an **unordered set** — identity ordinals carry no execution-order semantics; an ordered target list is an implementation plan wearing a goal's clothes.
3. **Subordinate, not independent.** GD-3 litmus at this boundary: a Target must be a slice of its parent objective. A candidate that would stand as a meaningful end state of its own is a separate Goal — split it, do not nest it.
4. **A tree, not a graph.** A Target belongs to exactly one Goal; 1 Goal : N Targets; N runs : 1 Target. Cross-goal Targets do not exist, and Targets carry no dependency edges between them.

**Identity.** Local form `T-<nnn>` — issued monotonically within the goal, never reused. Qualified form `<goal-slug>.T-<nnn>`, dot-namespaced after the `<team-slug>.TI-<nnnn>` precedent and legal under the shared identity grammar (which admits `.` but not `#` or `/`). Lifecycle is exactly `open` / `done` / `dropped`; terminal Targets are retained with their state, never deleted.

**Two progress axes — never conflate.** Success criteria measure **end-state attainment** and remain the sole authority for `achieved`. Targets measure **scope coverage** (n of m slices done). All Targets complete does NOT make a Goal achieved; criteria are never derived from Targets, and Targets never restate criteria (the criteria authority rule extends to Target statements). At the summary layer, milestones (`MS-<nnnn>`) remain criteria projections; completed Targets MAY additionally feed milestone entries under a distinct source marker — a presentation-layer concern owned by the summary mapping, not by this definition.

**Write model — authored lifecycle, derived progress.**

- *Authored*: a Target's statement and its deliberate lifecycle live inside the Goal's definition file (a `## Targets` section; exact layout owned by the implementing feature) and are written **only via `/speckit.goal`** — the sole-authoring-entry rule is unchanged. Teams and runs may **propose** Targets or completions; a human ratifies through `/speckit.goal` (propose → ratify, as in `coordinate`).
- *Derived*: per-Target execution progress is folded from team ledgers (`items.jsonl` rows carrying a `target_ref`) at summary time and is never written back into `goal.md`. When authored state and evidence disagree (state `open`, yet every attributed item is complete), the discrepancy is surfaced for ratification — never auto-flipped.

**Run assignment.** A team run MAY name one Target under the team's **bound** Goal. The reference is validated — a dangling or terminal Target is reported, never silently accepted — and a run that names no Target runs against the Goal broadly, exactly the pre-Target behavior. Work items attribute to the Target through the ledger's `target_ref`.

## Storage & Goal Archive

```
.specify/goal/
└── <goal-slug>/     # one Goal definition — narrative + criteria + lifecycle state
```

- **Goal Archive** = the whole `.specify/goal/` tree: the materialized "current & historical goal list" of the project. Terminal (`achieved` / `abandoned`) Goals stay archived — never deleted.
- This document fixes only the **location and semantics**; the file layout inside `<goal-slug>/` is owned by the feature that implements Goal management.

## Goal–Team Binding

- A team references its Goal by **one-way identity**: the team declares a `goal_slug`; the binding is **N teams : 1 Goal**. The team side stores the identity only — never a copy of the Goal content.
- **Team Goal** therefore means *the reference* — which project-level Goal this team serves. Team evaluators measure progress against the referenced Goal's criteria.
- **Migration fallback**: teams created before Goal management exist may still carry an inline goal in `team.md`; wherever a Goal definition exists, the definition is authoritative and the inline copy is legacy.
- **Run-level Target assignment**: the binding axis stays team ↔ Goal and stays static. The run-sized variable is the **Target**: a run may select one Target **inside the bound Goal** — this never rebinds the team, never alters goal-identity resolution, and never relocates the summary delivery directory. See Target Decomposition.

## Terminology Boundaries

| Term | Meaning | Where defined |
|------|---------|---------------|
| **Goal** (this document) | Project-level authored end-state definition (narrative + criteria + lifecycle) | here; store `.specify/goal/<goal-slug>/` |
| **Goal Archive** | The `.specify/goal/` tree — current & historical Goals, terminal ones retained | here |
| **Goal–Team Binding** | One-way `goal_slug` reference, N teams : 1 Goal, identity-only | here |
| **Team Goal** | A team's reference to the project-level Goal it serves | here; declared in `.specify/teams/<slug>/team.md` |
| **Requirement** | Feature-bound spec of testable clauses (FR/SC) driving plan → tasks → implement → verification | `.specify/specs/<ID>-<slug>/requirements.md`; `/speckit.requirements` |
| **Feature** | Long-lived capability entry in the feature index | `.specify/memory/features.md` |
| **Success Criteria (SC-xxx)** | Per-feature measurable outcomes — authority limited to their Feature | requirements spec of that Feature |
| **Team** | Multi-agent structure organized around (exactly one) Goal | `/speckit.team`, `skills/internal/create-team` |
| **Target** (this document) | Run-assignable sub-outcome (scope slice) under exactly one Goal — an annex to the definition, unordered, authored via `/speckit.goal` | here; persisted in `.specify/goal/<goal-slug>/goal.md` (`## Targets`) |
| **`target_ref`** | A ledger work item's attribution to a Target (`T-<nnn>`) | `items.jsonl` contract (`skills/internal/create-team`, summary mapping) |
| **"target" elsewhere** | `optimization_target` / `co_targets` (the artifact an iteration loop mutates), a territory entry's `target` field, the `--target` flags of the evidence/interview engines — all **unrelated** to Goal Targets | their owning docs; glossary disambiguation |
