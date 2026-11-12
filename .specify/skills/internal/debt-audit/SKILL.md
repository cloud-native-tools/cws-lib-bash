---
name: debt-audit
description: Inventory a project's technical debt with project and history context and design its phased governance plan — partition the scope into disjoint read domains, dispatch one bounded SDD Debt Governor execution per domain through the dispatch carrier, verify evidence, and synthesize a debt register plus a mechanism-first cleanup plan with explicit adjudication points. Read-only: reclamation and repairs are routed to /speckit.sanitize and the SDD flow, never executed here. Use when the user mentions ["debt audit", "tech debt", "technical debt", "技术债务", "债务盘点", "技术债", "债务清单", "清理方案", "debt register", "governance plan", "debt-audit"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/debt-audit/SKILL.md>"
---

# debt-audit

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.

## Goal

Produce the technical-debt inventory and governance plan for a project scope. The **executor of every audit unit is the `sdd-debt-governor` agent template** (`agents/sdd-debt-governor.agent.md`, runtime face `.specify/agents/templates/sdd-debt-governor.agent.md`) — this skill is the harness binding: it owns the workflow (scope, partition, dispatch, verification, synthesis, adjudication), and every finding, severity and disposition is produced by that agent, never re-derived here.

This skill never executes cleanup: data reclamation is `/speckit.sanitize`, mechanism repairs are SDD runs. Its single deliverable is the register + plan.

## Input Contract

- **Scope**: the directory set named by `$ARGUMENTS`, else the framework-owned surfaces under `.specify/` (runtime state, specs, .specify/memory/history, .specify/scripts/templates, skills/agents/teams, root anchors).
- **Output**: the report directory named by `$ARGUMENTS`, else `.specify/studies/debt-audit-<YYYY-MM-DD>/` (`report.md` plus one `d-<n>-<domain>.md` per domain).
- **Reuse baseline**: an optional previous register; every reused finding MUST be re-verified and re-classified (`resolved` / `still` / `changed` / `new`) — never copied forward as a fact.
- **Dispatch carrier**: the local fork carrier (`.specify/scripts/bash/stage-runner.sh`) for same-family agents, the subprocess carrier for heterogeneous ones. The host-internal in-process subagent path is BANNED as a concurrency carrier.
- **Agent availability**: the template must resolve at one of its two faces; absence is a hard failure reported as such — never a reason to substitute a general-purpose role.

## Workflow

### 1. Load context (before any scan)

Read, by pointer: `.specify/shared/definitions/framework-map.md` (directory semantics), `.specify/shared/definitions/non-disposable-definitions.md` (disposition set and retention), `.specify/shared/guidelines/confirmation-gates.md` (destructive gates), `.specify/shared/definitions/one-source-of-truth.md` (fact ownership). Load the project's history knowledge (`history/`, `.specify/memory/knowledge/`, `register.md`, `features.md`). The agent repeats this load in each execution; this step exists so the partition is informed.

### 2. Partition into disjoint read domains

Split the scope into domains whose read sets never intersect (e.g. runtime state + scratch, specs by number band, .specify/memory/history/register, code surfaces). Declare each domain's paths before dispatch. A path assigned to two domains is a dispatch defect.

### 3. Dispatch one sdd-debt-governor execution per domain

For each domain, dispatch one bounded execution of the agent template with: its read domain, its report path, the reuse baseline slice, the fast-fail clause, and the anomaly-line requirement. Run domains concurrently up to the slot ceiling; record `requested` / `effective` / `effective_reason`.

### 4. Verify each return

A domain return is accepted only when: the report artifact exists and is non-empty; every finding carries an evidence path and a status class; the closing `DEBT-DONE` line appears in the report **and** the execution log (stdout); the anomaly line is present (`none` stated explicitly). A missing artifact or a sentinel present in only one surface is an incomplete unit — re-dispatch it or report it as a gap; never synthesize from a silence.

### 5. Synthesize through the same agent

Dispatch one final `sdd-debt-governor` execution over the accepted domain reports to produce the debt register (register ID · severity · status class · category · evidence · fact · disposition · owning lane · wave) and the phased plan (mechanism-first, then data reclamation, then structural convergence), with measurable outcomes and abort conditions per wave. Deduplicate by evidence path; a finding without a path is dropped. Same-path verdict conflicts are adjudicated by the owning document's text, with the losing reading kept and marked `superseded-by`.

When a reuse baseline was supplied, the synthesis MUST carry the four-class comparison (`consistent` / `refined` / `new` / `refuted`) and a method-delta section; the comparison is part of the deliverable, never an afterthought.

### 6. Report and adjudicate

Report the output paths, the counts (findings by severity, domains accepted/gapped), the concurrency reading, and the **adjudication points** — every decision the user must make (deletion authorization, retention parameters, scope) as short closed questions. State explicitly that nothing was deleted, moved or modified.

### 7. Handoff

On user authorization: data reclamation goes to `/speckit.sanitize` (its lanes and confirmation gates own the execution); mechanism repairs go to an SDD run. When an authorized batch is dispatched for execution, its executor is the **`sdd-debt-fixer` agent template** (`agents/sdd-debt-fixer.agent.md`, runtime face `.specify/agents/templates/`) — one bounded write territory per execution, items and authorization passed verbatim from the register. This skill neither executes nor schedules either.

## Behavior Rules

- **The agent judges; this skill orchestrates.** Never invent, downgrade or drop a finding the agent reported; never promote one to a fact without its evidence path.
- **Disjoint domains only.** Overlapping read domains are a defect, not an optimization.
- **Reuse is re-verification.** A baseline finding is a candidate, not a conclusion; carry its status class explicitly, and label non-reproducible readings as such.
- **Foreign owners are blockers, not deletions.** Scratch this run created may be reclaimed by the execution that made it; root- or foreign-owned artifacts are reported as blockers with counts — never deleted, moved or chmod-ed.
- **No destructive action, ever.** No delete, move, archive, rewrite or git write outside the declared report directory.
- **Surface anomalies at the point they appear** (`.specify/shared/guidelines/fast-fail.md`); an incomplete domain is named, never smoothed into the synthesis.

## Boundaries

- **Cleanup is not this skill.** Reclamation belongs to `/speckit.sanitize`; repairs belong to SDD runs; their owners stay by pointer.
- **The role definition is not this skill.** Method, evidence discipline, severity rubric, disposition vocabulary and boundaries live in `agents/sdd-debt-governor.agent.md`; this skill binds the invocation, not the behavior.
- **No second registry.** The debt register is a report artifact; it is not a durable registry and grants nothing.
- **The command surface is out of scope** in this release: the capability is skill-level; a slash-command wrapper is a separate, spec-gated decision.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:debt-audit" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:debt-audit" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:debt-audit" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
