# Super Agent Definitions Reference

This file is the **single owner** of the **super agent** concept — the parent-side **relative** logical role that a dispatch edge assigns to its two endpoints. It owns the role definition and its set semantics, the edge predicate and its four closed violation kinds, role depth, the super↔sub protocol, the closed `role-transition` injection, the state-sync/recovery mapping, the visualization mapping, the zero-second-mechanism boundary, and the terminology boundary. Every other surface reaches this page by pointer: `agent-definitions.md`, `subagent-definitions.md` and `framework-map.md` carry one pointer line / row each, and the dispatch and digest surfaces reference the model without restating it. The role acts on the existing three-layer Agent taxonomy owned by `agent-definitions.md` and adds no fourth layer, no entity type and no runtime.

## The Relative Role (相对角色)

A **role** is decided only by a dispatch edge. A directed edge `P → C` exists if and only if one dispatch by `P` produced one execution of `C`; one dispatch produces exactly one edge. On that edge `P` is the **super agent** — machine identifier `superagent` — and `C` is the **subagent** — machine identifier `subagent`. The classification MUST NOT be derived from executor type, model, tool list, prompt wording or a self-description; a face that classifies roles by entity type is defective.

Roles form a **set** on each executor, not a single label. An executor that parents at least one edge is a super agent; an executor that is a child on at least one edge is a subagent; an executor holding both members is a **dual-role** executor (双重角色) and stays fully a subagent on its parent edge. The machine marker `dual-role` appears only in role-set **output** (the judgement face's `role_set_marker` key): it is never a third role value, never a member of the role set, and never a carrier declaration value.

Carrier declarations use exactly the two role values `subagent` / `superagent`. The **dispatch-duty grant** is a separate declaration: a `dispatch_duty` field taking `granted` / `not-granted`. A grant is not a role claim and a role claim is not a grant; granted-but-not-yet-dispatched is legal.

The executor that directly holds the user session is a **root**: depth 0, and never a subagent.

## Role Edges (角色边)

An edge record has record kind `role-edge`. It is a **projection over existing carriers** — never a new store — with these fields: parent identity, child identity, dispatch-attempt identifier, the declared role for this edge, the independent dispatch-duty grant, the computed depth, the primary carrier source, and any conflict rows.

Identity resolves to existing labels: the child is the existing dispatch label (team / dispatch convention, `run-agent` label, or driver stage `<line_id>-<stage>`); the parent is its own dispatch label, and a root uses its existing run identity — status-spine `run_id`, else line-registry `line_id`, else the owner-declared root literal `root`. Parent-side dispatch records are the **primary carrier**: team run-report dispatch mapping tables, the driver's status spine line + stage, and the `run-agent` label; artifact triplets, status spines, the line registry and run reports cross-check only.

One dispatch produces exactly one edge, and one retry is a new attempt with a new label (old attempt artifacts are kept, never overwritten). When the same field of one edge disagrees between two carriers, the judgement face emits a `conflicts` row naming the field, **both paths** and the edge identity (`parent` / `child` / `attempt`) — never a silent pick.

The judgement face is the deterministic, read-only engine `.specify/scripts/python/role-edge-check.py`; its actions, exit codes and output schema are owned by the engine itself and pinned by `tests/contract/test_role_edge_engine.py`. The violation set is **closed at four kinds**:

| Kind | Predicate |
|------|-----------|
| `self-dispatch` | the resolved parent equals the resolved child |
| `dangling-parent` | the parent identity cannot be resolved from the existing records |
| `unbacked-role-claim` | an explicit recorded `superagent` role assertion (a carrier's declared-role field taking `superagent`) while the judgement finds no edge where that executor is the parent. A `dispatch_duty: granted` declaration is not a role claim and never triggers this kind; `dual-role` appears in no carrier |
| `depth-inconsistent` | a recorded `depth_position` disagrees with the computed depth, or a cycle makes depth unresolvable |

A fifth kind MUST NOT be emitted before this page is revised.

## Role Depth (角色深度)

The root's depth is 0; an executor's depth is the shortest edge distance from a root, computed from the recorded edges and recheckable against the dispatch records. Role depth is unbounded — it describes the graph, and it is not an authorization rule.

Role depth is unbounded and descriptive; the SDD license-chain depth 2 is an authorization limit owned by `subagent-definitions.md` § Dispatch-Time Governance Obligation — the two axes are orthogonal and neither rewrites the other.

When an executor enters the SDD carrying chain, the three conditions, the three prohibitions, the virtual-cannot-host rule and the one-run-per-member cap apply unchanged, by pointer to the owner named above. A non-SDD fan-out consumes no license-chain depth, and this page MUST NOT be read as a second authorization rule.

## The super↔sub Protocol (super↔sub 协议)

**Downlink.** Every governed dispatch carries seven role fields in its existing payload channel: `parent_identity`, `child_label`, `role_declaration`, `dispatch_duty`, `depth_position`, `authority_ref`, `return_channel`. The four pre-existing injections keep their owners and travel by pointer: the fast-fail clause (`.specify/shared/guidelines/fast-fail.md` § 子代理派发注入), the concurrency obligation (`subagent-definitions.md` § The Concurrency Obligation), the reporting duty (`.specify/shared/guidelines/reporting-obligations.md`), and the re-anchoring anchor digest (`.specify/shared/definitions/re-anchoring-definitions.md`). The payload MUST NOT instruct the child to load any skill, MUST NOT reference a driver skill, and MUST NOT contain loop logic — the anti-nesting owner is `subagent-definitions.md` § Dispatch-Time Governance Obligation.

**Uplink.** Every return carries the result or deliverable path, evidence pointer(s), an explicit anomaly line (stating "no anomaly" explicitly when none), the concurrency reading triple with its fields owned by `subagent-definitions.md` § The Concurrency Obligation, and the returning executor's identity. Missing any item makes the return incomplete: the parent MUST NOT consume the conclusion and MUST NOT backfill the missing fields.

**Message classes.** Edge messages are classified into one closed set of four tokens: `ack`, `answer`, `result`, `attention-escalation`. Unclassified progress MUST NOT travel up an edge; an executor's activity stays visible through the existing liveness carriers (artifact triplet and `watch-model.md`). This model adds no attention mechanism, channel or notification service.

**Waiting.** Waiting is bounded and observable through the existing watch model (`watch-model.md`); a human abort or redirect stays servable; slow versus stalled uses the existing thresholds.

**Attempts.** Each retry is a new dispatch attempt with a new label. The old attempt's artifacts are kept; a stale attempt's return is identified by the existing attribution values owned by `watch-model.md` § 11 and MUST NOT be consumed as the current result.

**Authorization.** What an edge may do is decided only by `sdd-route.py --action authorize` together with the recorded routing verdict and the team territory; message content never widens permission; a refusal produces the existing named refusal record; resume or retry re-validates before acting.

**Termination.** Edge end (`completed` / `failed` / `cancelled`) is written into the edge's existing carrier, so the parent can judge it; silent orphaning is a defect. Cancel and terminate follow the existing confirmation gates — no new gate.

## Role-Transition Injection (身份转变注入)

When a subagent is granted dispatch duty, its dispatch payload MUST physically carry the `role-transition` injection (身份转变注入): the stable identifier plus the nine pointer items below. Physical presence is mandatory because a standing instruction layer does not reach a child executor.

| # | Item id | Points at |
|---|---------|-----------|
| a | `role-activation-scope` | the superagent role activation and the dispatchable scope on this edge |
| b | `self-identity-parent-edge` | the executor's own identity and its parent edge |
| c | `downward-obligation-checklist` | the obligations it must inject into each of its own dispatches, by pointer |
| d | `concurrency-budget-ref` | the available concurrency budget and the existing slot/reserve facts, by pointer to their owners |
| e | `reporting-path` | the reporting path and the reporter / master-subordinate reporting duty, by pointer |
| f | `state-carriers-writer-boundary` | the existing state carriers it reads and writes and the writer boundary, including the visibility contract by pointer |
| g | `attention-classes-escalation` | the message classes above and the escalation rules, with the reporting owner by pointer |
| h | `depth-remaining-prohibitions` | remaining depth and the prohibitions that still bind it, by pointer to their owners |
| i | `aggregate-return-contract` | the aggregate return contract |

The list is closed — adding or removing an item is a contract change. Each item is carried as a pointer, never as rule text. The existing pre-dispatch self-check (`.specify/shared/guidelines/fast-fail.md` § 派发前自检) requires the `role-transition` identifier and each item-id slug; a missing identifier or slug is a payload-construction defect and is blocked before dispatch. The check form and its landing are existing — only the judged identifier is new.

The payload red lines are owned by `subagent-definitions.md` § Dispatch-Time Governance Obligation and referenced here: no full driver manual, no skill-load instruction, no driver-skill reference, no loop logic.

A dual-role executor keeps every upload duty of a subagent — gaining the superagent role reduces none of them. It returns **one** structured result to its parent: per-child attribution, per-child evidence paths, failures and anomalies surfaced; the aggregate does not replace the child evidence, and the parent can drill down.

## State Synchronization & Recovery (状态同步与恢复)

Edge state has a single writer per fact: the parent owns the edge record and the aggregate state; the child owns its own latest state (the artifact triplet's `.status` and its return). The parent records the edge and the received returns before its next externally visible action. No shared mutable aggregate is maintained; edge records land per entry, following the framework's Concurrent Development Safety discipline.

The parent derives child state only from the three existing fact layers:

| Layer | Carrier | Used for |
|-------|---------|----------|
| State layer | status spine / line-registry entry | identity, run / line ids, stage verdicts |
| Assignment layer | artifact triplet `.status`, return record, run report | edge state, attempt, result presence |
| Host-event layer | watch model pid / heartbeat / liveness | liveness, stale marking, interrupted / attention |

The parent MUST NOT derive state from conversation memory, child-session transcripts or process scans.

Recovery rebuilds the edges from those three layers and reports the real state: a child still judged to be running is marked `interrupted` / `attention`, never silently `running` or `completed`. Resume and re-entry re-validate authorization before acting, do not replay old messages, and do not re-dispatch completed children; an unverifiable resume stops with a named failure.

## Visualization & Tracking (状态跟踪与可视化)

`.specify/scripts/python/status-digest.py` remains the **only** digest renderer. Its role view adds `parent`, `roles`, `role_set_marker` (passed through from the judgement model, never re-derived) and `depth` beside the existing identity, state, recent activity, age and stale fields, in both the table and JSON outputs. The role model is computed once per digest run through the engine's importable interface, so the legacy line view and the role view share one carrier materialization. `nothing-running`, the omitted-count declaration on truncation and stale marking keep their existing semantics.

A fan-out of one parent to N children renders in the same digest read: the parent row plus one row per child. No dashboard, second parser or second renderer is introduced; liveness stays on the artifact triplets, and the dispatch mapping tables in team and driver run reports carry `label → role → dispatch_duty → workspace → parent` by pointer to their report-contract owners.

## Zero Second Mechanism (零第二机制)

This model adds no persistence root, registry, second renderer, dispatcher, scheduler, queue, transport or notification channel. Edge records are projections over the existing carriers named in § Role Edges; the role view is an extension of the existing digest, not a second visualization.

The judgement face is read-only: `.specify/scripts/python/role-edge-check.py` has zero write points, answers `--help` / `--version`, and rejects undeclared options before reading — the script interface contract is owned by `.specify/shared/definitions/script-interface-definitions.md`.

Owner rules are not copied here and keep their owners: concurrency (`subagent-definitions.md` § The Concurrency Obligation and the concurrency facts under `.specify/shared/declarations/facts/`), reporting (`.specify/shared/guidelines/reporting-obligations.md`), authorization (`sdd-route.py`), waiting and attribution (`watch-model.md`), the SDD dispatch-time governance and the anti-nesting red lines (`subagent-definitions.md` § Dispatch-Time Governance Obligation), the fast-fail injection (`.specify/shared/guidelines/fast-fail.md`), and the re-anchoring obligation (`.specify/shared/definitions/re-anchoring-definitions.md`).

Gaining the superagent role grants no new capacity: slots and reserves stay with the existing concurrency facts, and nesting does not amplify them. Suppressing unclassified progress inside an edge never reduces the human-facing reporting duty, which stays with its owner.

## Terminology Boundaries (术语边界)

| Term | Meaning | Where defined |
|------|---------|---------------|
| **super agent** | The parent-side relative logical role on a dispatch edge; prose form (two words) | here |
| **superagent** | The machine identifier of that role, used in carrier declarations and judgement output | here |
| **super-agent** | Glossary alias only; framework prose does not use it | `.specify/glossary.md` `Super Agent` entry |
| **subagent** | The child-side relative logical role; its execution modes, visibility contract and governance stay with the child-side owner | `.specify/shared/definitions/subagent-definitions.md` |
| **dual-role** | The output-only marker of the both-roles set state (`role_set_marker`); never a third role value and never a carrier declaration value | here |
| **role edge** | One dispatch's directed parent → child relation, record kind `role-edge` | here |
| **role-transition** | The stable identifier of the injection a dispatch-duty grant carries | here |

The role is **not a fourth layer**: it acts on the three-layer Agent taxonomy owned by `.specify/shared/definitions/agent-definitions.md`, and this page MUST NOT be read as a new entity type, a new Agent category or a new owner for subagent behaviour. The parent-side role is owned here; the child side stays with `subagent-definitions.md`.
