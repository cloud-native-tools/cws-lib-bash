---
name: improve-tools
description: Improve an existing tool definition record — correct a wrong source or contract, add or sharpen behavioral rules, add aliases, rename, or promote Draft to Verified — driven by invocation evidence and user corrections. Use this when the user mentions ["modify a tool", "improve a tool", "fix a tool record", "update tool rules", "add tool alias", "verify a tool", "promote tool", "修改工具", "优化工具", "更新工具", "工具规则", "工具别名"]
skill_id: "<SKILL:.specify/skills/improve-tools/SKILL.md>"
---

# improve-tools

## Goal

Improve **one existing tool definition record** under `.specify/memory/tools/` so the next invocation is more correct and safer: fix a wrong source identifier or parameter contract, add or sharpen behavioral rules, add aliases, rename the record, or promote it from `Draft` to `Verified`. This skill is the refinement engine invoked by `/speckit.tools` for **modify** intent. Creating a record that does not exist yet is out of scope — see `create-tools`.

Edits are **field-level**: load the record, change only what the evidence justifies, re-validate, re-persist. Never regenerate a record from a template — that discards the user's accumulated authoritative knowledge.

Goal anchor (Constitution Principle XIII): this skill is a Better-Harness instrument — improving a tool record strengthens the **Controlled Execution** dimension (correct, safe, repeatable invocations) and closes the **Learning Capture** loop; goal model in `.specify/shared/guidelines/better-harness.md`.

## Input Contract

The input is a description of the tool to improve. Interpret it as follows:

- **Target identifier**: resolve exactly one record by tool name, alias, or `tool_id` (`<TOOL:.specify/memory/tools/<name>.md>`). If several records match (same name under different types), present all and ask which one. If none match, report "no definition found" and offer to define it via `create-tools` — do NOT create one implicitly.
- **Improvement direction**: extract the requested change — wrong source, missing/incorrect parameters, missing behavioral rules, unsafe invocation, alias needed, rename, status promotion. If absent, infer it only from concrete evidence (a failed invocation, a user correction, a changed source).
- **User emphasis**: treat details the user states as high-priority evidence, even when other fields also look improvable.

## Workflow

1. **Load the record and identify the direction.** Read `.specify/memory/tools/<name>.md` in full before editing. Restate which single record you resolved and what will change, so a mis-resolution surfaces before any write.
2. **Gather evidence.** Prefer concrete signals over impressions: a failed or wrong invocation (the command run and its actual output), a user correction, a source that moved or no longer exists, a rule that was violated because it was absent or vague, or a `Draft` record blocking invocation. Verify the current `source_identifier` still resolves (path exists / binary on `PATH` / function defined / endpoint reachable) and report the result.
3. **Classify the improvement.** Map the change to one of these, since each has a different validation consequence:

   | Class | Typical change | Validation consequence |
   |-------|----------------|------------------------|
   | **Source correction** | `source_identifier` or `tool_type` is wrong | Re-verify the source resolves; a type change re-selects the canonical type and may reset `status` to `Draft` |
   | **Contract correction** | `arguments` / `returns` wrong or incomplete | A `Verified` record MUST retain at least one of `arguments` / `returns` |
   | **Rule hardening** | add / sharpen `## Behavioral Rules` | Keywords limited to `MUST` / `MUST NOT` / `SHOULD` / `SHOULD NOT`, one bullet per rule |
   | **Environment drift** | `## Environment Applicability` is stale or incomplete — the tool was upgraded, a flag changed between versions, a new OS/architecture is now in play, or a fallback/preflight check is needed | Re-verify on the environment actually in use and record only what was observed; never widen a claim to a platform or version you did not verify. If the pinned invocation no longer holds, demote to `Draft` rather than leaving a wrong `Verified` contract |
   | **Alias / rename** | add an alias, or rename the record | Rename MUST fail on a name conflict rather than overwrite; renaming changes the canonical path, so the `tool_id` must be regenerated |
   | **Status promotion** | `Draft` → `Verified` | Only when every mandatory field is present, the source verified, and `arguments` or `returns` populated |

