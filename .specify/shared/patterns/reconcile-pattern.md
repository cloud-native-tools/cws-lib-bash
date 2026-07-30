# Reconcile Pattern (调谐模式) — A Design Pattern for Agents & Skills

A reusable design pattern for any agent or skill whose job is to keep a **durable artifact space** (a directory tree, a set of config files, a registry document, a knowledge base) converged toward an ideal form over many invocations. Borrowed from the Kubernetes Operator mental model, adapted for LLM-driven work.

Distilled from two production configuration-management skills that each collapsed 3–6 accumulated "modes" into a single reconcile engine.

## When to Apply (适用判据)

Apply this pattern when **all** of these hold:

1. The unit **owns a durable artifact space** with a describable ideal form (templates + rules + principles), and is invoked **repeatedly across the artifact's lifetime** — not a one-shot generator.
2. **Mode proliferation** has started or is likely: initialize / update / reorganize / health-check / intake variants that all read and write the same space.
3. Some desired properties are **semantic** (only an LLM can judge conformance) while others are **deterministic** (existence, naming, size, link integrity).

Do **not** apply to: one-shot pipelines (generate a report, render a diagram), read-only analysis, or purely conversational flows.

## Boundary: Reconcile vs Continuous Operating Loop (概念消歧)

This pattern is easily confused with the **continuous operating loop** defined in [`skills/create-team/references/operating-loops.md`](../../skills/create-team/references/operating-loops.md) — both are "repeated runs + LLM judgment + state files". The root difference is **what is processed + when it terminates (处理对象 + 终止语义)**:

| Dimension | Reconcile (this pattern) | Continuous operating loop |
|-----------|--------------------------|---------------------------|
| Processing object | One durable artifact space (tree / config / registry / KB) with a describable ideal form | An unbounded stream of incoming work (CI failures, new PRs, issues, dependency updates) or a quality metric to sustain long-term |
| Paradigm | Declarative: desired vs current → diff → converge to consistency | Operational: process by cadence, no terminal "done" |
| Per-invocation termination | Closes within one call (R0–R6 loop completes in a single invocation) | One run = one bounded cycle (steps 1–8); the overall lifecycle is unbounded |
| Outer repetition driven by | User / on demand (invoked when convergence is wanted) | Cadence / cron scheduling, possibly unattended |
| Guardrail focus | Tolerance band (anti-churn) + archive-not-delete (anti-data-loss) + tiered confirmation | Maturity L1→L2→L3 + budget/circuit-breaker/kill-switch + independent verifier + attempt caps |
| Human position | Present at every invocation, gating destructive actions via tiers | L3 may run unattended, stopping only at boundaries — hence kill-switch/budget |
| Org structure | A design pattern inside one skill/agent (fan-out optional) | A multi-role team (supervisor / worker / independent verifier) |
| State-file semantics | snapshot / plan / audit / residual — describes one invocation's convergence transaction | STATE.md spine + run-log + post-run critique — cross-run memory and promotion evidence |

**Nesting, not competitors (嵌套关系，不是竞品)**: reconcile is a convergence engine that finishes *within one invocation*; the operating loop is the cross-invocation scheduling + governance shell that decides *when to act and with how much autonomy*. Inside a continuous team's cycle, if the TRIAGE→ACT work happens to be "keep artifact space X converged", it may invoke one full reconcile loop — **an operating loop can wrap a reconcile loop, never the reverse**.

**判定口诀 (rule of thumb)**: 有可描述的制品理想形态要反复收敛 → reconcile；有源源不断的工作、或要按节奏长期改进的指标 → continuous 运营循环。

**Near-synonyms not to conflate (容易张冠李戴的近义概念)**:
- 容忍带 (reconcile, skips cosmetic diffs) ≠ quality threshold / scoring (operating loop, per-cycle acceptance)
- audit log / residual report (reconcile, per invocation) ≠ STATE.md + post-run critique (operating loop, cross-run promotion evidence)
- 分级确认门禁 (human present) ≠ 成熟度 + kill-switch (unattended-capable)
- 只归档不删除 (reconcile) ≠ 路径黑名单 / 约束文件 (operating loop)

