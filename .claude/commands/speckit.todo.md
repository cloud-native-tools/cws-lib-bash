<!-- AUTO-GENERATED from templates/commands/todo.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

**Mode detection from `$ARGUMENTS`:**
- If empty, or contains `--list` → **List Mode** (default: enumerate everything, execute nothing)
- If contains `--insert` or explicitly requests insertion → **Insertion Mode**
- If contains `--park`, or the input is a free-floating idea/request with no tie to existing `SPECKIT TODO` blocks or current code (e.g. "park this idea", "暂存一个想法", a design thought raised mid-session) → **Park Mode**
- If contains `--collect`, or explicitly requests scanning/planning/executing the TODO blocks (e.g. "run the todos", "执行待办") → **Collection Mode**
- **Ambiguity rule**: when the input could plausibly be either a free-floating idea (Park) or a block-execution request (Collection) and no flag settles it, ask the user which mode applies — do NOT default to running the scanner against a non-block request.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection; non-conflicting new terms MUST be written directly and merged into the wrap-up report (non-blocking); only writes that conflict with or overwrite an existing user entry MUST still pause for user confirmation. User-authored entries are authoritative.

## List Mode Workflow

Triggered when `$ARGUMENTS` is empty or contains `--list`. Read-only: enumerate every TODO item — workspace `SPECKIT TODO` blocks **and** parked ideas — then stop. No planning, no execution, no writes.

### Step 1: Scanner Digest

Run `.specify/scripts/python/search-todo.py --json` and consume summary-first (see Step 1 of Collection Mode): only `counters`, `malformed`, and a per-block projection — `source_file`, `opening_line`, `context_heading`, plus the **first line** of `content`. Do NOT open full `content`/`prologue`/`epilogue` in this mode.

### Step 2: Parked Store Projection

For each `.specify/memory/todo/*.md`, extract frontmatter fields only (`title`, `status`, `parked_at`, `tags`) — never the body; open a body only if the user explicitly asks about that idea afterwards.

### Step 3: Report

Present two tables, then counts:

```
## Workspace TODO Blocks (<N>)
| # | Source | Context | First line |
|---|--------|---------|-----------|
| 1 | <file>:<line> | <context_heading or -> | <first line of content> |

## Parked Ideas (<M>)
| Title | Status | Parked | Tags | File |
|-------|--------|--------|------|------|
| <title> | parked/promoted/dropped | <date> | <tags> | <relative path> |
```

- Report malformed blocks (location + reason) separately; they are never listed as actionable.
- Zero blocks AND zero parked ideas → report "No TODO items found." and stop.
- Close with the handoffs: planning/executing blocks → re-run with `--collect`; reading a parked idea's body → ask by title; parking a new idea → `--park`.

## Collection Mode Workflow

### Step 1: Run Scanner

Execute `.specify/scripts/python/search-todo.py --json` from repo root. The script outputs JSON to stdout:

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

**Consume scanner output summary-first** (see `.specify/shared/guidelines/token-efficiency.md`): the JSON is machine-managed data — do NOT inject it wholesale into context. First consume `counters` + `malformed` + a projected digest (e.g. `jq '{counters, malformed, blocks: [.blocks[] | {block_id, source_file, opening_line, context_heading}]}'`); open a block's full `content`/`prologue`/`epilogue` only for the group you are actively planning in Step 3–5.

### Step 2: Handle Edge Cases

- **Zero blocks found**: Report "No actionable SPECKIT TODO blocks found in workspace." and stop.
- **Malformed blocks**: Report each with source location and reason. Exclude ALL malformed blocks from execution planning.
- **Scanner exit code ≠ 0**: Report error and stop. Exit codes: 1=argument error, 2=repo root undefined, 3=I/O error.

### Step 3: Group and Organize Blocks

**Recall prior memory first** (native `memory-recall` skill): search `.specify/memory/session/` and `.specify/memory/knowledge/` for prior TODO-run outcomes and durable preferences (suggested queries: `todo`, `convention`, `preference`, `decision`, `veto`), and list `.specify/memory/todo/` for parked ideas whose theme matches the current blocks. Apply recalled entries as non-derivable inputs below — e.g. a recorded user veto or deferral of a recurring block, a preferred grouping/batching convention, or a standing scope constraint. When a block clearly implements a parked idea, mark the parked record `promoted` (see Park Mode Step 4). Never contradict a recalled user decision — pause and ask the user first (user-decision protection, kept).

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
- Execute batches sequentially and automatically; present a per-batch completion report before starting the next batch (用户可在批间叫停,不设阻塞确认)——批次是用户明确请求执行的 TODO 计划,git 提供可逆性

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

### Step 6: Execute

For each batch (auto-executed after its presentation):
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

