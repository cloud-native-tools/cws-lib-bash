---
name: create-tools
description: Author a tool definition record for the Spec Kit tools system — a project-script, system-binary, shell-function, or webhook tool with explicit authoritative behavioral rules. Definition is the primary action; discovery only bootstraps a draft. Use this when the user mentions ["define a tool", "create a tool", "add a tool", "register a tool", "new tool", "tool record", "behavioral rules", "定义工具", "创建工具", "新增工具", "注册工具", "工具记录"]
skill_id: "<SKILL:.specify/skills/create-tools/SKILL.md>"
---

# create-tools

## Goal

Author a **single tool definition record** for the Spec Kit tools system — one of four types (`project-script`, `system-binary`, `shell-function`, `webhook`) — and persist it at `.specify/memory/tools/<name>.md` with a generated `tool_id`. This skill is the authoring engine invoked by `/speckit.tools` for **define** intent; the command recognizes intent and delegates here rather than rendering templates inline. Modifying an existing record is out of scope — see `improve-tools`.

**Why a Tool exists** — a Tool is an **abstraction layer between an agent's intent and the environment's reality**, and it earns its keep two ways. (1) It **absorbs environment variance**: the same logical capability differs by command name, version, version-specific flags, CPU architecture, and OS, so an agent reasoning from training knowledge picks one plausible invocation and gets it wrong on the machine actually present. (2) It **replaces throwaway generated scripts**: without a Tool, an LLM writes ad-hoc script code per run, varying in quality and correctness and differing between runs. A record pins what was verified once so it is reused thereafter — buying **stability** (same behavior across runs and agents), **efficiency** (no re-deriving or re-validating the invocation, so less inference overhead), and **authority** (the record's behavioral rules override the model's built-in knowledge). The canonical definition is `.specify/shared/definitions/tool-definitions.md`.

**Definition-first is the core discipline.** Because a record's whole value is being *more trustworthy than the model's beliefs*, mandatory fields MUST come from the user or from a verified observation — never auto-populated from what the model believes it knows about a command. Discovery assists only by bootstrapping a `Draft` for the user to complete.

Canonical template home: `${SKILL_HOME}/templates/` (installed mirror: `.specify/skills/create-tools/templates/`).

## Capability Matrix

Select the template from the tool's `tool_type`:

| `tool_type` | Scope | Source Identifier | Template |
|-------------|-------|-------------------|----------|
| `project-script` | Project-level — scripts bundled with this project | path relative to project root | `${SKILL_HOME}/templates/tool-project-script-template.md` |
| `system-binary` | System-level — executables on `PATH` | absolute binary path | `${SKILL_HOME}/templates/tool-system-binary-template.md` |
| `shell-function` | Shell-session — functions sourced from dotfiles | function name | `${SKILL_HOME}/templates/tool-shell-function-template.md` |
| `webhook` | Network-level — HTTP-triggered remote operation | URL endpoint | `${SKILL_HOME}/templates/tool-webhook-template.md` |

Type semantics, the RFC 2119 behavioral-rules format, edge cases, and the invocation preview contract are defined once in `.specify/shared/definitions/tool-definitions.md`. Read it before authoring; do not restate it here.

## ToolAuthoringRequest Intake

Resolve these before writing anything. Mandatory fields have **no default** — ask rather than guess:

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Command-like identifier (letters, digits, hyphens, underscores); names the record file |
| `tool_type` | yes | One of the four canonical types above; legacy short forms `system` / `shell` / `project` are normalized on save |
| `source_identifier` | yes | Per the Capability Matrix — the concrete thing that gets invoked |
| `description` | yes | One line: what it does and when to use it |
| `behavioral_rules` | recommended | RFC 2119 bullets; the whole reason records outrank model knowledge |
| `environment` | recommended | Verified version, version differences, platform, architecture, fallback, preflight check — the axes along which this capability actually varies. Record only what was verified; an empty field means "no known variance", never "verified everywhere" |
| `arguments` / `returns` | conditional | **Required when `status: Verified`** — a Verified record with neither is invalid |
| `aliases` | optional | Alternate names resolved to this record |
| `status` | derived | `Draft` until the contract is complete and confirmed; then `Verified` |

## Workflow

