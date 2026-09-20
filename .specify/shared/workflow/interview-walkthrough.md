# Interview-Driven Requirements Walkthrough (访谈式需求走查)

This document is the authoritative detailed reference for the Requirements Analyst's **interview mode**. The agent definition (`.specify/agents/templates/requirements-analyst.agent.md`) declares the mode and its phases; everything here is the operational detail.

**Relationship to the generic pattern**: this is the **requirements-domain instance** of [`shared/patterns/interview-pattern.md`](../patterns/interview-pattern.md), which owns the generic semantics — design tree, frontier, rounds, question format, fact-vs-decision split, write-through, and the user-confirmation exit gate. Read the pattern for those; read this document for what the requirements domain adds on top: interview units, decision cards, verification levels, and delivery-loop coupling. Where the two speak to the same rule, the pattern is the authority.

Use it when requirement details live in the stakeholder's head rather than in a written document. Do not ask the user to "write a spec" — decompose the requirement into interview units, show the user the real artifact for each unit, ask open questions, and land every decision on the spot. A full walkthrough can span dozens of units and multiple days; the walkthrough ledger file is the durable state that makes this possible.

Field-proven: the rules in this document encode lessons from a proven multi-day, contract-driven walkthrough (dozens of units) — see [Lessons & Calibration](#lessons--calibration-经验校准) below.

## Mode Selection

- **Document mode** (user already provides a written requirement): follow the classic flow — Receive → Analyze → Clarify → Translate → Structure → Validate.
- **Interview mode** (requirement is scattered, tacit, or "in the user's head"; or the user asks to "walk through" something): follow the phases below.
- **Human-in-the-loop constraint**: interview mode requires a live stakeholder answering per unit. Run it in an interactive session; when invoked as a fire-and-forget subagent, process only the requested batch of units against the durable ledger and return — never fabricate answers for units the stakeholder has not seen.
- **Loop coupling** (choose one at Phase 0 and record it in the ledger header):
  - **Record-only**: decisions land in the requirement doc; implementation is a downstream batch handoff.
  - **Delivery-loop** (即谈即做, the high-trust mode): each unit's decisions are handed to the implementing roles immediately, and the ledger row is only marked ✅ after the downstream gate at the unit's committed verification level passes. Never let decisions from multiple units pile up unimplemented — same-day decision→verified-code is what builds stakeholder trust and decision quality.

## Phase 0 — One-time Setup (默认约定先行)

1. **Decompose** the requirement into interview units (pages / modules / scenarios / user stories) and enumerate them into a **walkthrough ledger** — one row per unit, no omissions.
2. **Declare conventions once** at the top of the ledger: interview granularity, how decisions are recorded, decision-card taxonomy, loop coupling, and the done-criteria for a unit — so they are not renegotiated per unit.
3. **Pre-scan gaps**: diff what already exists (docs / code / contracts) against the stated goal, and carry the gap list into interviews so each unit's known issues are confirmed on the spot instead of surfacing at the end.
4. **Initialize the ledger as a durable file** (e.g., `.specify/specs/<feature>/walkthrough-log.md`) — see the template below. It is the single source of walkthrough state across sessions.
5. **Environment readiness & baseline**: verify the artifact environment is reachable (e.g., dev server up, generated contract/client present) and snapshot the baseline (branch, contract version, generated-artifact fingerprint) so drift can be detected per unit.
6. **Resumability**: on every (re)invocation, if the ledger exists, read its header conventions (never renegotiate them) and resume from the first non-✅/⏭ row. Multi-day, multi-batch walkthroughs are the norm, not the exception.

## Per-unit Loop (单元三阶段循环)

One unit at a time. Never batch two units into one interview.

### Stage 1 — Interview (访谈)

- **Show the real artifact**: open the real running page via browser-utils (screenshot/snapshot), or present the actual file / diagram / data — let the user "look at it while deciding" instead of describing from memory.
- **Open main question first**: "What changes does this unit need?" — then targeted follow-ups on specific elements (navigation, controls, fields, flows). Never preset the answer space.
- **Strict granularity**: discuss only the currently open unit; if the user drifts to another unit, note it in that unit's ledger row and return.
- **Drift check first**: before showing the artifact, verify the environment baseline has not drifted (branch switched, generated artifacts reset by an external process, dependency rolled back). If drifted: restore first, record the incident as a follow-up with a root-cause owner, then interview — never interview against a corrupted artifact.

### Stage 2 — Record (即时落库)

- Write each decision explicitly as **「用户决策：…」** into that unit's requirement section, **overwriting** the stale content so only the latest round survives (覆写式落库).
- Classify the decision with a **decision card** plus free-text supplement, and update the ledger row's structured columns (status, time, decision card, contract change, verification level, summary) — structured columns, not free text only, so residuals can be counted and queried at closing.

### Stage 3 — Derive (即谈即做)

- Immediately translate the decisions into numbered functional requirements + acceptance scenarios for that unit — never let interview conclusions pile up unprocessed.
- **Assign a verification level** to the unit and record it in the ledger (see below). A downgraded level (e.g., backend not ready → L1 only) must be an explicit stakeholder decision recorded in the row, never a silent default.
- **Delivery-loop handoff** (when loop coupling = delivery-loop): hand this unit's decisions to the implementing roles now (see Delivery-loop Coordination below), and mark the row ✅ only after the committed verification level passes. In record-only mode, mark ✅ when requirements are derived and traceable.
- If the unit reveals an upstream gap (missing contract, undecided dependency, backend not ready), record it as an explicit follow-up item with an owner, mark the unit `To Do` where needed, and keep the walkthrough moving.
- **Contract-gap items are structured**: an `Extend` decision must yield `{endpoints, schemas, branch/ledger location, owner}` so the downstream role can act without re-interviewing. **Landing cadence**: prompt the owner to land (push/merge) accumulated contract gaps every 2–3 items — a long local accumulation window is where external interference strikes.
- **Scope escape hatch**: if one unit balloons into a cross-unit redesign, do not break the granularity convention — split it out as an independent spec item (its own spec → plan → implement track) and record the split in the ledger.

## Decision Cards (访谈决策模板)

Open questioning naturally converges to these decision types; use them to reduce recording ambiguity, never to constrain the user:

| Card | Meaning |
|------|---------|
| **Keep** (保持现状) | No change now; optionally mark a future To Do |
| **Adopt** (立即接入) | Wire up the real capability/data now |
| **Extend** (补充再接入) | Upstream contract/dependency has a gap — fill it first, then adopt; must yield a structured contract-gap item `{endpoints, schemas, branch/ledger location, owner}` |
| **Remove** (裁剪) | Delete for now; re-add later if needed (DoD includes cleaning the call chain: pages, services, hooks, routes) |
| **Redesign** (重新设计) | Rework against a reference design; may rename/move |
| **Align-baseline** (对齐基准) | Conform strictly to an authoritative data/contract baseline; remove invented fields |

## Verification Levels (验证分级)

| Level | Gate | When sufficient |
|-------|------|-----------------|
| **L1 compile** | Build/type gate passes (e.g., `tsc --noEmit`, dev compile) | Skeleton work, backend-not-ready units |
| **L2 contract** | Mock/contract replay against the spec (e.g., Prism) passes | Contract-first units without live backends |
| **L3 e2e** | Real data end-to-end verified in the running artifact | Default for adopted real-capability units |

## Delivery-loop Coordination (同回路多角色协同)

The Requirements Analyst chairs the walkthrough ledger; implementing roles close the loop per unit:

| Decision card | Hand to | Gate owner | Row ✅ when |
|---------------|---------|------------|-------------|
| Extend | System Designer (contract design) → Module Designer (code + contract ledger) | Test Engineer / QA | committed level passes |
| Adopt / Align-baseline | Module Designer | Test Engineer / QA | committed level passes |
| Redesign | split as independent spec item (escape hatch) | per that item's track | split recorded |
| Keep / Remove | Module Designer (call-chain cleanup for Remove) | Test Engineer / QA | cleanup compiles |

Rule: the stakeholder's spoken decision becomes verified code the same day, or the unit carries an explicit `To Do` with an owner. There is no third state.

## Closing (收尾)

1. **Sweep scan**: after all units are ✅/⏭, scan for anything the walkthrough could not cover (legacy debt, orphan references, mismatches) and classify residuals as actionable vs. needs-confirmation — expose them as next-iteration input instead of leaving them silent.
2. **Artifact freshness check**: before final ✅ on the walkthrough, verify recorded artifacts (screenshots, snapshots, examples embedded in unit docs) reflect the post-decision state; refresh any that lag behind.
3. **Aggregate cross-cutting findings**: requirements and improvement suggestions that span units are summarized separately from per-unit decisions.
4. **Validate & hand off**: check every requirement is independently testable and traceable to a「用户决策」entry, list remaining Open Questions (max 3), and hand the structured document to the System Designer.

## Ledger Template (台账模板)

Header (conventions, declared once):

```markdown
# Walkthrough Ledger: <feature>

- **Started**: <date>
- **Units**: <N> (<breakdown>)
- **Granularity**: one unit per interview; drift notes go to the drifted-to unit's row
- **Loop coupling**: record-only | delivery-loop
- **Recording**: 「用户决策：…」overwrite style in each unit doc; latest round only
- **Done criteria**: row ✅ requires <recorded & traceable | gate at committed verification level passed>
- **Environment baseline**: <branch / contract version / artifact fingerprint>
- **Status legend**: ⬜ pending / 🔄 in progress / ✅ done / ⏭ skipped
```

Rows (structured columns — no free-text-only summaries):

```markdown
| # | Unit | Ref | Status | Time | Card | Contract change | Level | Summary |
|---|------|-----|--------|------|------|-----------------|-------|---------|
| 1 | <unit> | <doc/route/file> | ⬜ | | | | | |
```

## Unit Document Template (单元文档模板)

Per-unit requirement document (one file per unit), frontmatter + decision/rewrite sections:

```markdown
---
title: <unit name>
ref: <route / module / scenario id>
status: pending | interviewed | implemented
services: [<service refs>]      # filled at derive/handoff
apis: [<contract endpoints>]    # filled at derive/handoff
---

# <Unit Name>

![artifact](<screenshot or snapshot path>)   # refreshed at closing

## 页面定义与数据映射 / Unit Definition & Data Mapping
用户决策（<date>）：<latest decision summary>

| Element | Source | Service / Endpoint | Notes |
|---------|--------|--------------------|-------|

## 重构需求 / Requirements (overwrite style — latest round only)
- <decision-derived requirements, FR-nnn traceable>
```

## Long-Walkthrough Operations (长走查运维)

- **Checkpoint & resume**: the ledger file is the state. End every session with the ledger fully written (no in-memory-only progress); start every session by re-reading it.
- **Batching**: when turns or time run out, stop at a unit boundary — never mid-unit. A unit mid-interview stays 🔄 with its partial decisions already written to the unit doc.
- **No fabrication**: units the stakeholder has not seen stay ⬜. Skipping ahead and guessing decisions is the one unrecoverable failure mode.
- **Incident ledger**: environment drift, external interference, and broken gates are recorded as follow-ups with owners, not silently absorbed.

## Lessons & Calibration (经验校准)

Distilled from a proven multi-day, contract-driven walkthrough spanning dozens of units. Use these to calibrate expectations and to recognize incidents when they recur.

### Decision-Card Distribution (typical)

- **Extend** (contract gaps) is usually the most common card in contract-driven walkthroughs — expect the contract-gap pipeline to be the busiest track.
- **Adopt** and **Keep** are the steady-state cards; for **Remove**, enforce the call-chain cleanup DoD at decision time, not at closing.
- **Redesign** is rare but dangerous: watch for cross-unit scope creep and trigger the escape hatch early rather than bending the granularity convention.

### Incident Types → Rules

| Incident type | Rule it maps to |
|---------------|-----------------|
| External process resets generated artifacts mid-walkthrough | Phase 0 baseline snapshot + per-unit drift check first; incidents recorded with a root-cause owner |
| Contract-gap commits accumulate locally for days | Landing cadence: land every 2–3 contract-gap items |
| Backend not ready for a unit | Verification levels: explicit downgrade as a recorded stakeholder decision, unit carries To Do |
| One unit balloons into a cross-unit redesign | Scope escape hatch: split as an independent spec item |
| Hand-written calls pointing at non-existent endpoints | Pre-scan gaps in Phase 0, not only the closing sweep |
| Schemas drifted from the real data baseline | Align-baseline card: the authoritative baseline wins; remove invented fields |

### Transferable Takeaways

1. Interviewing **against the real running artifact** is faster and higher-fidelity than asking users to write requirements from memory.
2. One-unit granularity + open main question + overwrite-style recording keeps a long walkthrough focused, unstacked, and auditable.
3. Interview → implement → verify in the **same loop** turns spoken decisions into verified code the same day — this is the primary trust driver.
4. A single source of truth (contract) + atomic commits + ledger bookkeeping makes cross-repo collaboration auditable.
5. The closing **sweep scan** converts historical debt the walkthrough cannot reach into explicit next-iteration input instead of silent residue.
