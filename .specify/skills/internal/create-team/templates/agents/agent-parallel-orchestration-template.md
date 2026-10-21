---
name: "{{PROJECT_NAME}}-parallel-orchestration"
description: "Parallel multi-agent orchestration for {{PROJECT_NAME}}"
---

# Parallel Agent Orchestration: {{PROJECT_NAME}}

> **Model alignment**: this is a **parallel Loop** in the Role/Stage/Type model. The **Lead** is the **Team Supervisor** (Meta role — coordination + quality gate, formerly split as Meta-Coordinator). Each dispatched agent is a **Worker** running at the `executor` stage.

## Configuration

**Parallel Count**: {{PARALLEL_COUNT}} (number of agents to dispatch)
**Max Concurrency**: {{MAX_CONCURRENCY}} (default: 4)
**Aggregation Strategy**: {{AGGREGATION_STRATEGY}} (merge | report-only | sequential-merge)
**Timeout Per Agent**: {{AGENT_TIMEOUT}} (default: 300s)
**Run Workspace**: `.specify/teams/.work/{{TEAM_SLUG}}/` (git-ignored) — holds all status manifests and intermediate files. Final deliverables go to their declared target paths (real project paths), never the workspace.

### Territory Rules

{{TERRITORY_RULES}}

> Territory validation is deterministic: if any agent's Write Scope overlaps with another's, dispatch MUST be aborted until the conflict is resolved.

### Forbidden Write List (Lead-Only Files)

{{FORBIDDEN_WRITE_LIST}}

## Agent Assignments

| Agent ID | Task Brief | Write Scope | Read Scope | Model Tier |
|----------|-----------|-------------|------------|------------|
| {{AGENT_1_ID}} | {{AGENT_1_TASK}} | {{AGENT_1_WRITE}} | {{AGENT_1_READ}} | {{AGENT_1_MODEL}} |
| {{AGENT_2_ID}} | {{AGENT_2_TASK}} | {{AGENT_2_WRITE}} | {{AGENT_2_READ}} | {{AGENT_2_MODEL}} |
| {{AGENT_N_ID}} | {{AGENT_N_TASK}} | {{AGENT_N_WRITE}} | {{AGENT_N_READ}} | {{AGENT_N_MODEL}} |

## Orchestration Flow

### Step 1: Territory Validation (Deterministic Check)

Before any dispatch, verify:

- [ ] All Write Scopes are mutually exclusive (zero overlap)
- [ ] Forbidden Write List covers all shared files
- [ ] Each agent has non-empty Write Scope
- [ ] No file appears in both a Write Scope and the Forbidden Write List simultaneously

**If validation fails**: ABORT. Report conflicting territories and ask the Lead to re-partition.

### Step 2: Context Isolation

For each agent, prepare an isolated payload:

```
Payload for Agent <ID>:
  task_brief: <one-paragraph task>
  write_scope: [files/dirs agent may modify]
  read_scope: [files/dirs agent may read]
  forbidden_files: [files agent MUST NOT touch]
  output_manifest: .specify/teams/.work/{{TEAM_SLUG}}/parallel-result-<agent-id>.md
```

**Rule**: NO conversation history, NO other agents' tasks, NO shared mutable references.

### Step 3: Parallel Dispatch

Issue ALL agent calls in a **single response block**:

- Agent {{AGENT_1_ID}} → task + territory
- Agent {{AGENT_2_ID}} → task + territory
- Agent {{AGENT_N_ID}} → task + territory

**Key**: Multiple sub-agent invocations in one response = parallel execution.

**Worktree isolation** (when the team config sets `isolation: worktree`): dispatch each *writing* agent with worktree isolation so it works on its own branch in a physically separate tree; read-only agents dispatch normally. After completion, the Lead reviews each branch diff and merges sequentially — a merge conflict means territory validation was wrong (stop and repartition, do not resolve ad hoc). Never remove a worktree that still has uncommitted changes.

### Step 4: Completion Monitoring

Poll for completion manifests at each agent's declared output path in the run workspace:

```
.specify/teams/.work/{{TEAM_SLUG}}/parallel-result-<agent-id>.md
```

Monitor for:
- **Completion**: Manifest exists with `status: done`
- **Stall**: No manifest update after {{STALL_THRESHOLD}} (default: 120s)
- **Failure**: Manifest exists with `status: error`

### Step 5: Conflict Detection & Resolution

After all agents complete, run deterministic checks:

| Check | Rule | Action on Fail |
|-------|------|----------------|
| Territory Integrity | No agent wrote outside its Write Scope | Reject violating writes |
| Output Completeness | All declared deliverables exist | Flag missing items |
| Contradiction Scan | No conflicting recommendations for same concern | Trigger Lead review |

**Resolution protocol**: Present conflicts to Lead for LLM-judgment resolution.

### Step 6: Result Aggregation & Final Report

Merge all agent outputs per the configured aggregation strategy:

- **merge**: Combine all outputs into unified deliverable
- **report-only**: Collect outputs without merging; present as individual results
- **sequential-merge**: Merge in agent-ID order, later agents override on conflict

## Model Selection Guidance

| Sub-task Nature | Model Tier | Rationale |
|-----------------|-----------|-----------|
| Mechanical / Deterministic | Light | Single correct answer; no judgment needed |
| Analytical / Evaluative | Standard | Tradeoff weighing; moderate reasoning |
| Creative / Architectural | Heavy | Novel synthesis; deep reasoning required |

## Result Template

### Per-Agent Status

| Agent ID | Status | Duration | Output Path | Conflicts |
|----------|--------|----------|-------------|-----------|
| {{AGENT_1_ID}} | pending | — | — | — |
| {{AGENT_2_ID}} | pending | — | — | — |
| {{AGENT_N_ID}} | pending | — | — | — |

### Aggregated Report

```markdown
# Parallel Execution Report

## Dispatch Summary
- Total Agents: {{PARALLEL_COUNT}}
- Completed: <count>
- Failed: <count>
- Conflicts Detected: <count>

## Deliverables
[List of final output paths]

## Conflict Resolutions
[How contradictions were resolved, if any]

## Lead Post-Processing
[Changes to Forbidden Write List files made by Lead]
```
