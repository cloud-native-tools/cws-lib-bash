---
name: "{{WORKFLOW_NAME}}"
description: "Serial chain orchestration for {{WORKFLOW_NAME}}"
---

# Serial Chain Orchestration: {{WORKFLOW_NAME}}

> **Model alignment**: this is a **serial Loop** in the Role/Stage/Type model. Each stage agent is a **Worker** running at the `executor` stage; the **Lead** (optional quality gate between stages) is the **Team Supervisor** (Meta role).

## Configuration

**Workflow ID**: {{WORKFLOW_ID}}
**Total Stages**: {{STAGE_COUNT}}
**Handoff Protocol**: file-path-only
**Failure Strategy**: {{FAILURE_STRATEGY}}
**Progress File**: {{PROGRESS_FILE}}

## Stage Definitions

{{STAGE_TABLE}}

> Format: | Stage ID | Agent Kind | Task | Inputs From | Outputs | Blocked By | Quality Gate |

## Orchestration Flow

For each stage in topological order, execute the following 6-step cycle:

### Step 1: Check blockedBy Dependencies

- Read the progress file at `{{PROGRESS_FILE}}`
- For the current stage, verify ALL stages listed in `blockedBy` have status = `completed`
- If any dependency is not completed → WAIT (do not proceed)
- If all dependencies are satisfied → proceed to Step 2

### Step 2: Build Stage Context (Upstream Outputs)

- Collect output file paths from all stages listed in `inputs_from`
- Format as a file-path list (do NOT read or paste file content):

```
Input artifacts for stage [current_stage_id]:
- [path] (from: [upstream_stage_id])
- [path] (from: [upstream_stage_id])
```

- This list becomes the downstream agent's input context

### Step 3: Invoke Stage Agent (Spawn Subagent)

- Spawn a NEW subagent with the role matching `agent_kind`
- Provide the agent with:
  - The stage `task` description
  - The input artifact paths from Step 2
  - The required `outputs` paths to write to
- Do NOT provide file content — the agent reads files itself

### Step 4: Validate Stage Output (Quality Gate)

- Verify all declared `outputs` files exist and are non-empty
- If `quality_gate` is defined:
  - Evaluate the condition (LLM judgment on output quality)
  - If PASS → proceed to Step 5
  - If FAIL → apply failure strategy ({{FAILURE_STRATEGY}})
- If no quality gate → proceed to Step 5

### Step 5: Record Completion + Update Progress

- Update the progress file with:
  - Stage status → `completed`
  - Completion timestamp
  - Actual output paths
- Append to Handoff Log:
  - `[timestamp] [stage_id] → [next_stage]: Passed [output_paths]`

### Step 6: Unlock Downstream Stages

- Identify all stages that list the current stage in their `blockedBy`
- These stages may now be eligible for execution (if all their other dependencies are also met)
- Move to the next stage in topological order

[Loop back to Step 1 for next stage]

## Handoff Protocol

| Rule | Description |
|------|-------------|
| **Write convention** | Each agent writes outputs to its declared `outputs[]` paths |
| **Path-only transfer** | Downstream agents receive ONLY file paths, never content |
| **Existence check** | Lead verifies files exist + non-empty before unlocking next stage |
| **No upstream mutation** | Downstream agents MUST NOT modify upstream artifacts |

## Progress Tracking

| Stage | Agent | Status | Started | Completed | Output Path |
|-------|-------|--------|---------|-----------|-------------|
| {{STAGE_ROWS}} |

## Handoff Log

```
[timestamp] stage_a → stage_b: Passed [output_paths]
```

## Failure Recovery

**Active Strategy**: {{FAILURE_STRATEGY}}

| Condition | Action |
|-----------|--------|
| Output files missing | Retry stage (max 2 attempts) |
| Quality gate failed (minor) | Invoke `improve-agent` on output |
| Quality gate failed (critical) | Halt workflow, report to user |
| Agent error/crash | Retry stage (max 2 attempts) |
| User requests skip | Mark stage as skipped, continue |

## Final Report

After all stages complete (or workflow halts), report:

- **Workflow**: {{WORKFLOW_NAME}} (`{{WORKFLOW_ID}}`)
- **Outcome**: Completed / Halted at stage [X] / Partially completed
- **Stages Completed**: [N] / {{STAGE_COUNT}}
- **Total Duration**: [start → end]
- **Artifacts Produced**:
  - [List all output paths from completed stages]
- **Issues Encountered**:
  - [Any retries, quality gate failures, or skipped stages]
- **Next Steps**:
  - [Recommendations if workflow halted or partially completed]