1. **Resolve the target and reject duplicates.** Check `.specify/memory/tools/<name>.md` and alias matches. If a record already exists, stop and hand off: offer `modify` (→ `improve-tools`) or `view`. Never silently overwrite an existing definition. When the same name exists under a *different* type, require explicit user disambiguation and present all matching records.
2. **Collect mandatory fields from the user.** Ask for anything missing from the Intake table. **Do NOT auto-populate `source_identifier`, `description`, `arguments`, `returns`, or `behavioral_rules` from built-in knowledge about a well-known command** — that is the exact failure the record exists to prevent. If the user supplied only a name, offer discovery (step 3) to bootstrap a draft.
3. **Bootstrap from discovery only when asked.** Run `.specify/scripts/bash/create-new-tools.sh --json --name <name> --action find` to locate a candidate source. A discovery-derived record MUST be saved with `status: Draft` and `discovery_origin: discovery-assisted`, labelled `Draft — pending user confirmation`; a manually authored one uses `discovery_origin: manual-entry`. Discovery proposes; the user confirms.
4. **Author the record from the matching template.** Copy the template selected in the Capability Matrix and fill every placeholder. Preserve the template's section order and the `## Behavioral Rules` section — downstream consumers parse these headings. Write behavioral rules as `- {KEYWORD} {constraint}` bullets using only `MUST` / `MUST NOT` / `SHOULD` / `SHOULD NOT`.
5. **Capture the verified environment.** Fill `## Environment Applicability` with what was actually observed: the version the contract was verified against, any version-specific flag differences, OS/architecture applicability and per-platform differences, a fallback when the primary source is unavailable, and a cheap preflight check. **Never claim a version, platform, or architecture that was not verified** — state what you verified and leave the rest blank. Where variance is known but one invocation cannot cover it, put the branch in the relevant field rather than silently pinning one form. Omit the section entirely when the capability genuinely does not vary.
6. **Validate before persisting.** Confirm: `tool_type` is canonical; `name`, `source_identifier`, `description` are non-empty; behavioral-rule keywords are valid; and if `status: Verified`, at least one of `arguments` / `returns` is populated. If the source path/endpoint does not exist, warn the user but still allow creation as `Draft`. Contradictory user rules are persisted as-is with an advisory note — the user is the authority.
7. **Persist and generate the `tool_id`.** Write to `.specify/memory/tools/<name>.md`. The `tool_id` is the canonical form `<TOOL:.specify/memory/tools/<name>.md>` — generate it from the workspace-relative path, never hand-type it.
8. **Register.** Add one row for the tool in the `### Tools` table of `.specify/instructions.md` (`## Resource Registry`), inside the `<!-- TOOLS_REGISTRY_START -->` / `<!-- TOOLS_REGISTRY_END -->` range. Keep rows deduplicated and sorted, and keep the columns aligned with the table header. This range is owned by the tools domain — `/speckit.instructions` does not reconcile it.
9. **Report.** State the record path, the `tool_id`, the resolved `status`, and — when the record is `Draft` — exactly which fields the user must supply to reach `Verified`.

## Constraints

- **Never fabricate a tool's contract.** No auto-populated parameters, flags, return shapes, or rules from model knowledge. Absent user input, the field stays empty and the record stays `Draft`.
- **Never execute the tool while defining it.** Authoring is a write-a-record operation. Invocation is a separate mode behind the `/speckit.tools` preview → confirm → execute gate.
- **One record per invocation.** Batch requests are handled one tool at a time, each with its own confirmation.
- **Do not edit `.specify/memory/tools.md`** — that file is the discovery inventory regenerated by `refresh-tools.sh`, not a definition record.
- **Behavioral rules are authoritative at invocation time.** When a record exists, agents MUST follow its persisted rules over training knowledge.

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/create-tools/SKILL.md>`
- Canonical Path: `.specify/skills/create-tools/SKILL.md`

## Resources

| Path | Contents |
|------|----------|
| `${SKILL_HOME}/templates/` | `tool-project-script-template.md`, `tool-system-binary-template.md`, `tool-shell-function-template.md`, `tool-webhook-template.md` |
| `.specify/shared/definitions/tool-definitions.md` | Single source of truth for type semantics, RFC 2119 rules format, edge cases, and the invocation preview contract |
| `.specify/scripts/bash/create-new-tools.sh` | Discovery bootstrap + template-driven record creation (`--action find` / `create` / `list`) |
| `.specify/scripts/python/tools-utils.py` | Record model, validation, save/load, alias resolution |

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
.specify/memory/feedback/create-tools-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

The feedback document MUST contain:

```markdown
# Agent Execution Feedback

**Source**: create-tools
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
     --unit-id "skill:create-tools" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
