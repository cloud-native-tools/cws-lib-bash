---
name: "{{AGENT_NAME}}-triad"
description: "EEI Triad orchestration for {{AGENT_NAME}}"
---

# EEI Triad Orchestration: {{AGENT_NAME}}

## Configuration

**Role Scope**: {{ROLE_SCOPE}} (the parent role this loop serves; `none` for a standalone triad)
**Task**: {{TASK_DESCRIPTION}}
**Threshold**: {{THRESHOLD}} (stop when weighted total exceeds this)
**Max Iterations**: {{MAX_ITERATIONS}} (default: 20)
**Max Consecutive Regressions**: {{MAX_REGRESSIONS}} (default: 3)
**Run Workspace**: `.specify/teams/.work/{{TEAM_SLUG}}/` (git-ignored) — per-iteration candidate outputs, scores, and scratch. Final deliverables (best iteration's output that the goal declares as the product) go to their declared target paths, not the workspace. On completion, write a dated run report to `.specify/teams/{{TEAM_SLUG}}/runs/`.

### Scoring Dimensions

{{SCORING_DIMENSIONS}}

> When invoked by a role supervisor (`{{ROLE_SCOPE}}` ≠ `none`), the executor's task and environment paths are bound to that role's domain, and `{{SCORING_DIMENSIONS}}` defaults to the role-default dimensions unless the user overrides them.

## Sub-Agent Definitions

> Type is judged by **operating object**, not derived from Stage (see `references/conceptual-model.md`). In this EEI triad: the executor acts on business artifacts → Worker; the evaluator's Type follows what it scores (business artifact → Worker; agent performance → Meta); the optimizer here tunes environment/prompts (agent-layer objects) → Meta.

### Executor (Stage: executor, Type: Worker)
- **Template**: agent-stage-executor-template.md
- **Environment Paths**: {{EXECUTOR_ENVIRONMENT_PATHS}}
- **Output Directory**: `.specify/teams/.work/{{TEAM_SLUG}}/` (run workspace for iteration artifacts; only declared final deliverables go to real target paths)

### Evaluator (Stage: evaluator, Type: judge by scored object)
- **Template**: agent-stage-evaluator-template.md
- **Artifacts**: [populated from executor output each iteration]
- **Dimensions**: [from Scoring Dimensions above]

### Optimizer (Stage: optimizer, Type: Meta — tunes environment/prompts)
- **Template**: agent-stage-optimizer-template.md
- **Workspace Paths**: {{OPTIMIZER_WORKSPACE_PATHS}}

## Orchestration Loop

For each iteration (1 to MAX_ITERATIONS):

### Step 1: Invoke Executor
- Spawn a NEW subagent using the Executor template
- Pass: task description + environment paths + iteration context
- Collect: output artifact paths

### Step 2: Invoke Evaluator
- Spawn a NEW subagent using the Evaluator template
- Pass: ONLY the artifact paths + scoring dimensions
- Collect: structured scores + suggestions

### Step 3: Check Threshold
- If weighted_total > threshold → STOP (success)
- If iteration = max_iterations → STOP (max reached, return best output)
- If consecutive_regressions >= max_regressions → STOP (regression limit)

### Step 4: Track History
- Record: round, scores, delta, changes
- Update best_output if this iteration scored higher

### Step 5: Invoke Optimizer (if continuing)
- Spawn a NEW subagent using the Optimizer template
- Pass: ONLY evaluator feedback + workspace paths + iteration history summary
- Collect: changes made (file edits + prompt suggestions)

### Step 6: Apply Adjustments
- Optimizer's file edits are already on disk
- Apply executor prompt adjustments to the next iteration's context

[Loop back to Step 1]

## Iteration History Table

| Round | {{DIMENSION_NAMES}} | Total | Delta | Key Changes |
|-------|---------------------|-------|-------|-------------|
| 1     | ...                 | ...   | -     | (initial)   |

## Final Report

After loop completes, report:
- **Outcome**: Converged / Max iterations reached / Regression limit
- **Best Score**: [highest weighted_total across all iterations]
- **Best Output**: [artifacts from best-scoring iteration]
- **Total Iterations**: [count]
- **Iteration History**: [the table above]