4. **Apply the minimal field-level edit.** Change only the fields the evidence supports. Preserve every unmodified field verbatim — including `behavioral_rules`, `aliases`, `discovery_origin`, and the record's section order. Do not reorder or drop sections, and do not clear a mandatory field (`name` / `tool_type` / `source_identifier` / `description`): clearing one is an error, not an edit.
5. **Re-validate and re-persist.** Run the same validation `create-tools` applies: canonical `tool_type`, non-empty mandatory fields, valid rule keywords, and the `Verified` ⇒ `arguments or returns` invariant. Refresh `last_updated`. If the edit invalidates the contract, demote to `Draft` and say so explicitly rather than persisting an inconsistent `Verified` record.
6. **Sync the registry.** Update the tool's row in the `### Tools` table of `.specify/instructions.md` when `name`, `tool_type`, `source_identifier`, `aliases`, `status`, `description`, or the canonical path changed. On rename, move the row rather than adding a second one — the registry MUST NOT carry two rows for one tool.
7. **Report.** State which record changed, the fields before → after, the resulting `status`, and any follow-up the user must do (e.g. fields still missing for `Verified`, or a stale reference to an old name).

## Constraints

- **Never regenerate from a template.** Field-level edits only; templates belong to `create-tools`.
- **Never invoke the tool to "test" an improvement.** Verification is limited to checking that the source resolves. Actual execution goes through the `/speckit.tools` invoke mode's preview → confirm → execute gate.
- **Never silently promote to `Verified`.** Promotion is an explicit, validated decision reported to the user.
- **Never weaken a behavioral rule without stated cause.** Rules are the record's safety surface; removing or loosening one requires the user's explicit instruction, recorded in the report.
- **One record per invocation.** Improving several tools is several runs.
- **Do not edit `.specify/memory/tools.md`** — that is the discovery inventory regenerated by `refresh-tools.sh`, not a definition record.

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/improve-tools/SKILL.md>`
- Canonical Path: `.specify/skills/improve-tools/SKILL.md`

## Resources

| Path | Contents |
|------|----------|
| `.specify/shared/definitions/tool-definitions.md` | Single source of truth for type semantics, RFC 2119 rules format, edge cases, and the invocation preview contract |
| `.specify/scripts/python/tools-utils.py` | Record model, validation, save/load, alias resolution, rename |
| `.specify/skills/create-tools/templates/` | The four type templates — read-only reference for the canonical section order |

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

Before executing this skill's workflow, identify which AI agent you are:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Qwen Code** | `QWEN.md` instructions loaded; `.qwen/` directory exists |
| **Codex CLI** | `.codex/` directory exists |
| **Hermes Agent** | `.hermes/` directory exists |
| **iFlow** | `.iflow/` directory exists |

If you cannot identify your agent, skip Step 2 and proceed with the standard workflow.

### Step 2: Load Agent-Specific Guidance

If you identified your agent in Step 1, check if a guide exists at:

```
${SKILL_HOME}/references/<agent-slug>-guide.md
```

Where `<agent-slug>` is: `claude-code`, `copilot`, `qoder`, `opencode`, `qwen`, `codex`, `hermes`, or `iflow`.

If the guide exists, read it and apply the agent-specific tool mappings, best practices, and pitfall avoidances during execution. If no guide exists for your agent, proceed with the standard workflow.

### Step 3: Capture Execution Feedback

If you encounter an agent-specific obstacle during execution (e.g., a tool call is unavailable, output format doesn't match expectations, a workaround was needed), generate a feedback document at:

```
.specify/memory/feedback/improve-tools-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

The feedback document MUST contain:

```markdown
# Agent Execution Feedback

**Source**: improve-tools
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

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:improve-tools" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
