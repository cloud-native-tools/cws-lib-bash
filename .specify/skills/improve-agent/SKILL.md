---
name: improve-agent
description: General-purpose skill to improve a single Spec Kit agent artifact — role template, supervisor, supervision snippet, or custom agent — from execution feedback, user corrections, and behavioral observations. Use this when the user mentions ["improve agent", "refine agent", "fix agent", "agent feedback", "agent not working", "优化agent", "改进agent", "agent执行反馈"]
skill_id: "<SKILL:.specify/skills/improve-agent/SKILL.md>"
---

# improve-agent

## Goal

Improve **an existing single-agent artifact** based on evidence from real usage — user feedback, failure cases, behavioral drift, or observed inefficiencies. Targets include role templates, the shared supervision snippet, generated agents, and execution configs. The result is a targeted update that fixes the identified issues while preserving the artifact's established structure. To adjust or optimize a multi-agent **team** (stages, orchestration, thresholds), use `improve-team` via `/speckit.team`.

Goal anchor (Constitution Principle XIII): this skill is a Better-Harness instrument — improving an agent artifact strengthens the **Task Understanding** and **Controlled Execution** dimensions (clearer role intent, more reliable guided behavior) and closes the **Learning Capture** loop; goal model in `.specify/shared/guidelines/better-harness.md`.

## Input Contract

The input is a description of the agent to improve and what went wrong or could be better. Parse:

- **Layer (mandatory, explicit)**: which agent layer the improvement targets — `template` / `instance` / `execution` (taxonomy: `.specify/shared/definitions/agent-definitions.md`). Never infer the layer silently; if the request does not state it and the target identifier does not imply it unambiguously, ask the user before editing anything.
- **Target identifier**: Resolve to exactly one artifact of a supported kind (see § Target Classification):
  - `.specify/agents/templates/*.agent.md` (an installed role Template)
  - `skills/create-agent/templates/agent-capacity-*-template.md` (an abstract capacity Class)
  - `skills/create-agent/templates/agent-supervision-delegation.md` (shared supervision snippet — edits here propagate to ALL supervisors)
  - `.specify/agents/instances/*.agent.md` (a generated custom / project-custom agent)
  - `.specify/agents/execution/configs/*.yaml` or `execution/scripts/*` (dispatch config / wrapper)
- **Improvement direction**: What specifically needs to change — extracted from user feedback, observed failures, or behavioral drift.
- **Evidence**: Concrete examples of the problem (conversation excerpts, incorrect outputs, missing behaviors; for the execution layer, runtime logs under `.specify/agents/execution/logs/` are first-class evidence — read them, never edit them).

## Target Classification

Before the workflow, classify the target by **layer + kind** and route to the matching refinement rules:

| Layer | Target kind | Match | Route to |
|-------|-------------|-------|----------|
| template | role Template | `.specify/agents/templates/*.agent.md` | Workflow steps 1–6 (root-cause on the six mandatory sections) |
| template | capacity Class | `agent-capacity-*-template.md` | Workflow steps 1–6 (root-cause on the six mandatory sections) |
| template | supervision snippet | `agent-supervision-delegation.md` | Workflow steps 3–5; WARN that changes affect every supervisor (single source) |
| instance | custom / project-custom | `.specify/agents/instances/*.agent.md` | Workflow steps 1–6 against the generated file's own structure; keep the Template reference (`capacity-scope:`) intact — capability gaps route to the template layer instead |
| execution | dispatch config / script | `.specify/agents/execution/{configs,scripts}/*` | Workflow steps 2–6 driven by log evidence; preserve the Visibility Contract (`.specify/shared/definitions/subagent-definitions.md`); logs themselves are read-only evidence, never a target |

If the identifier matches multiple kinds or none, ask one clarifying question. A misbehaving **running** execution is out of scope — terminate/re-dispatch it; the durable fix lands in one of the three layers above.

## Workflow

### 1. Identify the target template

- Parse the user's input for a role name, slug, or artifact path, plus the declared **layer**
- Resolve within the declared layer: `template` → `.specify/agents/templates/<slug>.agent.md` or `skills/create-agent/templates/agent-capacity-<slug>-template.md`; `instance` → `.specify/agents/instances/<slug>.agent.md`; `execution` → `.specify/agents/execution/configs/<slug>.yaml`
- If multiple artifacts match or none match, ask one clarifying question
- Read the current artifact content before making changes

