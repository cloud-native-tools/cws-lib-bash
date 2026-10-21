---
description: 工具记录操作统一入口：定义、修改、查看或调用 Tool
---
<!-- AUTO-GENERATED from templates/commands/tools.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). If empty, execute the **Default Behavior (No Arguments)** defined below. If non-empty but intent is ambiguous or unsupported, report capabilities and request the missing intent (do NOT guess silently). If a `tool_id` and a natural-language hint conflict, stop and request correction.

## Outline

`/speckit.tools` is the **single entry point** for every **tool** operation — the tool-domain analogue of `/speckit.agents` and `/speckit.team`. It recognizes intent, then routes to the owning tool skill. It delegates to skills and does **NOT** render templates inline.

A **tool** is a named, pre-verified, reusable **definition of one concrete capability** — persisted at `.specify/memory/tools/<name>.md` — that an agent invokes *instead of* improvising the action per run (it absorbs environment variance and replaces throwaway generated scripts). The full concept, its rationale (stability / efficiency / authority), the definition-first discipline, the four canonical types, type semantics, the RFC 2119 behavioral-rules format, the optional `## Environment Applicability` block, the two-state lifecycle (`Draft` → `Verified`; only `Verified` records may be invoked), the edge cases, and the invocation preview contract are defined once in `.specify/shared/definitions/tool-definitions.md` — reference it, do not restate it. The reuse-before-generating operating rule for every other skill/command is `.specify/shared/workflow/tool-reuse-gate.md` (Constitution Principle XII). The authoring templates live inside the owning skill at `.specify/skills/internal/create-tools/templates/`.

> **Terminology**: unqualified "tool" here means the record above. A supported coding agent (Claude Code, Codex CLI, …) is an **AI agent CLI**; the `tools:` frontmatter key on an agent is its **tool-call list**.

### Modes → Capability Routing

`/speckit.tools` exposes **exactly five** modes:

| Mode | Recognized intent | Delegates to |
|------|-------------------|--------------|
| **define** | "定义工具", "创建工具", "新增工具", "注册工具", "define a tool", "create/add/register a tool" | `create-tools` skill |
| **modify** | "修改工具", "优化工具", "更新工具", "改工具规则", "modify/improve/fix a tool", "add alias", "verify tool" | `improve-tools` skill |
| **view** | "查看工具", "看下这个工具", "view/show a tool" | read-only display (see View / List Mode) |
| **list** | "列出工具", "有哪些工具", "list tools" | read-only display (see View / List Mode) |
| **invoke** | "调用工具", "执行工具", "跑一下", "invoke/run/execute a tool" | invocation gate (see Invoke Mode) |

**Routing flow**:

1. **Recognize intent** from `$ARGUMENTS` and conversation/repo context: classify as `define`, `modify`, `view`, `list`, or `invoke`.
2. **Resolve the record** — check `.specify/memory/tools/<tool-name>.md` and alias matches. When the same name exists under different types, require explicit user disambiguation and present all matching records.
3. **define** → `create-tools`: collect the mandatory fields **from the user** (never auto-populate a tool's contract from built-in knowledge), author the record from the matching type template, validate, and persist it with a generated `tool_id` — the record file is the single source of truth (no registry). If the record already exists, inform the user and offer `modify` or `view` instead.
4. **modify** → `improve-tools`: load the existing record and apply **field-level** edits only — source/contract correction, rule hardening, alias/rename, or `Draft` → `Verified` promotion. Preserve every unmodified field; re-validate and re-persist. If the record does not exist, report "no definition found" and offer to `define` it.
5. **view / list** → read-only display; never mutate a record (see View / List Mode below).
6. **invoke** → follow the **preview → confirm → execute** gate below.
   > Gate probe: gate-tools-invoke-entry — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).
7. **Empty arguments** → execute **Default Behavior (No Arguments)** below.
8. **Non-empty but ambiguous / unsupported** → report capabilities and request the missing intent (see "Ambiguous or Unsupported Intent" below).

### Default Behavior (No Arguments)

When `$ARGUMENTS` is empty, the command MUST execute the following sequence instead of routing to a mode:

1. **List all registered tools** — scan `.specify/memory/tools/*.md` and present a summary table with each tool's `name`, `tool_type`, `source_identifier`, and `status`. If no records exist, state "No tools found" explicitly.
2. **Give contextual suggestions** — based on the current conversation, recent repo activity, and the listed records, recommend the most relevant next action. Examples: a `Draft` record blocking use → suggest `modify` to complete it; a script the conversation keeps invoking by hand → suggest `define` it; a `Verified` record matching the current task → suggest `invoke`. Suggestions MUST be grounded in observable context, NOT fabricated.
3. **Show capability summary** — briefly list the five modes so the user knows what operations are available.

This behavior is informational and non-destructive: it MUST NOT define, modify, or invoke any tool without explicit user instruction.

### Ambiguous or Unsupported Intent

When intent cannot be resolved from non-empty arguments, the command MUST report the recognized capabilities and request the missing intent. It MUST NOT guess silently or fail without a message. Report this capability listing:

- **define** — author a new tool definition record with authoritative behavioral rules → `create-tools`
- **modify** — correct or strengthen an existing record, or promote it to `Verified` → `improve-tools`
- **view** — display one record's full definition
- **list** — show a summary table of all records
- **invoke** — preview a resolved invocation and execute it only after explicit confirmation

### View / List Mode

Read-only, never mutating:

- **view** — load the record and display its full definition: fields, parameters, returns, behavioral rules, aliases, `status`, `discovery_origin`, and `tool_id`. If no record exists, report "no definition found" and offer to `define` it.
- **list** — display a summary table of all records under `.specify/memory/tools/`. Distinguish `Draft` from `Verified` so incomplete records are visible.

### Invoke Mode (preview → confirm → execute)
> Gate probe: gate-tools-invoke-mode — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

Invocation is gated. The command MUST NOT execute a tool before explicit user confirmation:
> Gate probe: gate-tools-invoke-rule — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

1. **Load** the record and require `status: Verified`. A `Draft` record MUST block invocation — guide the user to complete the definition via `modify` instead.
2. **Preview** using the Invocation Preview format in `.specify/shared/definitions/tool-definitions.md`: the resolved command, resolved parameter values, the record's behavioral rules, and the expected output shape.
3. **Confirmation gate** — prompt `Proceed with execution? (yes/no)` and execute **only** on an explicit `yes`. On anything else, stop without executing and record the session as `cancelled`.
   > Gate probe: gate-tools-invoke-prompt — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).
4. **Execute** exactly what was previewed — do NOT modify parameters beyond the preview — while honoring the record's behavioral rules as authoritative over built-in knowledge.
5. **Record the session** — `tool_name`, `tool_id`, `resolved_command`, `result_status`.

### Persistence

Definition records: `.specify/memory/tools/<name>.md`; `tool_id` is the canonical form `<TOOL:.specify/memory/tools/<name>.md>`; the record file is the single source of truth — no registry. Discovery inventories, the `.specify/memory/tools.md` index trap, and store ownership: `.specify/shared/definitions/tool-definitions.md`. Agent-specific detection, guidance, and execution-feedback capture follow the routed skill's own Agent-Specific Configuration section (`create-tools` / `improve-tools`); for shared operational guidance, see `.specify/shared/workflow/agent-configuration.md`.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.tools" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.tools" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.tools" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"

## Handoffs

**Before**: Use when you need to externalize and reuse tool records with strict behavioral rules that outrank the agent's built-in knowledge.

**After**: Tool records are available for agent permissions wiring and reuse via the reuse gate.