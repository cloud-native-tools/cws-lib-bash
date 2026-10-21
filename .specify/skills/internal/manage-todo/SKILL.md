---
name: manage-todo
description: Manage the workspace's SPECKIT TODO surface — list every TODO item (workspace `SPECKIT TODO` blocks + parked ideas), scan blocks into reviewable grouped execution plans and execute them with in-step block removal, insert new TODO blocks at the exact code or document location they refer to, and park free-floating ideas into the `.specify/memory/todo/` idea store. This is the executable core of `/speckit.todo`, running four modes (List / Collection / Insertion / Park) over one scanner engine with summary-first digest consumption, context-completed interpretation, FR-013 batch discipline, and a six-rule safety veto set. Use this when the user mentions ["todo", "TODO blocks", "待办", "TODO 管家", "run the todos", "执行待办", "list todos", "列出待办", "scan todos", "扫描 TODO 块", "insert todo", "插入 TODO", "park this idea", "寄存想法", "暂存一个想法", "parked ideas", "SPECKIT TODO", "--collect", "--insert", "--park"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-todo/SKILL.md>"
---

# manage-todo

## Goal

Own and execute the operations behind `/speckit.todo` — the TODO butler surface: enumerate
the workspace's TODO items, turn scattered `SPECKIT TODO` blocks into reviewed and batched
work, execute it, insert conforming blocks, and park ideas worth remembering but not yet
worth a spec, a TODO block, or any code change. List Mode is strictly read-only; Park Mode
writes only into the park store; Insertion Mode never creates files.

The **concept** — what a `SPECKIT TODO` block is (form ownership, fence vs comment,
context-completed interpretation, perception obligations of passing workflows, lifecycle) —
is owned by `.specify/shared/guidelines/todo-in-context.md`. **Link to it; never restate
its rules.**

Scanner engine: the command frontmatter `scripts:` block resolves `{SCRIPT}` to
`.specify/scripts/python/search-todo.py --json`; run it from repo root. Its JSON output contract is
fixed in Collection Mode Step 1 — consume it summary-first, never wholesale
(`.specify/shared/guidelines/token-efficiency.md`).

**Memory face (existing delegation)**: the two memory touchpoints in this workflow — the
pre-collection recall (Collection Step 3) and the wrap-up record (§ Memory Record) — are
existing delegations to the native `memory-recall` / `memory-record` skills. This skill
invokes them; it does not absorb their logic.

Canonical extraction source: `.specify/templates/commands/todo.md` § List/Collection/Insertion/Park
Mode Workflows, § Safety Rules, § Optional: Git Commit, and § Memory Record. Content moved
here verbatim in substance; the command template keeps entry, user-input handling, the
glossary pre-step, the Philosophy pointer, and wrap-up lifecycle steps only.

## Input Contract

`$ARGUMENTS` below denotes the request arguments the command captured (entry handling and
the User Input Protocol stay in the command template).

**Mode detection from `$ARGUMENTS`:**
- If empty, or contains `--list` → **List Mode** (default: enumerate everything, execute nothing)
- If contains `--insert` or explicitly requests insertion → **Insertion Mode**
- If contains `--park`, or the input is a free-floating idea/request with no tie to existing `SPECKIT TODO` blocks or current code (e.g. "park this idea", "暂存一个想法", a design thought raised mid-session) → **Park Mode**
- If contains `--collect`, or explicitly requests scanning/planning/executing the TODO blocks (e.g. "run the todos", "执行待办") → **Collection Mode**
- **Ambiguity rule**: when the input could plausibly be either a free-floating idea (Park) or a block-execution request (Collection) and no flag settles it, ask the user which mode applies — do NOT default to running the scanner against a non-block request.

## List Mode Workflow

Triggered when `$ARGUMENTS` is empty or contains `--list`. Read-only: enumerate every TODO item — workspace `SPECKIT TODO` blocks **and** parked ideas — then stop. No planning, no execution, no writes.

### Step 1: Scanner Digest

Run `{SCRIPT}` and consume summary-first (see Step 1 of Collection Mode): only `counters`, `malformed`, and a per-block projection — `source_file`, `opening_line`, `context_heading`, plus the **first line** of `content`. Do NOT open full `content`/`prologue`/`epilogue` in this mode.

### Step 2: Parked Store Projection

For each `.specify/memory/todo/*.md`, extract frontmatter fields only (`title`, `status`, `parked_at`, `tags`) — never the body; open a body only if the user explicitly asks about that idea afterwards.

### Step 3: Report

Present two tables, then counts:

