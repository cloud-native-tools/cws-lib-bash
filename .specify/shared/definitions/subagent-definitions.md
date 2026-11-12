# Subagent Definitions Reference

Canonical definition of a **Subagent**, its three execution modes, the mode-selection rules, and the visibility contract for external CLI dispatch. This file is the single source of truth for the Subagent concept; other documents (`/speckit.agents`, `/speckit.team`, `skills/internal/create-team`) link here rather than re-defining it.

**Position in the Agent taxonomy**: a subagent is the **Agent Execution** layer of the three-layer model defined in [`agent-definitions.md`](agent-definitions.md) — *Agent Template → Agent Instance → Agent Execution* — viewed from the orchestrator that delegated it. This document governs only the Execution layer: how an Agent Instance's definition becomes a live run, and how that run stays observable.

**Super agent pointer**: the parent-side relative logical role on a dispatch edge — the endpoint that created the child execution — is owned by [`superagent-definitions.md`](superagent-definitions.md). The parent-side role is owned there; this page owns the child side.

## What a Subagent Is

A **Subagent** is a **task-scoped delegated worker**: an orchestrator (the main session or a team supervisor) hands it a bounded task brief plus an **independent prompt and configuration**, it executes autonomously within that scope, and it delivers a result through an agreed contract (returned message, result manifest, or declared output paths).

Three properties hold regardless of execution mode:

1. **Independent prompt & config** — the subagent runs under its own system prompt / tool list / model settings, derived from its **Agent Instance** definition (`.specify/agents/instances/<name>.agent.md`, or a Template under `.specify/agents/templates/`) plus its dispatch config (`.specify/agents/execution/configs/<name>.yaml`) or dispatch payload, not from the orchestrator's conversation.
2. **Bounded task scope** — it receives exactly one task brief (plus its territory manifest in team runs), never the orchestrator's full history.
3. **Result contract** — completion is signalled through a defined channel, so the orchestrator can tell "done" from "still running" from "failed".

A subagent is a running **Agent Execution**; the **Agent Instance** is the definition it is launched from (which in turn derives from an **Agent Template** — see [`agent-definitions.md`](agent-definitions.md)). The same Instance can be executed multiple times, sequentially or concurrently, without affecting the definition.

## The Concurrency Obligation (并发义务 — 所有执行体的单一声明位点)

**Owner note**: this section is the three-part obligation's authored statement. Every execution body — a skill or command body, a goal slice, a team, a loop stage — reaches it by path and MUST NOT restate its text. The closed class table and each class's own obligation text are owned by `.specify/shared/declarations/facts/concurrency-class.yaml`; the serial-reason vocabulary by `.specify/shared/declarations/facts/serial-reason.yaml`; the reading's three fields and the `not_evaluated` literal by `.specify/shared/declarations/facts/effective-concurrency.yaml`; the slot cap, verifier reserve and budget bound by `.specify/shared/declarations/facts/concurrency-slot-and-reserve.yaml`. None of those values is copied here.

Every execution body carries the obligation in three **separately checkable** parts:

1. **Consider concurrency first (先想并发)** — partition the duty into the units its grain defines before choosing an execution shape. A body that never asked the question is `obligation-incomplete`, whichever shape it then ran.
2. **Dispatch concurrently when allowed (能并发则并发)** — the **default is concurrent**: whenever the body's class, the units' independence, file-level write-domain disjointness, a legal process carrier (see § Three Execution Modes) and the budget allow, the units run concurrently. Concurrency is never an optional enhancement that a body may simply decline.
3. **…and otherwise name the reason and record the reading (串行须具名理由并记读数)** — a serial result MUST carry a reason code from the closed vocabulary plus that code's declared evidence form (a bare `.` is never evidence), and every advancing unit records the `requested` / `effective` / `effective_reason` triple, with the literal `not_evaluated` wherever the intervals are absent — never `0` and never an estimate. A serial shape with no code is `code-required`; a record with one or two of the three fields is `reading-incomplete`; a concurrent pattern carrying serial codes (or a serial pattern carrying none) is `form-reason-inconsistent`.

