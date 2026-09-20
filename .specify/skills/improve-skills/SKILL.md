---
name: improve-skills
description: This skill continuously improves one local Skill from a user-provided Skill description, execution history, user feedback, failure cases, and observed inefficiencies. Use this when the user mentions ["improve skills after use", "skill execution feedback", "refine SKILL.md", "skill retrospective", "skill iteration", "技能执行反馈", "基于执行问题优化skill", "持续改进Skill"]
skill_id: "<SKILL:.specify/skills/improve-skills/SKILL.md>"
---

# improve-skills

## Goal

Continuously improve one existing local Skill from a user-provided Skill description and evidence from real executions. The expected result is a focused Skill update that fixes observed problems, captures reusable lessons, and makes the next execution more reliable.

Goal anchor (Constitution Principle XIII): this skill is a Better-Harness instrument — improving a Skill strengthens the **Controlled Execution** dimension (the supported, repeatable path the Skill provides) and closes the **Learning Capture** loop; goal model in `.specify/shared/guidelines/better-harness.md`.

## Input Contract

The input is a description of the Skill to improve. It must be interpreted as follows:

- **Target identifier**: identify exactly one local Skill by `skill_id`, frontmatter `name`, canonical path, or Skill directory name. If multiple Skills match or no local Skill can be found, ask one targeted clarification before editing.
- **Optimization direction**: extract the requested direction when present (execution failures, efficiency, input/output clarity, tool usage, validation strength). If absent, infer it only from concrete execution history and user feedback.
- **User emphasis — highest priority**: the user's optimization descriptions are the highest-priority input. They receive a dedicated application pass (Workflow step 6) and outrank this skill's built-in optimization defaults; the only bound is the normative red lines (step 6's conflict rule).
- **Batch mode** (user names a *set* of Skills or a whole directory): run **one** batch pass — collect evidence once, freeze the per-skill candidate list, prefer mechanical sanctioned conformance edits over speculative rewrites, verify mirrors once at the end. Do not loop the full workflow N times blindly.
- **Batch triage ownership**: a Skill absent from *this* repo is not automatically out of scope — resolve where it actually lives and process it there when the user owns that location.
- **Intent routing guard**: if the intent is to *monitor/score an ongoing execution* rather than modify a Skill, this is the wrong entry point (editing conflicts with monitoring's zero-write red line) — route to a `continuous` team and say why.

Batch procedure, ownership resolution, and routing rationale: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Input Contract`.

## Workflow

总体流程:**调研(步骤 2–3)→ 按规范优化(步骤 4–5)→ 按用户要求优化(步骤 6)→ 最终检查(步骤 8)**;步骤 1/7/9 是识别、落盘与报告框架。

1. **Identify the target Skill, optimization direction, and execution window**
   - Resolve the description to exactly one local Skill (`skill_id` / frontmatter `name` / canonical path / directory name). For “this Skill”, infer from the active file or recent conversation, then verify it resolves uniquely.
   - Treat `.specify/skills/<name>/SKILL.md` as the canonical source of truth; `.github/skills/<name>` is only a compatibility entrypoint. **Re-read the canonical file before editing** — a user edit, formatter, or refresh script may have changed it.
   - Carry the optimization direction through evidence, analysis, edits, validation, and reporting. Define the execution window: current conversation, last run, failed command output, user correction, test failure, or recent edits.
   - When improving `improve-skills` itself, use the most recent improvement loop as the window and do not reapply a lesson already applied unless new evidence shows the previous fix was insufficient.

2. **调研实现 — research the Skill's current implementation (before any optimization action)**
   - Read the full implementation: `SKILL.md` + `references/` + `scripts/` + `assets/`; run `python3 ${SKILL_HOME}/scripts/skill-shape.py <SKILL.md>` for the objective shape verdict.
   - Assess strengths and weaknesses **from the implementation's own perspective**, beyond norm conformance: which mechanisms are load-bearing, which sections are dead weight, where the workflow leaks decisions, which prose is deterministic logic in disguise, what optimization space remains.
   - Record a research note (strengths / weaknesses / optimization space) before any edit; every later keep/change/drop decision traces back to it. Conformance-only optimization without this research is theater. Method detail: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 2`.

3. **调研证据 — measure execution effectiveness (evidence-step A/B)**
   - Execute Step A/B per `.specify/shared/workflow/evidence-step.md` (single source of truth; do not restate its rules here): reuse fresh findings via `evidence-utils.py --action latest --target skill:<name>`, or collect via `--action collect --target skill:<name> --lanes all` (session + feedback lanes carry the strongest signals).
   - Triage findings by `evidenceState`, then **freeze the candidate list** — later steps must not add or drop candidates. Red lines: `Unobserved` items are recorded only and MUST NOT be treated as defects; counting signals MUST NOT directly generate optimization points.
   - Supplementary evidence from the execution window, runtime failures and silent under-extraction as first-class evidence, and the degenerate-evidence fallback: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 3`. If evidence is insufficient, ask one targeted question about what failed, what was inefficient, or what should happen differently next time.

4. **Organize improvement items**
   - Give the user's stated optimization direction a dedicated analysis pass: confirm what is already satisfied, what is missing, and which edits address the request.
   - Group observations by failure mode: trigger/discovery, scope inference, missing context, wrong tool choice, unsafe step, unclear output, validation gap, resource/reference issue, **constraint non-compliance** (diagnose as a constraint-*placement* problem per [`./references/constraint-placement.md`](./references/constraint-placement.md) before rewording the rule), or **cross-skill ownership boundary**.
   - For each item, record: symptom, likely cause in the Skill instructions, desired next behavior, and the section to change. An item deferred for lack of evidence names the concrete evidence that would unlock it.
   - **Red-line conformance gate (proactive, mandatory)** — run `python3 ${SKILL_HOME}/scripts/redline-check.py <target SKILL.md>`: it collects the target's attributes (automation / sensitive-info / …), fires the red lines bound to each present attribute, and returns PASS or TRIGGERED. A TRIGGERED red line is a **MUST-fix** item — not evidence-gated, not deferrable: remediate it, or record why each flagged signal is a sanctioned, announced exception. Framework, registry, admission rigor, and the HC5 reconciliation: [`./references/red-lines.md`](./references/red-lines.md).
   - Gates before acting — misuse-vs-pitfall gate, fact-check gates (delegation capability / data tables / tier coverage), legacy path idiom detection (bare relative paths / `${SKILL_ROOT}/X` / agent-specific install paths → rewrite as `${SKILL_HOME}/...`), Feedback-section conformance: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 4`.

5. **按规范优化 — correct the root causes with minimal changes**
   - Fix the instruction that caused the observed failure first (wrong arguments, nonexistent paths, invalid formats, missing prerequisite checks); for inefficiency, replace the step with a more direct method, deterministic script, or clearer decision branch. Prefer changing the failing step over adding broad new rules; convert repeated user corrections into explicit decision branches.
   - Apply transferred lessons from references, do not restate them here: DOM/live-surface hardening and ground-truth-over-label extraction → [`./references/hardening-examples.md`](./references/hardening-examples.md); constraint non-compliance → fix placement before wording per [`./references/constraint-placement.md`](./references/constraint-placement.md) (a generic "follow the constraints" reminder is a measured no-op).
   - **Keep `SKILL.md` a contract — for content you REMOVE and for content you ADD.** New detail defaults to `./references/` or `./scripts/`; existing manual content moves out per [`./references/skill-slimming-principles.md`](./references/skill-slimming-principles.md), always **delete-and-absorb**, never delete-and-drop. **Never slim a section a feature spec or contract test mandates inline** — grep `.specify/specs/**` and `tests/contract/**` before moving any named heading. Defer environment-level recovery (auto-install, shell switching, OS branching) to the user — surface the error and the fix command, then stop.
   - **Codify deterministic logic; reserve natural language for judgment** — extract recurring deterministic prose (path derivation, validation, decision trees, transforms) into self-describing `${SKILL_HOME}/scripts/` scripts; judgment stays prose. Criteria and script requirements: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 5`.

6. **按用户要求优化 — apply user-passed requirements with priority**
   - The user's optimization descriptions get a dedicated application pass **after** the norm pass: within the frozen candidate list, user-required edits land first; when a built-in optimization default (slimming preference, structure habit, style norm) conflicts with a user requirement, **the user requirement wins**.
   - **Bound — 不破坏技能规范**: a user requirement must not violate normative obligations (this skill's Hard Constraints, the target's contract-mandated sections, evidence/red-line discipline). On such a conflict, surface it explicitly and propose the closest compliant realization — never silently drop the requirement, never silently break the norm.
   - Priority is decision order, not verification exemption: user-pass edits pass the same step-8 gates. Conflict taxonomy and worked cases: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 6`.

7. **Update the Skill for the next execution**
   - Edit `SKILL.md` to make the improved behavior executable and checkable. Update frontmatter `description` only when execution feedback shows trigger/discovery mismatch; update `./references/`, `./scripts/`, or `./assets/` only when the evidence shows they will reduce future mistakes. Scripts extracted in step 5 are listed in the Resources table.
   - Distill only reusable lessons — no process logs, changelogs, or retrospectives. **Never narrate the document's own history** (`旧文档断言…已证伪` / `重要勘误` frames) — exceptions and rewrite examples: [`./references/skill-slimming-principles.md`](./references/skill-slimming-principles.md) `## No History Narration`.
   - **Rename/removal downstream-wiring checklist**: a rename/consolidation/removal is not done until every downstream pointer moves with it (obsolete-skills list, contract tests, skills-count list, feature history, dogfooded artifacts) and both mirrors are byte-equal. Five-step checklist and move-then-edit ordering: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 7`.

8. **最终检查 — validate the improvement loop**
   - Re-read the changed Skill and verify each edit maps to an observed execution issue or a user requirement.
   - **Run the shape gate on every `SKILL.md` you touched**: `python3 ${SKILL_HOME}/scripts/skill-shape.py <SKILL.md>` — exit `0` required, or the report carries a recorded exception per Hard Constraint 3, including the before/after controllable-token counts (step-2 baseline run vs this run) and their delta. Never finish a loop having grown a body past the gate without saying so.
   - **Re-run the red-line gate**: `python3 ${SKILL_HOME}/scripts/redline-check.py <SKILL.md>` must exit `0`, or the report records why each remaining signal is a sanctioned exception. A loop MUST NOT finish with a triggered red line left unremediated (see [`./references/red-lines.md`](./references/red-lines.md)).
   - **Reference code is executed, not eyeballed**: run or line-trace changed snippets/scripts against a real target; files-exist/links-resolve is not validation — if you cannot run it this loop, mark it as needing runtime validation rather than reporting it verified. When metadata changed, check frontmatter, resource paths, `skill_id`/directory/`name` agreement, and accept a directory-level `.github/skills -> ../.specify/skills` symlink as a valid compatibility entrypoint.
   - **Structural edits run the affected contract tests** (`tests/contract/` of the governing feature) — heading greps are not proof. On a red suite, prove zero regression with a clean-baseline failure-set diff (prefer `git worktree` over `git stash`): [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 8`. **Behavior-changing edits get a pressure re-test (RED-GREEN)** per `create-skills/references/pressure-testing.md`; wording-only or resource-path edits are exempt — state which case applied.
   - Skill-owned executable resources belong in `./scripts/`, never documented as `.specify/scripts/`. **Intervention ledger (evidence-step Step E)**: when the run consumed findings evidence, write `intervention.json` into the baseline evidence-run directory (targetFinding / change / baselineRunId / expectedSignal); never claim "fixed" without the next-run before/after comparison.

9. **Report the feedback-driven changes**
   - Summarize the driving evidence, list changed files and the behavior expected to improve, and note unresolved feedback that needs another real execution to validate.

## Quality Checklist

Use [the Skill quality checklist](./references/skill-quality-checklist.md) to structure execution feedback, root-cause analysis, and validation when the improvement involves more than one observed issue.

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/improve-skills/SKILL.md>`
- Canonical Path: `.specify/skills/improve-skills/SKILL.md`

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

Before executing this skill's workflow, identify which AI agent you are:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Codex CLI** | `.codex/` directory exists |
| **Hermes Agent** | `.hermes/` directory exists |

If you cannot identify your agent, skip Step 2 and proceed with the standard workflow.

### Step 2: Load Agent-Specific Guidance

If you identified your agent in Step 1, check if a guide exists at `${SKILL_HOME}/references/<agent-slug>-guide.md` (`<agent-slug>` ∈ `claude-code`, `copilot`, `qoder`, `opencode`, `codex`, `hermes`). If it exists, read it and apply the agent-specific tool mappings, best practices, and pitfall avoidances during execution; otherwise proceed with the standard workflow.

### Step 3: Capture Execution Feedback

On a genuine agent-specific obstacle (tool call unavailable, unexpected output format, workaround needed), write a feedback document to `.specify/memory/feedback/improve-skills-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md` carrying fields `**Source**: improve-skills`, `**Agent**`, `**Timestamp**` (ISO-8601), `**Outcome**` (`success-with-workaround | partial-failure | full-failure`) and sections `## Obstacle` / `## Workaround Applied` / `## Suggested Improvement`. Only generate feedback for a genuine obstacle.

## Resources

| Directory | Contents |
|-----------|----------|
| `${SKILL_HOME}/references/` | `skill-slimming-principles.md`, `loop-playbook.md`, `skill-quality-checklist.md`, `hardening-examples.md`, `constraint-placement.md`, `red-lines.md` (attribute-triggered red-line framework, registry catalogue, admission rigor), `claude-code-guide.md`, `copilot-guide.md` |
| `${SKILL_HOME}/scripts/` | `skill-shape.py` — deterministic L1 shape gate for a `SKILL.md` (token budget, fence ratio, long fences, example sections); exit `0` pass / `10` slim-recommended; `--help` for thresholds and calibration. `redline-check.py` — deterministic attribute-triggered red-line probe (collect attributes → fire bound red lines → verdict `not-applicable`/`gap`/`review`/`compliant`); exit `0` pass / `1` triggered; `--json`, `--scan-all`, `--help` |

## Hard Constraints

Objective conditions for finishing a loop. Each is checkable, not a matter of judgement.

1. **Research before optimization.** No edit happens before the step-2 research note (strengths / weaknesses / optimization space) exists; conformance-only polish without implementation research is not an improvement loop.
2. **User requirements are never silently dropped.** Every user-passed optimization requirement is either implemented, or surfaced as a norm conflict with a closest compliant realization proposed. Priority never exempts the step-8 gates.
3. **Contract shape is gated, not estimated.** Every `SKILL.md` touched this loop must end at `skill-shape.py` exit `0`, or the step-9 loop report must carry a **recorded exception** with two parts: (a) the qualifying case — a contract-mandated inline section (naming the spec/test that mandates it) or a pre-existing over-budget baseline (the file already exited `10` at the step-2 read); and (b) the before/after `est_tokens_controllable` numbers from the step-2 and step-8 gate runs plus their delta. A case named anywhere but the loop report, or named without both numbers, is not a recorded exception — the gate stays red. Case taxonomy and delta mechanics: [`./references/loop-playbook.md`](./references/loop-playbook.md) `## Step 8`. Do not substitute an impression that the file "looks fine".
4. **New detail lands in L2/L3 by default.** Do not add worked examples, full command sequences, or multi-line snippets to `SKILL.md` — write them into `./references/` or `./scripts/` and leave a one-line pointer with an anchor in the body.
5. **Evidence before defect.** Do not label anything a defect without an observed symptom (error text, wrong output, user correction, artifact). `Unobserved` findings are recorded only; counting signals alone never becomes an optimization point.
6. **Capability verified before it is documented.** Before writing a delegation path, data table, or coverage claim, read the delegate's real surface (`--help`, contract, cached facts) and encode honest limitation branches. Do not write values or capabilities from memory.
7. **Reference code is executed, not eyeballed.** Any snippet or script added/changed must be run (or traced line-by-line against the documented API). "File exists" and "links resolve" are not validation — state explicitly when runtime validation is deferred. For detection scripts also run a **reverse case on a domain-legitimate sample** (must NOT flag required syntax) — catching bad samples alone can induce deleting required syntax.
8. **Removal preserves content.** Every slimming move is delete-and-absorb in the same edit; never delete a section and defer relocating its substance.
9. **No claim of "fixed" without before/after.** Improvement outcomes are decided by the intervention ledger's next-run comparison, not by asserting the edit works.
10. **Wrap-up commits verify the staging area.** Before any loop-end commit, `git status --short` and confirm only this loop's files are staged; unstage unrelated pre-staged entries or commit by explicit pathspec — never `git add -A`.
11. **Red lines are mandatory, not recommended.** If `redline-check.py` returns TRIGGERED for the target, the loop MUST NOT finish until every triggered red line is remediated, or each flagged signal is explicitly recorded as a sanctioned, announced exception. Adding a new red line requires passing **all** admission criteria in [`./references/red-lines.md`](./references/red-lines.md) — a general best practice MUST NOT be promoted to a red line (that devalues the real ones).

## Self-Improvement Routing

Start every run with SI-0 from `.specify/shared/workflow/self-improvement-workflow.md`. This skill is an Assisted Improvement executor by default; when the target Skill’s own completed run produced the initiating signal, preserve origin=`self` and use this Skill as the delegated improver. Workflow step 3 is SI-2, step 8 performs SI-6/SI-7, and a later comparable run performs SI-8. Report the current intervention as outcome pending; never call it “improved” before comparison. When improving `improve-skills` itself, keep the target and improver roles explicit and use a separate verifier execution for behavior-changing edits.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:improve-skills" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
