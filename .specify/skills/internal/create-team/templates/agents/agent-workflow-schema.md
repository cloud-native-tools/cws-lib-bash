# Agent Workflow Schema

Defines the declarative data model for multi-agent serial workflows (DAG-based stage pipelines).

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentWorkflow",
  "description": "Declarative DAG data model for multi-agent serial chain orchestration",
  "type": "object",
  "required": ["workflow_id", "name", "stages", "handoff_protocol", "progress_file"],
  "properties": {
    "workflow_id": {
      "type": "string",
      "description": "Unique workflow identifier (kebab-case, e.g. 'feature-auth-impl')"
    },
    "name": {
      "type": "string",
      "description": "Human-readable workflow name"
    },
    "stages": {
      "type": "array",
      "minItems": 2,
      "items": {
        "type": "object",
        "required": ["stage_id", "agent_kind", "task", "outputs"],
        "properties": {
          "stage_id": {
            "type": "string",
            "description": "Unique stage identifier within the workflow"
          },
          "agent_kind": {
            "type": "string",
            "description": "Agent role type to invoke (e.g. requirements-analyst, system-designer)"
          },
          "task": {
            "type": "string",
            "description": "Task description for this stage"
          },
          "inputs_from": {
            "type": "array",
            "items": { "type": "string" },
            "default": [],
            "description": "Upstream stage IDs whose outputs feed into this stage"
          },
          "outputs": {
            "type": "array",
            "items": { "type": "string" },
            "description": "File paths this stage will produce. Intermediate (non-terminal) handoff files MUST live under the git-ignored run workspace `.specify/teams/.work/<slug>/`; only the terminal stage's final deliverables (standard output) use real project target paths."
          },
          "blockedBy": {
            "type": "array",
            "items": { "type": "string" },
            "default": [],
            "description": "Stage IDs that must complete before this stage can start"
          },
          "quality_gate": {
            "type": "string",
            "description": "Optional quality gate condition (LLM evaluates pass/fail)"
          }
        }
      }
    },
    "handoff_protocol": {
      "type": "string",
      "enum": ["file-path-only"],
      "description": "Inter-stage data transfer protocol. 'file-path-only' = pass paths, not content"
    },
    "progress_file": {
      "type": "string",
      "description": "Path to the workflow progress tracking file; a run intermediate — MUST live under `.specify/teams/.work/<slug>/`"
    }
  }
}
```

## DAG Constraints

1. **No circular dependencies**: The `blockedBy` graph must be a DAG (directed acyclic graph). Validate via topological sort before execution.
2. **Unique stage IDs**: Every `stage_id` must be unique within a workflow.
3. **Valid references**: All IDs in `blockedBy` and `inputs_from` must reference existing `stage_id` values.
4. **At least one root**: At least one stage must have an empty `blockedBy` array (entry point).

## Example Workflows

### Example 1: Requirements → Design → Implementation

```json
{
  "workflow_id": "feature-user-auth",
  "name": "User Authentication Feature Pipeline",
  "stages": [
    {
      "stage_id": "requirements",
      "agent_kind": "requirements-analyst",
      "task": "Analyze user stories and produce a requirements spec for authentication",
      "inputs_from": [],
      "outputs": [".specify/teams/.work/feature-user-auth/requirements.md"],
      "blockedBy": []
    },
    {
      "stage_id": "design",
      "agent_kind": "system-designer",
      "task": "Design system architecture based on requirements",
      "inputs_from": ["requirements"],
      "outputs": [".specify/teams/.work/feature-user-auth/design.md"],
      "blockedBy": ["requirements"],
      "quality_gate": "Design covers all requirements and has no unresolved trade-offs"
    },
    {
      "stage_id": "implementation",
      "agent_kind": "module-designer",
      "task": "Implement modules per the system design",
      "inputs_from": ["design"],
      "outputs": ["src/auth/"],
      "blockedBy": ["design"]
    }
  ],
  "handoff_protocol": "file-path-only",
  "progress_file": ".specify/teams/.work/feature-user-auth/progress.md"
}
```

### Example 2: Spec → Review → Apply

```json
{
  "workflow_id": "spec-review-apply",
  "name": "Specification Review and Application",
  "stages": [
    {
      "stage_id": "draft-spec",
      "agent_kind": "requirements-analyst",
      "task": "Draft the feature specification from user intent",
      "inputs_from": [],
      "outputs": [".specify/teams/.work/spec-review-apply/draft-feature.md"],
      "blockedBy": []
    },
    {
      "stage_id": "review",
      "agent_kind": "qa-engineer",
      "task": "Review spec for completeness, consistency, and testability",
      "inputs_from": ["draft-spec"],
      "outputs": [".specify/teams/.work/spec-review-apply/feature-review.md"],
      "blockedBy": ["draft-spec"],
      "quality_gate": "No critical issues remain unresolved"
    },
    {
      "stage_id": "apply",
      "agent_kind": "module-designer",
      "task": "Apply reviewed spec into implementation code",
      "inputs_from": ["draft-spec", "review"],
      "outputs": ["src/feature/"],
      "blockedBy": ["review"]
    }
  ],
  "handoff_protocol": "file-path-only",
  "progress_file": ".specify/teams/.work/spec-review-apply/progress.md"
}
```

### Example 3: Analysis → Test Plan → Test Implementation

```json
{
  "workflow_id": "test-coverage-pipeline",
  "name": "Test Coverage Improvement Pipeline",
  "stages": [
    {
      "stage_id": "analyze",
      "agent_kind": "qa-engineer",
      "task": "Analyze current test coverage gaps",
      "inputs_from": [],
      "outputs": [".specify/teams/.work/test-coverage-pipeline/coverage-gaps.md"],
      "blockedBy": []
    },
    {
      "stage_id": "plan-tests",
      "agent_kind": "test-engineer",
      "task": "Create test plan addressing coverage gaps",
      "inputs_from": ["analyze"],
      "outputs": [".specify/teams/.work/test-coverage-pipeline/test-plan.md"],
      "blockedBy": ["analyze"]
    },
    {
      "stage_id": "write-tests",
      "agent_kind": "test-engineer",
      "task": "Implement test cases per the test plan",
      "inputs_from": ["plan-tests"],
      "outputs": ["tests/"],
      "blockedBy": ["plan-tests"],
      "quality_gate": "All planned test cases are implemented and pass"
    }
  ],
  "handoff_protocol": "file-path-only",
  "progress_file": ".specify/teams/.work/test-coverage-pipeline/progress.md"
}
```