```
## Workspace TODO Blocks (<N>)
| # | Source | Form | Context | First line |
|---|--------|------|---------|-----------|
| 1 | <file>:<line> | fence/comment | <context_heading or -> | <first line of content> |

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

Execute `{SCRIPT}` from repo root. The script outputs JSON to stdout:

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

**Recall prior memory first** (native `memory-recall` skill, `.specify/skills/internal/memory-recall/SKILL.md`): search `.specify/memory/session/` and `.specify/memory/knowledge/` for prior TODO-run outcomes and durable preferences (suggested queries: `todo`, `convention`, `preference`, `decision`, `veto`), and list `.specify/memory/todo/` for parked ideas whose theme matches the current blocks. Apply recalled entries as non-derivable inputs below — e.g. a recorded user veto or deferral of a recurring block, a preferred grouping/batching convention, or a standing scope constraint. When a block clearly implements a parked idea, mark the parked record `promoted` (see Park Mode Step 4). Never contradict a recalled user decision — pause and ask the user first (user-decision protection, kept).

For each valid block, create a **work item** with:
1. **Source**: `source_file:opening_line` (link to origin)
2. **Context**: `context_heading` + `prologue` (why this TODO exists)
3. **Task**: Parse `content` to extract the actionable work description
4. **Scope**: Infer affected files/modules from content and context

**Context completion (上下文补全)**: block content states a short intent; the context around it completes the reading. When the content alone is terse or admits more than one reading, resolve it FIRST from the block's context — `prologue`/`epilogue` (adjacent code, comments, statements), `context_heading`, and the source file's surrounding structure (per `.specify/shared/guidelines/todo-in-context.md`). Only when two readings survive the context does the run stop and ask the user which one applies — never guess between them.

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
3. Remove the completed TODO block from its source file in the same step: delete the whole block (both fence lines for fence form; the full comment run for comment form) plus the blank line the insertion rules added, preserving all other content. The landed change plus git history is the record — a stale marker would send the next run re-planning finished work (lifecycle: `.specify/shared/guidelines/todo-in-context.md`)
4. Report completion status per task
5. If a task fails, stop and report — do NOT continue to subsequent tasks, and do NOT remove the block of a failed or unverified task

If `$ARGUMENTS` contains background context, apply it as constraints when interpreting block content and generating task descriptions.

> **Fast Fail 实例指针**:本文件中"即停 / 即中止 / 不得静默降级"一类规则是快速失败纪律的既有**实例**;其判据与两份清单的唯一真源是 `.specify/shared/guidelines/fast-fail.md`(本文件引用它,MUST NOT 复述它)。

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

Insert a conforming SPECKIT TODO block at the specified location, choosing the form by target file type (per `.specify/shared/guidelines/todo-in-context.md`):

- **Markdown-family target** (`.md`, `.markdown`, `.mdown`, `.mkd`, `.mdx`) — fenced form:

````markdown
```SPECKIT TODO
<content from user>
```
````

- **Source code target** (any other file) — comment form using that language's line-comment token (`#`, `//`, `--`); NEVER insert a fenced block into a source file — a fence is a syntax error there:

```text
# SPECKIT TODO
# <content from user>
```

**Placement (就位原则)**: the block MUST sit at the exact code or document element it refers to — above the function/statement/module it concerns, or inside the section it concerns — never dumped at file head or tail. When `$ARGUMENTS` does not pin the location, derive it from what the TODO is about.

**Content (内容原则)**: a short intent statement is enough — surrounding context completes it. Do not pad the block with details the location already shows.

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

## Memory Record (delegated)

At wrap-up, invoke the native `memory-record` skill (`.specify/skills/internal/memory-record/SKILL.md`; skip for trivial no-op runs — zero blocks found, or a pure insertion with no decisions):

- **Session scope**: persist a working note of this run's outcome (blocks executed / deferred / vetoed and why, batches confirmed) so the next `/speckit.todo` run recalls what was already handled and avoids re-proposing it.
- **Knowledge scope**: when the run surfaced a durable user preference, veto rule, or grouping/batching convention, upsert it as long-term knowledge so future runs apply it at Collection Step 3.

## Command-lifecycle surfaces (kept in `/speckit.todo`)

Entry argument handling (`$ARGUMENTS` per `.specify/shared/workflow/user-input-protocol.md`), the glossary pre-step (`.specify/memory/glossary.md`, protocol `.specify/shared/workflow/glossary.md`), the Philosophy section (a pointer to `.specify/shared/guidelines/todo-in-context.md`), the `## Feedback` / `## Documentation` steps (docs-sync evaluation per `.specify/shared/workflow/docs-step.md`, escalation target `/speckit.docs`), and the Handoffs (implement/review routing via `/speckit.implement` / `/speckit.review`) stay in the command template — they are command lifecycle, not TODO operations.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-todo" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-todo" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-todo" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