### 2. Gather evidence

First execute Step A/B per `.specify/shared/workflow/evidence-step.md` (single source of truth): reuse or collect findings via `evidence-utils.py --action latest|collect --target skill:create-agent --lanes all` — the **assets lane** carries template lint/inventory evidence relevant to agent artifacts; session/feedback lanes carry behavioral and recurring-theme signals. Triage by `evidenceState` and freeze the candidate list. Combined red line: do NOT optimize from generic best practices without execution evidence, and do NOT treat `Unobserved` items as defects — both are the same discipline: no evidence, no edit.

Then collect concrete supplementary evidence of what needs improvement:

- **User feedback**: Direct statements about what the agent did wrong
- **Behavioral observations**: How the generated agent actually behaved vs. expected behavior
- **Output quality**: Whether the agent's output format matched the template's specification
- **Workflow adherence**: Whether the agent followed its defined workflow steps
- **Handoff issues**: Whether upstream/downstream references worked correctly

### 3. Analyze root causes

For each issue, determine whether the root cause is in:

- **Identity section**: Role definition too vague or too narrow
- **Responsibilities**: Missing duties or conflicting priorities
- **Workflow**: Steps unclear, wrong order, or missing critical steps
- **Upstream/Downstream**: Incorrect references or missing handoff artifacts
- **Output Format**: Expected output not matching what downstream roles need
- **Placeholders**: Wrong context variables for this role's needs

### 4. Apply targeted fixes

- Make minimal, focused changes that address the identified root causes
- Preserve the established template structure (six mandatory sections)
- Do not change sections that are working correctly
- Verify that fixes maintain handoff chain consistency with other roles

### 5. Validate the updated template

- Verify YAML frontmatter still has required fields
- Verify `tools` field remains omitted
- Verify all six mandatory sections are still present
- Verify only approved `{{PLACEHOLDER}}` variables are used
- Verify upstream/downstream references are still consistent

### 6. Report

- List the specific changes made and why
- Reference the evidence that motivated each change
- Suggest re-running `/speckit.agents` to regenerate the agent from the updated template
- Recommend testing the improved agent with the scenario that originally failed

## Constraints

- The **layer** MUST be explicit before any edit; the layer decides the editable surface (template → templates stores; instance → `.specify/agents/instances/`; execution → `execution/{configs,scripts}/` only — logs are read-only evidence)
- Changes MUST be evidence-based — do not optimize from generic best practices without concrete evidence
- The established template structure (six mandatory sections) MUST be preserved
- Handoff chain consistency with other role templates MUST be maintained
- Prefer minimal changes that fix the observed problem over broad rewrites

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

If you identified your agent in Step 1, check if a guide exists at:

```
${SKILL_HOME}/references/<agent-slug>-guide.md
```

Where `<agent-slug>` is: `claude-code`, `copilot`, `qoder`, `opencode`, `codex`, `hermes`.

If the guide exists, read it and apply the agent-specific tool mappings, best practices, and pitfall avoidances during execution. If no guide exists for your agent, proceed with the standard workflow.

### Step 3: Capture Execution Feedback

If you encounter an agent-specific obstacle during execution (e.g., a tool call is unavailable, output format doesn't match expectations, a workaround was needed), generate a feedback document at:

```
.specify/memory/feedback/improve-agent-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

The feedback document MUST contain:

```markdown
# Agent Execution Feedback

**Source**: improve-agent
**Agent**: <agent-slug>
**Timestamp**: <ISO-8601>
**Outcome**: <success-with-workaround | partial-failure | full-failure>

## Obstacle
[Description of the agent-specific issue encountered]

## Workaround Applied
[What was done to work around the issue, if anything]

## Suggested Improvement
[Specific change to the skill or reference document that would prevent this issue]
```

Only generate feedback when a genuine agent-specific obstacle was encountered.

## Self-Improvement Routing

Start every run with SI-0 from `.specify/shared/workflow/self-improvement-workflow.md`. This skill is an Assisted Improvement executor by default. If the target Agent supplied the initiating signal from its own completed execution, preserve origin=`self` while this skill acts as the delegated improver. Reuse the existing evidence step as SI-2, write the Step-E intervention ledger after edits, and report outcome pending until a later comparable Agent Execution. This `improve-agent` Skill’s own run evidence targets `improve-skills`, not the Agent currently being improved.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:improve-agent" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
