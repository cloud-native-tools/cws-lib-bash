## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

**Mode detection from `$ARGUMENTS`:**
- If contains `--insert` or explicitly requests insertion → **Insertion Mode**
- Otherwise → **Collection Mode** (default)

## Collection Mode Workflow

### Step 1: Run Scanner

Execute `.specify/scripts/bash/search-todo.sh --json` from repo root. The script outputs JSON to stdout:

```json
{
  "repository": "<path>",
  "branch": "<branch>",
  "scanned_at": "<ISO timestamp>",
  "counters": {
    "total_files_scanned": <int>,
    "total_blocks_found": <int>,
    "malformed_blocks": <int>,
    "excluded_files_count": <int>
  },
  "blocks": [
    {
      "block_id": "<file>:<line>:<idx>",
      "source_file": "<relative path>",
      "opening_line": <int>,
      "closing_line": <int>,
      "content": "<block text>",
      "context_heading": "<nearest heading or null>",
      "prologue": "<text before block>",
      "epilogue": "<text after block>"
    }
  ],
  "malformed": [
    {
      "source_file": "<path>",
      "opening_line": <int>,
      "reason": "unclosed_fence|nested_fence",
      "content_snippet": "<first 120 chars>"
    }
  ],
  "excluded_files": ["<path>", ...]
}
```

### Step 2: Handle Edge Cases

- **Zero blocks found**: Report "No actionable SPECKIT TODO blocks found in workspace." and stop.
- **Malformed blocks**: Report each with source location and reason. Exclude ALL malformed blocks from execution planning.
- **Scanner exit code ≠ 0**: Report error and stop. Exit codes: 1=argument error, 2=repo root undefined, 3=I/O error.

### Step 3: Group and Organize Blocks

For each valid block, create a **work item** with:
1. **Source**: `source_file:opening_line` (link to origin)
2. **Context**: `context_heading` + `prologue` (why this TODO exists)
3. **Task**: Parse `content` to extract the actionable work description
4. **Scope**: Infer affected files/modules from content and context

Group work items by:
- Related source files or modules
- Common themes or dependencies
- Logical execution order

### Step 4: Batching (FR-013)

If `total_blocks_found > 10`:
- Split into batches of **at most 5 groups** per batch
- Present each batch sequentially
- Require explicit user confirmation before proceeding to next batch

### Step 5: Present Plan for Review

For each group/batch, present:

```
## Group N: <theme/module>

### Source Blocks
- <source_file>:<line> — "<context_heading>"

### Tasks
1. <concrete action with file path>
2. <concrete action with file path>
...

### Risk Notes
- <any safety concerns from content analysis>
```

### Step 6: Execute on Confirmation

After user confirms a batch:
1. Execute tasks in the presented order
2. After each task, verify the change is correct
3. Report completion status per task
4. If a task fails, stop and report — do NOT continue to subsequent tasks

If `$ARGUMENTS` contains background context, apply it as constraints when interpreting block content and generating task descriptions.

## Insertion Mode Workflow

Triggered when `$ARGUMENTS` contains `--insert` or explicitly requests TODO insertion.

### Step 1: Parse Insertion Request

Extract from `$ARGUMENTS`:
- **Target file**: The file path where the block should be inserted
- **Location**: Line number, section heading, or position description (e.g., "after imports", "end of file")
- **Content**: The TODO description text to place inside the block

### Step 2: Validate Target

1. Verify target file **exists** — if not, report error and STOP (do NOT create files)
2. Verify target file is **writable** — if not, report error and STOP
3. Verify location is valid (line number in range, or section heading exists)

### Step 3: Insert Block

Insert a conforming SPECKIT TODO block at the specified location:

````markdown
```SPECKIT TODO
<content from user>
```
````

Rules:
- Preserve ALL surrounding file content unchanged
- Add a blank line before and after the block if not already present
- Do NOT modify any content outside the inserted block

### Step 4: Confirm

Report:
- File modified: `<path>`
- Block inserted at: line `<N>`
- Block content preview

## Safety Rules

1. **Destructive content veto**: If a TODO block's content requests destructive operations (rm -rf, DROP TABLE, force push, secret exposure), REJECT it from execution planning and report the safety concern.
2. **Out-of-scope veto**: If a TODO block requests actions clearly outside the current project scope, flag it for manual review.
3. **Malformed exclusion**: Never execute or plan around malformed blocks — only report their locations.
4. **Bounded changes**: Each executed task should produce a small, reviewable change. Never batch large refactors into a single execution step.
5. **No file creation in insertion mode**: The `--insert` mode MUST NOT create new files.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this command reached its wrap-up stage. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against `/speckit.todo`'s declared purpose and produce a short review plus ≥1 concrete, command-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this command's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id` (e.g. the feature key + a run timestamp); if a nested skill/command already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "/speckit.todo" --unit-type command \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before running this command**:
- Embed `SPECKIT TODO` blocks in your project files where work is needed.

**After running this command**:
- Run `/speckit.implement` to execute generated plans if they align with a feature spec.
- Run `/speckit.review` to validate execution results.