## Core Model (核心模型)

- **Desired state (期望态 / spec)** = the artifact space's ideal form, assembled from: templates + rules/thresholds + principles + authoritative external facts + **existing local content** (local conventions outrank templates) + **this invocation's user input**.
- **Current state (当前态 / status)** = what is actually on disk in the artifact space.
- **Reconcile (调谐)** = one loop: observe current state → compute desired state → diff (through the tolerance band) → converge (dry-run + tiered confirmation) → verify until consistent.

### Two deliberate divergences from the K8s Operator (与 Operator 的本质差异)

1. **Fuzzy desired state — judge, don't field-match (模糊期望态)**: the ideal form is semantic/intent-level and cannot be diffed field-by-field. The LLM judges "is the current state already sufficiently conformant?"; only deterministically decidable properties (path/naming existence, line/KB thresholds, link resolution, marker integrity) are enforced by rules or scripts.
2. **Tolerance band + archive-not-delete (容忍带 + 只归档不删除)**:
   - **Tolerance band**: within-threshold differences are marked "consistent (tolerated)" and **never enter the convergence plan** — this prevents churn where every invocation rewrites cosmetic diffs.
   - **Archive-not-delete**: content that exists in the current state but not in the desired state is **moved to an `archive/` area, never `rm`'d or overwritten**. The pattern has no "delete" concept, only "archive". Transient scratch areas (`tmp/`) may be exempted as cleanup *suggestions* left to the user.

## Single-Engine Collapse (模式坍缩)

All accumulated modes are **the same engine under different inputs** — do not maintain separate mode workflows:

| Legacy mode | Reconcile expression |
|-------------|----------------------|
| Initialize / bootstrap | Reconcile of an empty artifact space (desired state = full initial skeleton) |
| Directed update | User input merged into the desired state → targeted convergence |
| Reorganize / restructure | Structure-dimension convergence |
| Health check / maintain | R1–R3 + report only (converge on confirmation) |
| Intake / archive material | Fan-out reconcile carrying new facts |

## Scope Resolution (作用域判定)

Resolve the invocation's scope **before** entering the loop:

| Input | Scope | Behavior |
|-------|-------|----------|
| No arguments | **Full sweep (全量)** | Run the complete loop on every managed target (parallel subagents allowed, one per target, no cross-target writes) |
| A target path/name | **Single target (单目标)** | Reconcile only that target; with supplementary instructions, converge directionally |
| Raw material without a single target | **Fan-out (扇出)** | Decompose → triage per information domain → converge multiple targets |
| Target exists but core files absent | **Bootstrap** | Init variant: generate skeleton from scratch |

## The Reconcile Loop (调谐环 R0–R6)

```
- [ ] R0 Mandatory pre-hooks + load baseline
- [ ] R1 Observe current state        → artifact: observation snapshot
- [ ] R2 Compute desired state
- [ ] R3 Diff per dimension (tolerance band first)
- [ ] R4 Dry-run plan + tiered confirmation gates → artifact: plan
- [ ] R5 Converge (archive-not-delete)            → artifact: audit log
- [ ] R6 Verify + residual report                 → artifact: residual report
```

- **R0 — pre-hooks + baseline**: run mandatory pre-hooks first (see Optional Components: derived-fact refresh, input vocabulary validation), then load the desired-state baseline: templates + thresholds + layout rules + local existing content. **Local established conventions outrank shipped templates.**
- **R1 — observe**: scan only the managed zone (see Scope Zones below). **Mandatory artifact — observation snapshot** (inline): managed tree status, core-file existence/size vs thresholds, stray files, layout deltas. Without the snapshot, R3 cannot diff dimension-by-dimension.
- **R2 — compute desired state**: synthesize the sources. If underdetermined, ask the **minimum necessary questions (≤ 3)** plus automatic probing — never fabricate the desired state.
- **R3 — diff, tolerance band first**: for each dimension, first ask "already sufficiently conformant?"; only substantive deviations enter R4. Typical dimensions: core content, structure/layout, size thresholds, link/reference integrity, external-source sync, derived distributions, vocabulary.
- **R4 — dry-run plan + tiered confirmation**: aggregate convergence items into a plan. Move/archive/restructure plans are **written to a plan file** (with `[x]/[ ]` opt-out rows); pure-write plans may be shown inline. No disk writes happen while planning.
- **R5 — converge**: execute confirmed items (`mkdir → write → mv → audit`). Same-name targets are never clobbered (suffix `__<ts>`). On any `mv` failure: stop remaining items, keep succeeded ones, record, ask for human review. **Mandatory artifact — audit log** (file in the artifact space): timestamp, scope, per-item action + source→target + result, tolerated summary, rollback basis. **Write it even when nothing converged** ("all dimensions within tolerance") so every reconcile leaves a trace.
- **R6 — verify + report**: re-check consistency (layout vs declared constraints, size budgets, link resolution). **Mandatory artifact — residual report** (inline): converged / archived / tolerated / pending-human-decision, plus verification results. If the run produced no net enrichment, say so honestly.

