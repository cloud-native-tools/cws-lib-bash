---
name: review-sdd-process
description: Critically review the SDD process behind a completed feature — the spec/plan/tasks artifacts and the workflow that produced them, never the code they produced — and produce a self-contained, improvement-focused report for the spec-kit framework maintainers. Captures portable project context with commit-reachability verification, reconstructs the process execution history from git (with working-tree fallbacks when commits are missing or ungrouped), diagnoses friction, ambiguity, cargo-cult boilerplate, drift risks and process gaps, validates every P0 finding through an independent read-only subagent wave with evidence snapshots at diagnosis time, and fills the review report template. This skill has no overlap with the code-review skill, which reviews code diffs/PRs. Use this when the user mentions ["review SDD process", "process review", "SDD 过程评审", "过程评审", "评审 SDD 过程", "review report", "评审报告", "improvement report", "改进报告", "framework friction", "process gaps", "过程改进", "process retrospective", "/speckit.review"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/review-sdd-process/SKILL.md>"
---

# review-sdd-process

## Goal

Produce a **self-contained, improvement-focused** review report for spec-kit framework
maintainers — a critique of the SDD process that produced a feature, not of the feature's
business merits. Owning command: `/speckit.review`. The report MUST:

1. Be readable standalone — embedded evidence, absolute paths or `{REPO_URL}@{COMMIT_SHA}`
   references
2. Prioritize problems, friction, ambiguities in the SDD process
3. Focus on process/tooling quality, not business merits

Canonical extraction source: `.specify/templates/commands/review.md` § Goal, § Operating Constraints,
and § Outline 1–6 including §4.5. Content moved here verbatim in substance; the command
template keeps entry + delegation only.

## Input Contract

- **When**: after `/speckit.implement` completes. Typical flow: feature → requirements →
  plan → tasks → implement → **review**. Running it earlier reviews an incomplete process.
- **Arguments**: guide review focus areas only. The transport and the User Input Protocol
  belong to the command, not this skill.
- **Subject**: the feature's artifact chain under `REQUIREMENTS_DIR` (resolved in step 1).
  A missing required artifact surfaces when the prerequisite script runs — do not improvise
  around it.

## Operating Constraints

- **Problem-first**: Do not narrate artifact contents. Identify process gaps.
- **Self-contained**: Evidence quoted inline. No references to local-only resources.
- **Evidence-backed**: Every finding cites a specific quoted excerpt. Drop unsupported
  findings.
- **Process scope only**: Don't judge feature business content.

## Workflow

### 1. Capture portable project context

Run the command's declared prerequisite script once from repo root; parse
`REQUIREMENTS_DIR`, `FEATURE_ID`, `FEATURE_NAME`, `AVAILABLE_DOCS`. Then capture via
git/shell the portable context items: `REPO_NAME`, `REPO_URL`, `BRANCH`, `COMMIT_SHA`,
`REPO_ROOT_ABS`, `REVIEW_DATE`, `REVIEWER`, `ENVIRONMENT`, SPECKIT version, and
`ARTIFACT_INVENTORY` (basename, path, line count, one-line summary per artifact).

**Verify that commit-anchored citations will actually resolve** before relying on them —
this fails routinely in forks:

- Capture ALL remotes (`git remote -v`), not just `remote.origin.url`. In a fork, `origin`
  is often the UPSTREAM project while the work lives on a differently-named remote, so a
  `{REPO_URL}@{COMMIT_SHA}` citation built from `origin` points at a repository that does
  not contain the commit.
- Run `git branch -r --contains HEAD`. If it is empty the commit is unpushed and NO URL
  citation can resolve.
- Record the result as a `Reachability of COMMIT_SHA` row in §0 (Portable Project Context)
  of the report. When unreachable, cite absolute paths plus `git show <sha>:<path>`
  recovery instructions instead of URLs, and say so explicitly — a report that looks
  portable but is not is worse than one that is obviously local.
- Note that `blob/` URL syntax assumes an HTTPS web remote; SSH-only remotes cannot be
  rendered that way.

### 2. Reconstruct process execution history

From `git log` scoped to `REQUIREMENTS_DIR`: commit ordering, command traces (distinctive
artifacts), deviations from prescribed workflow, friction moments (dirty tree, version
skew, manual rewrites, repeated template fixes).

**Fallback when `git log` for `REQUIREMENTS_DIR` is empty** (the feature was implemented
but never committed): reconstruct from working-tree state instead — `git status --short`
for the spec dir, staged/untracked artifact set, and `verification.md` self-reports — and
record the missing-commit condition itself as a process-history finding.

**Degradation when commits exist but are NOT story/task-grouped** (e.g. one bulk
"implement everything" commit, or commits that mix several phases): git history cannot
attribute artifacts to individual tasks. Degrade to working-tree + artifact
reconstruction (task `[X]` markers, file mtimes, `verification.md` self-reports) for the
per-task timeline, use the commits only for coarse ordering, and annotate every timeline
claim drawn from this path with its evidence strength (e.g. "inferred from artifact
state, not commit trace"). Record the missing story-grouped commit discipline itself as a
Workflow finding citing the commit gate in the `/speckit.implement` command.

### 3. Load core SDD artifacts

From `REQUIREMENTS_DIR`: requirements.md, plan.md, tasks.md (REQUIRED). Plus
data-model.md, contracts/, research.md, checklists/, feature detail (IF EXISTS). Also
load constitution, templates, scripts, command files as reference targets for
recommendations.

### 4. Diagnostic review — problem-first

**Same-author detection delegation**: when the artifacts under review were produced by
the agent now running this skill, in the current session — the ordinary case when this
review follows an implement run the same agent performed — self-review is weak evidence,
and detection MUST be delegated to fresh-context read-only subagents rather than left to
step 5. Apply the canonical gate in
`.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not
restate its rules here). This skill's local parameter: the propagation-surface cap is
**P1** (used when no downstream artifact or process step inherits the finding).

For each artifact and workflow as a whole, find issues:

- **Friction**: Extra work forced by template/prompt/script gaps
- **Ambiguity/contradiction**: Conflicting instructions
- **Cargo-cult/boilerplate**: Irrelevant template content
- **Missing structure**: Ad-hoc prose where template fields should exist
- **Drift risk**: Same facts in multiple places without single source of truth
- **Process gaps**: Lifecycle steps lacking automation

Per finding: **ID** (F1, F2...), **Severity** (P0/P1/P2), **Category**
(Template | Command Prompt | Automation | Workflow | Documentation), **Location**
(absolute path or URL), **Evidence** (quoted excerpt), **Why**, **Proposed fix**.

### 5. Finding validation (independent subagent pass)

Every **P0** finding MUST be confirmed by an independent read-only validation subagent
before it enters the report:

- The validator receives ONLY the finding (id, claim, severity, location, quoted
  evidence) — never the diagnostic reasoning or sibling findings — and returns
  `confirm` / `reject` (with why) / `downgrade` (with proposed severity).
- **Disjoint from the detection pass**: when step 4 delegated detection under the
  same-author gate, no validator may validate a finding its own detection pass produced
  (owner: `.specify/shared/workflow/objective-analysis-gate.md` rule 5).
- Only `confirm`ed findings keep P0; `downgrade`d rows take the proposed severity with a
  `(validated: downgraded)` note; `reject`ed rows go to an **Unvalidated Findings**
  appendix in the report — never silently dropped. P1/P2 skip validation.
- **Evidence snapshot at diagnosis time**: capture the quoted evidence (path + line +
  literal excerpt) when the finding is diagnosed, not when it is validated — the tree can
  move between the two, and a validator re-reading a since-changed line rejects a finding
  that was true when observed.
- **Counts are enumerated, never asserted**: when a finding claims N occurrences, the
  validator receives the enumerated instances each carrying its own anchor; dispatch only
  once every instance is anchored, so an inflated count cannot pass as a single confirmed
  claim.
- **Subagent-unavailable fallback**: if the validation subagent dispatch fails twice in a
  row (upstream error), a direct evidence re-read by the reviewing agent MAY substitute;
  the finding row MUST then carry `(validated: direct re-read, subagent unavailable)` so
  the weaker evidence path stays visible to the reader.
- Do not flag: deliberate `[~]` deferrals with recorded reasons, mirror-by-design
  duplication under `.specify/`, or pre-existing baseline failures already recorded for
  the feature.

### 6. Generate report

Use the review report template `.specify/templates/review-template.md` as the structure.
Fill all sections: Context → Timeline → Findings Summary → Findings → What Worked (brief
bullets only) → Recommendations (cite target files) → Priority Roadmap. Self-containment
check before writing. Write to `REQUIREMENTS_DIR/review.md`.

### 7. Report summary

`REQUIREMENTS_KEY`, feature name, commit SHA, report path, finding counts (P0/P1/P2 by
category), top 3 recommendations.

## Boundaries

- **Code review is not this skill.** The existing `code-review` skill reviews **code
  diffs/PRs** (pre-submission author self-check, structured dimension review of a delta).
  This skill reviews the **SDD process artifacts** (spec/plan/tasks) and the workflow that
  produced them. No overlap — keep the two separate even though both say "review".
- **Cross-artifact consistency analysis is not this skill.** `/speckit.analyze` runs a
  read-only consistency pass **before** implementation (drift, coverage gaps, ambiguity);
  this skill critiques the process **after** implementation and feeds framework
  improvement, not artifact repair.
- **Feedback is not this skill.** `/speckit.feedback` is a cross-cutting,
  framework-targeted mechanism over accumulated unit-run entries; this skill is an
  SDD-flow review of one feature's process. The boundary is owned by
  `.specify/shared/workflow/feedback-step.md` § *Mechanism boundary*.
- **Remediation is not this skill.** It produces findings and recommendations; applying
  improvements to .specify/templates/commands/scripts, or iterating requirements/plan, is a
  follow-up the maintainer or a later run performs.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:review-sdd-process" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:review-sdd-process" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:review-sdd-process" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
