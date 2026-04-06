> Note: `$ARGUMENTS` is **optional**. If empty, continue with discovery + interactive disambiguation. If provided, treat it as hint(s) for target tool, source type, alias preference, or execution priority.
>
> Intent interpretation rule:
>
> - Natural-language `$ARGUMENTS` describes the **tool capability to define/create or locate**, not an instruction to immediately execute that real-world action.
> - Example: `/speckit.tools 下载钉钉文档到本地markdown文件` means “create/find a tool whose purpose is 下载钉钉文档到本地markdown文件”, **not** “immediately download the document now”.
> - Actual tool invocation is allowed only after target tool resolution + parameter confirmation + explicit `Proceed with execution? (yes/no)` consent.

## User Input

```text
$ARGUMENTS
```

You **MUST** treat `$ARGUMENTS` as command parameters, not as a replacement of this workflow.

## Outline

Goal: Resolve one target tool, ensure a complete ToolRecord exists at `.specify/memory/tools/<tool-name>.md`, show execution preview, and execute only after explicit confirmation.
Goal extension: every creation/refresh/discovery path MUST produce and persist a deterministic `tool_id` (canonical workspace-relative record path).

### Tool Type Standardization

Tool naming and categorization MUST use the following four canonical types:

1. `mcp-call`: invoke MCP services.
2. `project-script`: scripts inside the current project, typically custom project-specific capabilities.
3. `system-binary`: binary tools in the current runtime environment (on Linux, typically tools like `find`, `grep`, etc.).
4. `shell-function`: functions defined in the current shell session (e.g., bash functions loaded at session startup via `~/.bashrc`).

In `refresh-tools.sh`, discovery MUST use JSON mode only when calling each Python discovery script. Persist the discovered payloads as source-specific JSON manifests so downstream prompts and scripts consume a single canonical JSON format.

Execution steps:

1. **Identify target tool basic info**
   - Parse `$ARGUMENTS` to extract **tool-definition intent** (tool name/capability description), not immediate runtime action.
   - If user input is a verb phrase (e.g., “下载…/同步…/生成…”), interpret it as candidate tool purpose and continue create/find flow first.
   - If missing, present interactive selection from available tools.

2. **Discover tools via script**
   - Run `.specify/scripts/bash/create-new-tools.sh --json --name $ARGUMENTS --action find` to get JSON output with tool information.
   - Parse JSON response and check status:
     - `status: "found"` → Tool exists, extract tool details
     - `status: "not_found"` → Tool not found, proceed to create
     - `status: "multiple_matches"` → Present options to user for disambiguation
   - Map tool to its source type (`mcp-call`, `project-script`, `system-binary`, `shell-function`).

3. **Resolve naming and conflicts**
   - Check exact name, alias match, and fuzzy candidates.
   - If same name exists across source types, require explicit user disambiguation before continuing.

4. **Reuse or create tool record**
   - Primary location: `.specify/memory/tools/<tool-name>.md`.
   - If existing record is complete, reuse directly.
   - If missing or incomplete, create/update from `.specify/templates/tool-*-template.md` with generalized ToolRecord fields:
     - Tool Name / Tool Type / Source Identifier / Tool ID / Description / Status / Last Updated
     - Parameters / Returns / Aliases
   - `tool_id` MUST be generated from the canonical path `.specify/memory/tools/<tool-name>.md` and persisted to the record.

5. **ID-first resolution**
   - If input contains a `tool_id`, resolve by ID before fuzzy discovery.
   - If `tool_id` is missing or invalid, fall back to existing fuzzy discovery.
   - If `tool_id` and natural-language hint conflict, stop and return an explicit conflict error.

6. **Validate record before invocation**
   - Required fields: `name`, `tool_type`, `source_identifier`, `description`.
   - `tool_type` must be one of `mcp-call|project-script|system-binary|shell-function`.
   - If status is `Verified`, Parameters and Returns cannot both be empty.
   - If invalid, guide user to fill missing fields and re-validate.

7. **Collect and sanitize parameters**
   - Collect required parameters one by one.
   - Apply minimal sanitization/escaping rules based on source type.
   - Produce one compact preview summary: source, tool, arguments, expected return shape.

8. **Explicit confirmation gate**
   - Ask: `Proceed with execution? (yes/no)`.
   - `yes` → execute tool.
   - otherwise → mark session as cancelled and do not execute.

9. **Report session result and persist artifacts**
   - Write/update tool record.
   - Backfill missing `tool_id` for historical records touched during refresh.
   - Record invocation session status (`success|failed|cancelled`) with summary.
   - If user asks to rename/alias, update record aliases and ensure uniqueness.

10. **Register `tool_id` in instructions template**
   - After a tool is selected or created, add one structured list entry to the `## Resource Registry` → `### Tools` subsection in `.ai/instructions.md`, using field names aligned with the selected `.specify/templates/tool-*-template.md` file.
   - Each entry must include at least `Tool Name`, `Tool ID`, `Tool Type`, `Source Identifier`, `Description`, and `Canonical Path`; include `Aliases`, `Status`, `Last Updated`, and `Resource ID` when available.
   - Keep the Tools list sorted and deduplicated, and remove `- None yet.` once at least one real tool entry exists.
   - Use the exact persisted `tool_id` value so future `/speckit.instructions` runs inherit the same registry.

## Output Requirements

- Tool records are stored in `.specify/memory/tools/` as `.md` files.
- Command output must include `tool_id` and canonical path whenever a tool is selected.
- Execution must not happen before user confirmation.
- Conflict scenarios must be resolved before invocation.
- Existing complete records should be reused to avoid repeated discovery.
- Alias/rename changes must remain discoverable by future `/speckit.tools` calls.