---
description: 批判性评审当前特性的 SDD 过程，出具改进导向报告
---
<!-- AUTO-GENERATED from templates/commands/review.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters guiding review focus.

## Goal

Produce a **self-contained, improvement-focused** review report for spec-kit framework maintainers. The report MUST:
1. Be readable standalone — embedded evidence, absolute paths or `{REPO_URL}@{COMMIT_SHA}` references
2. Prioritize problems, friction, ambiguities in the SDD process
3. Focus on process/tooling quality, not business merits

## Operating Constraints

- **Problem-first**: Do not narrate artifact contents. Identify process gaps.
- **Self-contained**: Evidence quoted inline. No references to local-only resources.
- **Evidence-backed**: Every finding cites a specific quoted excerpt. Drop unsupported findings.
- **Process scope only**: Don't judge feature business content.

## Outline

### 1. Capture portable project context

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-spec --include-spec --include-plan --include-tasks`; parse REQUIREMENTS_DIR, FEATURE_ID, FEATURE_NAME, AVAILABLE_DOCS. Then capture via git/shell: REPO_NAME, REPO_URL, BRANCH, COMMIT_SHA, REPO_ROOT_ABS, REVIEW_DATE, REVIEWER, ENVIRONMENT, SPECKIT version, ARTIFACT_INVENTORY (basename, path, line count, one-line summary per artifact).

**Verify that commit-anchored citations will actually resolve** before relying on them — this fails routinely in forks:

- Capture ALL remotes (`git remote -v`), not just `remote.origin.url`. In a fork, `origin` is often the UPSTREAM project while the work lives on a differently-named remote, so a `{REPO_URL}@{COMMIT_SHA}` citation built from `origin` points at a repository that does not contain the commit.
- Run `git branch -r --contains HEAD`. If it is empty the commit is unpushed and NO URL citation can resolve.
- Record the result as a `Reachability of COMMIT_SHA` row in §0. When unreachable, cite absolute paths plus `git show <sha>:<path>` recovery instructions instead of URLs, and say so explicitly — a report that looks portable but is not is worse than one that is obviously local.
- Note that `blob/` URL syntax assumes an HTTPS web remote; SSH-only remotes cannot be rendered that way.

### 2. Reconstruct process execution history

From `git log` scoped to REQUIREMENTS_DIR: commit ordering, command traces (distinctive artifacts), deviations from prescribed workflow, friction moments (dirty tree, version skew, manual rewrites, repeated template fixes).

**Fallback when `git log` for REQUIREMENTS_DIR is empty** (the feature was implemented but never committed): reconstruct from working-tree state instead — `git status --short` for the spec dir, staged/untracked artifact set, and `verification.md` self-reports — and record the missing-commit condition itself as a process-history finding.

**Degradation when commits exist but are NOT story/task-grouped** (e.g. one bulk "implement everything" commit, or commits that mix several phases): git history cannot attribute artifacts to individual tasks. Degrade to working-tree + artifact reconstruction (task `[X]` markers, file mtimes, `verification.md` self-reports) for the per-task timeline, use the commits only for coarse ordering, and annotate every timeline claim drawn from this path with its evidence strength (e.g. "inferred from artifact state, not commit trace"). Record the missing story-grouped commit discipline itself as a Workflow finding citing the commit gate in the `/speckit.implement` command.

### 3. Load core SDD artifacts

From REQUIREMENTS_DIR: requirements.md, plan.md, tasks.md (REQUIRED). Plus data-model.md, contracts/, research.md, checklists/, feature detail (IF EXISTS). Also load constitution, templates, scripts, command files as reference targets for recommendations.

### 4. Diagnostic review — problem-first

**Same-author detection delegation**: when the artifacts under review were produced by the agent now running this command, in the current session — the ordinary case when this review follows an implement run the same agent performed — self-review is weak evidence, and detection MUST be delegated to fresh-context read-only subagents rather than left to §4.5. Apply the canonical gate in `.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not restate its rules here). This command's local parameter: the propagation-surface cap is **P1** (used when no downstream artifact or process step inherits the finding).

For each artifact and workflow as a whole, find issues:
- **Friction**: Extra work forced by template/prompt/script gaps
- **Ambiguity/contradiction**: Conflicting instructions
- **Cargo-cult/boilerplate**: Irrelevant template content
- **Missing structure**: Ad-hoc prose where template fields should exist
- **Drift risk**: Same facts in multiple places without single source of truth
- **Process gaps**: Lifecycle steps lacking automation

Per finding: **ID** (F1, F2...), **Severity** (P0/P1/P2), **Category** (Template|Command Prompt|Automation|Workflow|Documentation), **Location** (absolute path or URL), **Evidence** (quoted excerpt), **Why**, **Proposed fix**.

### 4.5 Finding validation (independent subagent pass)

Every **P0** finding MUST be confirmed by an independent read-only validation subagent before it enters the report:

- The validator receives ONLY the finding (id, claim, severity, location, quoted evidence) — never the diagnostic reasoning or sibling findings — and returns `confirm` / `reject` (with why) / `downgrade` (with proposed severity).
- **Disjoint from the detection pass**: when §4 delegated detection under the same-author gate, no validator may validate a finding its own detection pass produced (owner: `.specify/shared/workflow/objective-analysis-gate.md` rule 5).
- Only `confirm`ed findings keep P0; `downgrade`d rows take the proposed severity with a `(validated: downgraded)` note; `reject`ed rows go to an **Unvalidated Findings** appendix in the report — never silently dropped. P1/P2 skip validation.
- **Evidence snapshot at diagnosis time**: capture the quoted evidence (path + line + literal excerpt) when the finding is diagnosed, not when it is validated — the tree can move between the two, and a validator re-reading a since-changed line rejects a finding that was true when observed.
- **Counts are enumerated, never asserted**: when a finding claims N occurrences, the validator receives the enumerated instances each carrying its own anchor; dispatch only once every instance is anchored, so an inflated count cannot pass as a single confirmed claim.
- **Subagent-unavailable fallback**: if the validation subagent dispatch fails twice in a row (upstream error), a direct evidence re-read by the reviewing agent MAY substitute; the finding row MUST then carry `(validated: direct re-read, subagent unavailable)` so the weaker evidence path stays visible to the reader.
- Do not flag: deliberate `[~]` deferrals with recorded reasons, mirror-by-design duplication under `.specify/`, or pre-existing baseline failures already recorded for the feature.

### 5. Generate report

Use `.specify/templates/review-template.md` structure. Fill all sections: Context → Timeline → Findings Summary → Findings → What Worked (brief bullets only) → Recommendations (cite target files) → Priority Roadmap. Self-containment check before writing. Write to `REQUIREMENTS_DIR/review.md`.

### 6. Report summary

REQUIREMENTS_KEY, feature name, commit SHA, report path, finding counts (P0/P1/P2 by category), top 3 recommendations.

## Position in Workflow

Use after `/speckit.implement` completes. Typical flow: feature → requirements → plan → tasks → implement → **review**.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.review" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: Run after `/speckit.implement` for complete artifact chain.

**After**: Apply improvements to spec-kit .specify/templates/commands/scripts. Optionally iterate requirements/plan.