### Tiered confirmation (分级确认门禁)

| Action class | Gate |
|--------------|------|
| Safe local writes (create/append managed files, mkdir, fix links, update indexes, annotate corrections) | **Auto-execute**; never clobber, conflict → `__<ts>` suffix |
| Writes to an **external authoritative source** (issue trackers, platforms, registries outside the space) | **Stop and confirm** (authoritative-source-first discipline) |
| **Destructive / move / archive** (mv to archive, restructure) | **Stop and confirm** via the dry-run plan |

### Scope zones (作用域纪律)

Declare zones up front and never blur them: **A — managed zone** (the pattern reads and writes here); **B — read-only zone** (observe, never modify; secrets: don't even read contents); **C — anchors** (always skip). Derived/distributed files owned by a hook (see below) are rewritten only by that hook, never hand-edited.

## Optional Components (可选组件)

- **Semantic routing (语义路由)**: a table mapping user-intent signals → target file/section, so users never need to know the internal layout. Single intent → direct write; multiple intents → route one by one; ambiguous → ask.
- **Derived-fact refresh hook (派生事实刷新钩子)**: when the space consumes a distribution derived from an external fact source, gate regeneration on a **content signature** — signature match → zero writes; mismatch → regenerate the consumption copy. The fact source stays single; derived copies are never hand-edited.
- **Input vocabulary validation (词汇表校验钩子)**: before semantic routing, validate proper nouns in user input against a shared glossary (voice/typing homophone errors); auto-correct registered variants, ask about unknowns, write confirmed terms back (append-only). Never let a suspect name silently land.
- **Fan-out intake (扇出调谐)**: decompose one raw document into items, triage each to its owning target, converge per target; un-triageable residue goes to a default target rather than being dropped.

## Applying the Pattern (设计与改造清单)

Designing a new reconcile-style skill/agent, or retrofitting an existing one:

1. **Name the artifact space** and draw the A/B/C scope zones (+ where `archive/` lives).
2. **Enumerate desired-state sources** in precedence order (templates < rules < principles < external facts < local conventions < this-run user input).
3. **Enumerate diff dimensions** and, per dimension, what is deterministic (rule) vs semantic (judgment), and the tolerance band.
4. **Assign confirmation tiers** to every action class the engine can take.
5. **Define the four mandatory artifacts** (snapshot / plan / audit log / residual report) and where they live.
6. **Collapse existing modes** into the scope-resolution table; keep the skill entry (SKILL.md / agent file) as a thin **dispatch layer** (scope + intent + coordination) and sink the engine detail into a `references/reconcile.md`-style sub-document.

## Anti-patterns (反模式)

- **Mode proliferation**: adding a new top-level mode instead of a new input to the one engine.
- **Silent deletion**: any `rm`/overwrite of current-state content — always archive.
- **Converge without a plan**: executing moves/archives that never appeared in a confirmable dry-run.
- **Churn**: converging cosmetic diffs because no tolerance band was defined.
- **Un-audited runs**: finishing a reconcile with no audit log (even a no-op line).
- **Fabricated desired state**: guessing what the user wants when sources underdetermine it — ask the ≤ 3 minimum questions instead.