**Pre-action assessment (动作前评估 — the obligation's execution face).** Before the first real action, the body
runs one assessment and records its outcome: (a) the unit **class** (the class fact, or
`concurrency-check.py classify --repo .`); (b) the legal **carrier** (`concurrency-check.py capability` — the
external fork/subprocess carriers are the concurrency mechanisms); (c) the **partition** — the duty's units at
the body's grain. Two or more independent units with disjoint file-level write domains and a legal carrier make
the shape **concurrent**; otherwise it is serial with a reason code and that code's declared evidence form. The
outcome IS the `requested` / `effective` / `effective_reason` reading: no user instruction is needed to enable
concurrency (it is the default), and a body that skips the assessment is `obligation-incomplete`.

The grain decides what a "unit" is; the obligation is the same statement at every grain. The examples below are illustrations, not a second rule set:

| Grain | Unit | The grain's own pointer |
|-------|------|-------------------------|
| skill or command body | work package / bounded step group | the body's own text; class table: `.specify/shared/declarations/facts/concurrency-class.yaml` |
| goal slice | target | [`goal-definitions.md`](goal-definitions.md) § Target concurrency |
| team | seat group | `.specify/skills/internal/create-team/references/conceptual-model.md` |
| loop stage | stage package (driver) / entry (house-keeping) / step (project-setup) | `.specify/skills/sdd-loop-driver/SKILL.md` and its `references/decomposition-model.md` |

The obligation at authoring time knows none of the tuning values — the slot cap, the ceiling, the per-unit budget and the effective bound are read at execution time through the facts named above (C-043). The reading triple and its `not_evaluated` literal are the only concurrency metric; a dispatched count, a configured value or a neighbouring run's number is not a reading.

**The declaration is falsifiable against its run record (C-057)**: a body that declares concurrency MUST emit at least the dispatched unit ids and their intervals; a body that cannot emit them MUST declare serial and say why. The unit record is the evidence — a declaration without a record is unproven, and a record showing one executor in sequence is `declaration-execution-mismatch`, never concurrency evidence.

### class-concurrent-by-default — concurrent-by-default (`work-package`)

**Obligation**: `must-concurrent` (value owner: `.specify/shared/declarations/facts/concurrency-class.yaml`; the decision rule that assigns a body to this class is owned there too). A skill or command body partitions its own duty into work packages and runs them concurrently whenever the FR-005 conditions hold. A serial result is never a free choice: it carries a reason code from the closed vocabulary plus that code's form-matching evidence — a non-empty string such as `.` is not a basis — and the run records the reading triple. Membership is decided by the fact's `(root_id, produced_shape)` rule, never by this section.

### class-partition-required — partition-required (`target-or-seat-group`)

**Obligation**: `must-concurrent` (value owner: `.specify/shared/declarations/facts/concurrency-class.yaml`). A goal's targets or a team's seats ARE the unit set the body produces, so a single-unit execution is itself a decision that MUST be recorded — the target set is exactly one, or the serial reason is named — never a silent default. Partitioning is judged before dispatch: intersecting target or seat write domains are red at binding time.

### class-serial-only — serial-only (`executor-run`)

**Obligation**: `may-serial` (value owner: `.specify/shared/declarations/facts/concurrency-class.yaml`). An agent definition's own advance is a single executor run, so it may proceed serially; it names which host or dependency condition applies by pointing at `.specify/shared/declarations/facts/serial-reason.yaml` rather than restating the vocabulary, so the class is not a free pass.

## Three Execution Modes

The word "subagent" covers three materially different execution mechanisms. Keep them distinct — they differ in isolation, parallelism, and how (or whether) their progress is observable.

| Mode | Mechanism | Isolation | Parallelism | Progress visibility |
|------|-----------|-----------|-------------|---------------------|
| **1. Native subagent** | The executing agent runtime dispatches subagents itself (e.g. Claude Code `Agent`/`Task` tool, Qoder CLI native subagents) | Runtime-managed context isolation | Runtime-dependent; **not a concurrency carrier** (see the ban below) | Native — the host UI renders the subagent's activity |
| **2. Virtual subagent** | The executing tool has **no** subagent capability; the current session *simulates* one: it adopts the agent definition's independent prompt/config and executes the task itself, in-session | None — shares the session's context, budget, and tools | None — strictly sequential | Inline — work happens in the visible session, but consumes its context |
| **3. External subagent** | The orchestrator launches a **real, separate agent process** via shell — the **fork carrier** (same-family `qodercli` child through `.specify/skills/sdd-loop-driver/scripts/stage-runner.sh`) or the **subprocess carrier** (heterogeneous agent's own CLI child) | Full process & context isolation | True OS-level parallelism — **the only legal concurrency mechanism** | **Not automatic** — MUST follow the Visibility Contract below |

### Mode notes

- **Native is a single-delegation convenience, never a concurrency mechanism.** The **host-internal in-process subagent path is BANNED as a concurrency carrier** — neither a default nor a degradation option. In-process subagents share one process and one CPU core, so fan-out only fills one core; such a record MUST NOT be counted as the concurrency mechanism and MUST NOT be counted as satisfying the parallel-dispatch condition. A body that declares `N >= 2` units MUST use one of the two process carriers below.
- **Virtual** is a fallback for subagent-less tools. It preserves the *authoring* benefits of agent definitions (independent prompt/config, bounded brief) but none of the *runtime* benefits: no isolation, no parallelism, and the subagent's work consumes the session's own context window. Keep virtual subagent tasks small; virtual mode can never carry a concurrent dispatch.
- **External** is the concurrency mechanism, with exactly two legal carriers (owner of the judgement: `.specify/shared/declarations/facts/concurrency-class.yaml` class obligations and FR-035):
  - **Fork carrier (same-family default)** — each concurrent unit is a separate `qodercli` child process launched through `.specify/skills/sdd-loop-driver/scripts/stage-runner.sh`: prompt through stdin, output streamed with `--output-format stream-json`, completion judged by the stage sentinel. The process pool's upper bound is the host's `nproc` reading **at dispatch** — never a frozen constant; the requested concurrency still comes from the stage/run declaration.
  - **Subprocess carrier (heterogeneous agents)** — when a unit is executed by an agent CLI of a different family than `qodercli`, it MUST be carried by an independent child process of **that agent's own CLI**, judged by the same rule: separate process, per-unit dispatch/settle intervals, completion by sentinel or exit record. A family difference MUST NOT cause a fallback to host-internal fan-out.
  - Its cost: the child process is a black box unless the dispatch is wired for visibility — which is exactly what the contract below fixes.

## Mode Selection

Choose per dispatch, per member, by scenario — not by habit:

| Scenario | Recommended mode |
|----------|------------------|
| Interactive single-task delegation; runtime supports subagents | Native (single delegation only) |
| Executing tool lacks subagent support; lightweight sequential delegation | Virtual |
| Long-running task that must survive the foreground session | External (detached) |
| Parallel fan-out (team parallel dispatch, cross-repo analysts) | External process form — **fork carrier** for same-family agents, **subprocess carrier** for heterogeneous agents; never host-internal in-process fan-out |
| Team orchestration with stall detection / progress monitoring requirements | External with the Visibility Contract |
| Subagent must use a different model/config than the orchestrator and the runtime can't override per-dispatch | External (CLI flags: `--model`, `--reasoning-effort`, `--context-window`, …) |
| Orchestrator is itself a non-nesting subagent (its runtime exposes no native subagent tool) and the work needs fresh context | External (one process per worker, parallel) |

When in doubt: a **single** delegation may use native; **any multi-unit duty defaults to the external process form** — fork for same-family agents, subprocess for heterogeneous ones — with virtual as the sequential fallback for subagent-less tools. The host-internal in-process path is never a concurrency carrier, and a body that cannot obtain a process carrier records serial with a named reason code rather than claiming parallelism.

**Session-creation APIs are not a carrier.** Creating a host chat session/conversation — `create_chat_session`, `fork_chat_session`, or any equivalent — is NOT one of the three modes above. It materializes a user-visible conversation that inherits the orchestrator's model and permission mode, has no bounded task scope and no result contract, and leaves a permanent entry in the user's session list. Internal dispatch (detection/validation waves, team members, stage executors) MUST use one of the three modes and MUST NOT use a session-creation API; when the orchestrator cannot nest natively, the correct carrier is **External**, not a new session.

## Dispatch Capability (派发能力 — `"dispatch-capability"`, STR-004)

**Owner**: this section owns the definition behind the shared string `"dispatch-capability"` (STR-004 of Feature 093's shared-string table) — what *can create a sibling executor* means for a body's definition. The judgement that reads it is `.specify/scripts/python/concurrency-check.py`'s `capability` action, whose dispatch-tool spelling set is that engine's single executable form; the value read is the **existing** frontmatter key `capability-tools` — no new key is introduced (FR-022, C-038).

A body **can create a sibling executor** when its own definition satisfies one of the three forms FR-021 admits, judged from the definition alone (never a runtime probe):

| Form | Verdict | Reading |
|------|---------|---------|
| a dispatch-class tool is present in the definition's `capability-tools` list | `dispatch-capable` | the list itself |
| the body text explicitly hands dispatch to a capable superior (driver / main agent) and names the handoff's form | `handoff-declared` | the handoff sentence |
| the body declares one of § Three Execution Modes' two process carriers (fork for same-family `qodercli` children through `stage-runner.sh`, subprocess for heterogeneous agents) | `external-process` | the carrier declaration |
| none of the above | `incapable` | — a body declaring `N >= 2` units while `incapable` is `declaration-execution-mismatch`, judged red and never repaired silently (C-040) |

The three execution modes are § Three Execution Modes above (native / virtual / external); only the **external** mode's two process carriers are a concurrency mechanism (C-094). Gaining dispatch capability never changes the anti-nesting rule: the permitted chain stays **depth 2** with the three prohibitions stated in § Dispatch-Time Governance Obligation — a stage executor remains a leaf and never hosts or starts an SDD run (FR-025). This section adds no fourth form, no second predicate and no new frontmatter key.

## Execution Topology Declaration (执行拓扑声明)

An Agent Execution is parameterized by a **topology declaration** — the environment facts that turn an instance reference into a concrete run. Every element is entry-level; nothing here hardcodes a workspace naming rule, a host, or a user.

| Element | Local topology（本地） | Remote topology（远端） |
|---------|----------------|-----------------|
| Project directory | `<project-dir>` | `<project-dir>` (remote path) |
| Subagent CLI | `<cli>` (e.g. `qodercli`, `claude`) | `<cli>` |
| Login target | none (direct drive) | `<alias>` or host IP (`ssh`) |
| Run identity | current user | `<run-user>` (`su`/`sudo`, uid ≠ 0) |

**Dual input forms, equivalent（双形态等价）**: the declaration may arrive as (a) **inline parameters（内联参数）** given at call time, or (b) an **execution config file（执行配置文件）** in the project's agent-execution config store (schema owned by `.specify/skills/internal/create-agent/references/execution-config.md`). The two forms are interchangeable; when BOTH are given and any element disagrees, the dispatch MUST be **rejected at parse time with the conflicting fields listed**（拒收报错并列冲突字段 — fast-fail discipline; never a silent pick）. A missing/invalid referenced template fails fast the same way — no silent degradation to an inline substitute.

**Three configuration layers（三层配置）**: an execution config is merged from the defaults layer (`.specify/agents/execution/configs/_defaults.yaml`, seeded once by `specify init` from `.specify/templates/execution-config-defaults.yaml`), the agent config (`configs/<slug>.yaml`), and inline parameters, in that precedence order. The field-level schema, clear sentinels, and validation rules are owned by `.specify/skills/internal/create-agent/references/execution-config.md`; the runtime resolver is `.specify/scripts/python/execution-config.py`. This document references both and MUST NOT copy the field table or the CLI capability matrix (`CAPABILITY_MATRIX` in the engine is the sole owner).

**Coverage vs conflict（覆盖与冲突）**: `mode` and `cli` are topology identity; `model / reasoning_effort / context_window / extra_flags / log_dir` are overrides. An override covering a lower layer is normal layering; identity fields that disagree between agent config and inline parameters are a **conflict** and are rejected at parse time with the field named. A defaults-layer `cli` is a default value, not a declaration: selecting another CLI skips the whole defaults layer (recorded in `skipped_layers`) so no default may leak across CLIs.

**Config snapshot and quantification provenance（快照与量化来源）**: every successful resolve writes a snapshot under `.specify/agents/execution/logs/config-snapshots/` keyed by `config_id` (canonical-JSON hash); an external dispatch's record references it through `collect-dispatch` (`.specify/scripts/python/exec-quant.py`), carrying the effective configuration plus `method_requested` vs `method_resolved`. Snapshot integrity (the id recomputed from `snapshot.effective` equal to both the snapshot's `config_id` and the caller's `--config-id`) is checked at collection time.

**Division of labor (unchanged)**: this section owns *what must be declared*; `../workflow/external-dispatch-recipes.md` owns *how the declaration is executed* (concrete command shapes). When they disagree, this contract wins（分歧时契约赢）.

## External Dispatch Visibility Contract

**The silent anti-pattern** (observed in real team runs):

```bash
qodercli -p "<prompt>" > agent.log 2>&1 &   # PROHIBITED
```

Print mode (`-p`) buffers **all** output until process exit. The log file stays at 0 bytes for the entire run — the orchestrator and the user see nothing: no progress, no stall signal, no debugging surface. A dispatch you cannot observe is a dispatch you cannot operate.

Every external subagent dispatch MUST therefore:

1. **Stream events** — run the CLI with `--output-format stream-json` (NDJSON, one event per line; supported by both `qodercli` and `claude`).
2. **Compact the stream** — pipe events through a filter that renders one short line per meaningful event (tool calls with key argument, assistant text excerpts, final `DONE` summary with turns/cost/duration).
3. **Emit the artifact triplet** per dispatched agent:
   - `<label>.live.log` — compact progress lines; tailable and monitorable in real time
   - `<label>.jsonl` — raw stream-json events, kept for forensics
   - `<label>.status` — `<label> exit=<code>` recorded at completion
4. **Monitor liveness** — watch `.live.log` growth (bytes/lines); stalled growth beyond the team's stall threshold means a stalled agent, triggering the team's recovery protocol (wait / nudge / terminate / reassign).
5. **Trace the session** — none of the supported agent CLIs exposes an official session-naming/rename mechanism (verified against each tool's official documentation surface; sessions carry auto-generated IDs only). Traceability therefore rides a convention, not a CLI flag:
   - give every dispatch a stable **label** (`<team-slug>--<run-stamp>--<member-role>`) that names the triplet files, and open the dispatched prompt with that label as a prefix line so the session's own transcript is self-identifying;
   - record the dispatch mapping (label → CLI → member → workspace) in the run report — the mapping table, not a renamed session, is the canonical cross-reference surface.

**Reference implementation**: `.specify/skills/internal/create-team/scripts/dispatch.sh` (+ `stream-filter.py`) — a generic, CLI-agnostic wrapper implementing the four observability points above (works with `qodercli` and `claude`; override via `DISPATCH_CLI`; the label convention of point 5 is the caller's responsibility). Team runbooks and command workflows SHOULD reuse it instead of re-rolling per-run dispatch scripts.

**Topology recipes**: for the concrete command shapes of driving an external subagent — remote `ssh + su` into a host, stage prompt files, runner derivation, background execution with log polling, and the local direct-drive variant — see [`../workflow/external-dispatch-recipes.md`](../workflow/external-dispatch-recipes.md). This document owns the contract; that document owns the recipes; when they disagree, the contract wins.

## Dispatch-Time Governance Obligation

The Visibility Contract above owns whether a dispatch is **observable**. This section owns whether it is **governed** — the two are complementary and neither substitutes for the other. A dispatch you can watch but not triage still runs an ungoverned agent; a dispatch you can triage but not watch still hides a stall.

Every dispatch MUST carry the fast-fail injection clause, because a subagent's prompt derives from its own definition and dispatch payload rather than from the orchestrator's conversation, so no standing instruction layer reaches it. The clause's owner literal, its three channels, the pre-dispatch probe, the anomaly return line, and the rule that an anomaly halt is not an ordinary failure are all defined once in `.specify/shared/guidelines/fast-fail.md` § 子代理派发注入; this section MUST reference it and MUST NOT restate it.

Every dispatch that serves an in-scope flow MUST also carry the **reporting duty** — the same payload channel, a different obligation, defined once in [`reporting-obligations.md`](../guidelines/reporting-obligations.md).

**Anti-nesting obligation (反嵌套)**: the dispatching prompt MUST NOT reference any driver/loop skill (e.g. `sdd-loop-driver`), MUST NOT instruct the subagent to load any skill, and MUST NOT contain loop logic — the loader of a driver manual is the driver; a subagent that receives the manual becomes a second driver and the hierarchy escapes.

**Concurrency obligations travel with the dispatch (C-076/C-077)**: every dispatched sub-agent's brief MUST carry the concurrency obligation as brief content — the three parts of § The Concurrency Obligation, or an explicit pointer to that section — injected at dispatch rather than inherited from an ambient layer. Every sub-agent **return** MUST carry its own `requested` / `effective` / `effective_reason` triple; a return without it is `report-incomplete` and MUST be reported by the coordinator, never filled in by the coordinator. A coordinator that plans parallel packages MUST emit the packages (each naming its scope, inputs and output path) before dispatching and MUST state the execution shape actually achieved — including a serial shape: "partition ready, execution serial" is a named disclosure with its reason code, never a silence (C-059, C-073, C-074).

**The narrowed predicate（收窄后的可判定谓词）**: a dispatch prompt may name or assign an SDD driver **only** when all three of the following conditions hold: (1) the recipient resolves to an Agent definition declaring the capability key `sdd-invocation` ([[STR-001]]) as `allowed` ([[STR-002]]); (2) the recipient's seat policy declares the same key as `allowed`, resolved by `(team, seat)` from the roster; (3) the assigned task is an **SDD assignment** — a member duty whose routing decision has been recorded with the `sdd` verdict (`"sdd"`). The verdict vocabulary and the recorded-decision requirement behind condition (3) are owned by [`sdd-routing-definitions.md`](sdd-routing-definitions.md), which also registers the `[[STR-NNN]]` literals cited here; a duty whose decision is absent, `direct` (`"direct"`), or `adjudicate` (`"adjudicate"`) is not an SDD assignment.

Every dispatch that does not satisfy all three conditions keeps the prohibition above word for word: the narrowing adds one allowance and removes no prohibition from any path that fails it, and the predicate is stated here once — no second copy of it is created elsewhere. The operational enforcement lives in `.specify/skills/internal/run-agent/SKILL.md` dispatch governance (pre-dispatch probe extended to this obligation); the ruling's provenance is the sdd-loop-driver Driver Topology defect fix (2026-10-16).

**Permitted chain（许可链，深度 2）**: the permitted nesting chain is depth 2: team orchestrator → invoking member (driver host) → stage executor (leaf). This chain replaces the unqualified depth-1 claim that used to stand here, because an unconditioned rule and a narrowed predicate cannot both hold. Three prohibitions bind at every depth: a stage executor MUST NOT start or host any SDD run; an SDD stage executor MUST NOT itself be an SDD invocation host; SDD-within-SDD recursion is prohibited. A stage executor is a leaf — never a driver host.

**Virtual mode cannot host（virtual 模态不得承载）**: a member executed in virtual mode MUST NOT host an SDD run. Virtual execution occupies the orchestrating session, so hosting a driver inside it collapses the outer layer into the driver; the dispatch is refused before it leaves and the reason is reported. This does not exempt virtual mode from the obligation above — it removes the hosting allowance from it.

**One run per member（硬上限）**: a member hosts at most one SDD run at a time — a hard cap with no escape: no higher per-member cap is declarable and no team-level override exists. A second duty that would need a concurrent run on the same member is serialized or rejected by the existing line registry and worktree-per-write-line ownership mechanism, which also settles overlapping territories between two authorized seats; no second concurrency primitive is introduced, and the decision cites that mechanism rather than inventing a gate.

**Refusal record（拒绝记录）**: a refused dispatch produces a record naming the failed condition and the recipient's resolved values, plus both source paths and the seat slug, so the verdict is recheckable without re-deriving it. A record that states only "not authorized" is non-conforming: the two halves exist precisely so a reader can tell a policy decision from a missing declaration. The record lands in the authorization probe record of `sdd-route.py --action authorize` and is carried into the team run report written under the existing `create-team` report contract; neither carrier is a new store.

**Enforcement precedes dispatch（先判后派发）**: the narrowing is enforced before dispatch — a prompt naming or assigning a driver without all three conditions is not dispatched, a stage executor cannot start or host a run, and the pre-existing prohibition stands unchanged on every path that fails the three conditions. **No new machinery（零新增机制）**: the authorization surface adds no additional user-confirmation step, no scheduler, and no second registry; its only stored state is the two declared values (the Agent definition's capability and the seat policy), and everything else — the duty's recorded decision, the execution mode, the chain position — is read at probe time from the definition, the roster, and the line registry.

The obligation binds all three execution modes (native / virtual / external) equally, and virtual mode is not exempt merely because the session itself holds a standing instruction layer. It is a **caller-side content** duty, deliberately NOT implemented in the reference wrapper below: a discipline that depends on one execution path can be bypassed by choosing another, so the wrapper stays generic and unchanged.

## Terminology Boundaries

| Term | Meaning | Where defined |
|------|---------|---------------|
| **Agent Template / Instance / Execution** | The three-layer Agent taxonomy; a subagent is the Execution layer | `.specify/shared/definitions/agent-definitions.md` |
| **Agent Instance** (a.k.a. agent definition) | Responsibility-bound `.agent.md` (under `.specify/agents/instances/`) a subagent is launched from | `agent-definitions.md`; authored via `/speckit.agents`, `skills/internal/create-agent` |
| **Subagent** (this document) | A running, task-scoped delegated Agent Execution | here |
| **Team** | Multi-agent structure orchestrating several subagents | `/speckit.team`, `skills/internal/create-team` |
| **Tool** | Pre-verified reusable capability record (`.specify/memory/tools/`) | `.specify/shared/definitions/tool-definitions.md` |
| **AI agent CLI** | A supported coding agent binary (`qodercli`, `claude`, …) | `docs/reference/cli/` |