### Step 4: Report

Report (执行报告:内容、产出、修改途径):
- File modified: `<path>`
- Block inserted at: line `<N>`
- Block content preview

## Park Mode Workflow

Triggered by `--park`, or when `$ARGUMENTS` is a free-floating idea with no tie to existing TODO blocks or current code — an idea worth remembering but not yet worth a spec, a TODO block, or any code change. Parking is **capture, not commitment**: the idea is stored verbatim in its raw form and left to mature with the project.

### Step 1: Parse the Idea

Extract from `$ARGUMENTS`:
- **Title**: a short slug-worthy name (2–6 words)
- **Body**: the idea as stated — preserve the user's wording; do NOT rewrite it into a design or a task list
- **Context (optional)**: where/why it surfaced (command, session, preceding discussion)

### Step 2: Write the Parked Record

Store location: `.specify/memory/todo/` (create the directory if absent — this is the ONE file-creation Park Mode permits). One file per idea:

```markdown
---
title: <short title>
status: parked            # parked | promoted | dropped
parked_at: <YYYY-MM-DD>
origin: <command/session where it surfaced, e.g. "/speckit.todo during 038-goal-target">
tags: [<topic>, ...]
---

<body — the idea as stated by the user>

## Evolution Log

- <YYYY-MM-DD> parked.
```

Rules:
- File name: `<YYYYMMDD>-<slug>.md`, date = park date
- Never overwrite an existing parked record; a re-parked variant gets its own file cross-referencing the original
- Do NOT touch any other file, do NOT insert TODO blocks, do NOT start specs or code changes

### Step 3: Report

Report the record path, title, and a one-line preview of the body (执行报告:内容、产出、修改途径). State explicitly that the idea is parked, not scheduled.

### Step 4: Lifecycle Transitions (later runs)

- **Promote**: when a parked idea becomes actionable — it turns into a `SPECKIT TODO` block (`--insert`), a requirement spec (`/speckit.requirements`), or an executed task — set `status: promoted` and append an Evolution Log line citing the destination.
- **Retire after merge**: once a promoted item's destination has actually landed (code/doc committed), the parked file MAY be deleted — the merge site is the record of truth, and keeping the original input after merge is data redundancy. Deletion requires a verifiable destination record; before the merge lands, the file stays.
- **Drop**: on explicit user veto, set `status: dropped` with a reason line. Never delete a parked/dropped/pre-merge file silently — the park store is an append-only history of considered ideas until an item retires per the rule above.

## Safety Rules

1. **Destructive content veto**: If a TODO block's content requests destructive operations (rm -rf, DROP TABLE, force push, secret exposure), REJECT it from execution planning and report the safety concern.
2. **Out-of-scope veto**: If a TODO block requests actions clearly outside the current project scope, flag it for manual review.
3. **Malformed exclusion**: Never execute or plan around malformed blocks — only report their locations.
4. **Bounded changes**: Each executed task should produce a small, reviewable change. Never batch large refactors into a single execution step.
5. **No file creation in insertion mode**: The `--insert` mode MUST NOT create new files.
6. **Park writes stay in the store**: Park Mode creates files ONLY under `.specify/memory/todo/` and modifies only its own parked records — never source code, specs, or other memory layers.

## Optional: Git Commit

After execution, offer to commit the changes using `.specify/templates/commit-template.md`:
- Collect: BRANCH, TYPE (`feat`/`fix`/`chore` per block content), SCOPE, SUBJECT
- Display `git add -A && git commit -m "{msg}"` — only execute on explicit user approval

## Memory Record

At wrap-up, invoke the native `memory-record` skill (skip for trivial no-op runs — zero blocks found, or a pure insertion with no decisions):

- **Session scope**: persist a working note of this run's outcome (blocks executed / deferred / vetoed and why, batches confirmed) so the next `/speckit.todo` run recalls what was already handled and avoids re-proposing it.
- **Knowledge scope**: when the run surfaced a durable user preference, veto rule, or grouping/batching convention, upsert it as long-term knowledge so future runs apply it at Step 3.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.todo" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before running this command**:
- Embed `SPECKIT TODO` blocks in your project files where work is needed.
- Or raise a free-floating idea (`--park` or a plain description) to store it in `.specify/memory/todo/` without committing to it.
- Invoke `memory-recall` to surface prior TODO-run outcomes and conventions (Step 3 does this by default).

**After running this command**:
- Run `/speckit.implement` to execute generated plans if they align with a feature spec.
- Run `/speckit.review` to validate execution results.
- Promote a parked idea when it becomes actionable: `--insert` it as a TODO block or route it through `/speckit.requirements`.
- Invoke `memory-record` to persist durable decisions and conventions (the Memory Record step does this by default).