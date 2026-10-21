---
name: create-skills
description: This skill can create new Spec Kit Skills from user input or conversation history. Use this when the user mentions ["create a skill", "new skill", "make a skill", "skill creation", "添加技能", "创建skill", "新建skill"]
skill_id: "<SKILL:.specify/skills/create-skills/SKILL.md>"
classification: external
---

# create-skills

## Goal

Create a high-quality Skill (for a Spec Kit project or any host application) from explicit user input or by distilling reusable workflows from the current conversation. The expected result is a well-structured `SKILL.md` with valid frontmatter, clear trigger descriptions, appropriate resource organization, and a deterministic `skill_id`.

## Workflow

### 0. Detect the runtime mode (Spec Kit project vs standalone)

Skills serve both code projects and non-code agent applications (e.g. QoderWork, Wukong, OpenClaw global skill directories). Detect the runtime mode first — the rule below is self-contained; in a Spec Kit project the reference doc `.specify/shared/workflow/runtime-mode.md`, **when present**, carries the same rule (optional integration, never required):

- `${SKILL_WORKDIR}/.specify/` **exists** → **Spec Kit project mode**: run the full workflow below (scaffolding, identity finalization, agent propagation, engine-backed Feedback).
- `${SKILL_WORKDIR}/.specify/` **does not exist** → **standalone mode** (first-class, not a degraded path): the target is a plain skills directory owned by the host application — or a generic project's own `skills/` root. In this mode:
  - `SKILL_HOME` is a sibling directory in the host skills directory; **align the new Skill's format with the existing skills there** (inspect one or two siblings first).
  - **Skip** Step 7 (propagation to built-in role agents) — that surface does not exist. Step 5 (identity finalization) applies in both modes; use the host skills directory paths, not `.specify/**`.
  - In Step 3, emit a **self-contained** `## Feedback` section (gated reflection, no `feedback-utils.py` invocation) instead of the engine-backed reference form.
  - Do not scaffold or reference any `.specify/**` path in the generated Skill.

State the detected mode briefly in the final report.

### 1. Determine the creation source

**Case A — User provided explicit input**

Parse `skill name` and `description` from the user input:

- **skill name**: A concise command-like identifier matching the project script validator: letters, digits, hyphens (`-`), and underscores (`_`) only. When inventing a name, prefer lowercase kebab-case (for example, `api-testing`) unless the user explicitly needs another valid form.
- **description**: A capability summary plus trigger keyword list. Format: `This skill can <capability>. Use this when the user mentions [ "keyword1", "keyword2", ... ]`. **No-workflow-summary rule**: the description MUST NOT summarize the workflow steps or body content — an agent that sees a workflow summary in the description will skip loading the body and execute a degraded version. Capability + triggers only.

If the input contains only a valid name and the Skill already exists at the detected mode's skills root (`.specify/skills/<name>/SKILL.md` in a Spec Kit project; `<skills-root>/<name>/SKILL.md` otherwise), redirect to `improve-skills` rather than creating a duplicate.

**Cross-SSOT collision check**: an absent skill at the detected root does not mean the name is free — scan the other locations that can own or load a Skill of that name (other projects' skills roots — including `.specify/skills/` locations in code projects when present — a global skills library, agent load directories, registries). On a hit, report *entity location + who references it* and choose a documented path (improve in place / adopt via link / split into layers / rename) — MUST NOT create a second entity with the same name silently. Scan targets and decision table: [name-collision-and-layering.md](./references/name-collision-and-layering.md) §1; when the chosen path is a split, the front-door / lower-layer authoring rules are §2.

If the description is missing, derive it from the current conversation or ask one targeted clarification question.

**Case B — User provided no input (empty arguments)**

Distill a reusable Skill from the current conversation history:

1. **Prefer an execution-notes doc over raw transcript**: if the workflow ran in a prior (possibly compacted) session, first look for a dated notes doc (e.g. `${SKILL_WORKDIR}/docs/notes/`) capturing the key commands and outcomes, and distill from it — mining a raw or compacted transcript is slow and lossy. When no such note exists, advise the user (in the wrap-up report) to record key commands into a dated notes doc *during* future executions so later distillation has a reliable source.
2. **Review the conversation history**: Identify recurring task patterns, explicit user intent (e.g., "save as a skill", "solidify this workflow"), multi-step operations with reuse value, and domain-specific decision logic.
3. **Distill a reusable workflow**: Extract the core task objective, key execution steps, trigger conditions/keywords, and required tools/scripts/resources.
4. **Generate Skill metadata**: Produce a concise English `name` (e.g., `data-validation`, `api-testing`) and a `description` with capability summary plus trigger keywords.
5. **Minimal clarification**: If critical information cannot be determined, ask **only one question at a time**. Prioritize: target output, scope (project vs personal), checklist vs multi-step workflow.

### 2. Determine SKILL_HOME and metadata

- **skill name** determines `SKILL_HOME`. Example: `name = "testing"` → `SKILL_HOME = <skills-root>/testing/` (root resolved per Step 0: `.specify/skills/` in a Spec Kit project; the project `skills/` root or the host skills directory otherwise).
- **description** must include keywords and trigger scenarios; avoid vague descriptions.
- **Writability pre-flight (fail fast)**: before drafting any content, touch-test the parent directory of `SKILL_HOME` (e.g. `mkdir -p "$SKILL_HOME" && touch "$SKILL_HOME/.wtest" && rm "$SKILL_HOME/.wtest"`). The host skills directory may be root-owned in some environments (container-created leftovers); report an unwritable target up front with the `sudo chown -R $USER <dir>` remedy instead of discovering it at the first write.

Storage location options (`SKILL_HOME`) — the root is an **input resolved per Step 0**, never a hard dependency:
- `.specify/skills/<name>/` — project-level primary **in Spec Kit project mode** (optional integration; when present it is the natural root for a Spec Kit project)
- project `skills/<name>/` — the generic project-level root (framework-source or standalone code projects)
- host skills directory `<skills-dir>/<name>/` — standalone mode (the directory the host agent application loads skills from)
- `.github/skills/<name>/` — compatibility entry (symlink, not primary)
- `${HOME}/.copilot/skills/<name>/` — personal-level

When authoring the new Skill, follow the canonical `${SKILL_HOME}` / `${SKILL_WORKDIR}` path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path the new Skill reads or writes (inputs in the user's project, outputs delivered to the user).

### 3. Structure the Skill

#### SKILL.md Specification

**Frontmatter** (minimum required):

```yaml
---
name: <name>
description: <capability + trigger keywords>
---
```

Optional frontmatter (on demand):
- `argument-hint`
- `user-invocable`
- `disable-model-invocation`
- `skill_id`: deterministic identifier for discoverability

**Body** — keep concise and actionable. Must include:
- Result goal
- Key steps (executable, checkable)
- Resource references (use relative paths: `./scripts/x.py`, `./references/details.md`)
- A `## Self-Improvement Contract` immediately before Feedback. In a Spec Kit project the form is owned by `.specify/shared/workflow/self-improvement-workflow.md` Create-Flow Integration (reference it, never copy its steps); standalone deployments carry an equivalent embedded contract.
- A `## Feedback` section as the final workflow section (mandatory). In Spec Kit project mode, copy the **skill reference form** from `.specify/shared/workflow/feedback-step.md` § *Embedded reference forms* **when those shared docs are present** (it begins with the runtime-mode gate), substituting only `skill:<name>`. That form is a pointer plus the unit id, so the section MUST NOT restate the owner's reflection rules, submission-prompt semantics or red lines — a restated copy is what drifts. In standalone mode, write a self-contained variant — keep the runtime-mode gate and the reflection steps, drop the `feedback-utils.py` invocation and threshold prompt. A new Skill lacking a `## Feedback` section is **non-conformant** and MUST fail validation.

**Size control**: Keep `SKILL.md` under 500 lines. Move large details into `./references/`.

#### Resource Directory Layout

```
${SKILL_HOME}/
├── SKILL.md            # Required, Skill main body
├── .specify/scripts/            # Executable scripts (optional)
├── references/         # Reference materials loaded on demand (optional)
└── assets/             # Static assets for outputs (optional)
```

The project creation script may create standard empty resource directories during scaffolding. Treat those as acceptable generated structure; only fail validation for unrelated documentation files, broken links, or resource directories whose checked-in contents are not needed by the Skill.

#### Progressive Disclosure

1. Discovery: Read `name` + `description`
2. After match: Read `SKILL.md` body
3. When needed: Read `.specify/scripts/`, `references/`, `assets/`

Constraints:
- `SKILL.md` recommended < 500 lines
- Reference chain at most one level (from `SKILL.md` directly to resource)
- Use relative paths uniformly (prefer `./references/...`)

#### Content NOT to include

Do not add unrelated documents: `README.md`, `INSTALLATION_GUIDE.md`, `QUICK_REFERENCE.md`, `CHANGELOG.md`, process logs, or full retrospectives.

### 4. Incrementally clarify details

Ask **only one question per round**, waiting for user response. Prioritize:
- Target output: What should the Skill produce?
- Applicable scenarios: Under what trigger conditions?
- Resource needs: Scripts, references, templates, or toolchain?

Iterate until:
1. Frontmatter is complete (`name`, `description`)
2. Body has clear executable steps
3. Resource directories are ready as needed
4. All resource links use relative paths

### 5. Finalize the Skill Identity (no registration)

There is no registry file in any mode — agents discover skills by scanning the skills directory (the Spec Kit project guide at `.specify/skills.md`, when present, describes the same model); Spec Kit project mode and standalone mode are the same here.

Finalize the identity inside `SKILL.md` itself:

- **skill_id**: `<SKILL:<resolved-path>/SKILL.md>` — Spec Kit installs record `.specify/skills/<name>/SKILL.md`; other roots record their own resolved path.
- **Canonical Path**: the same resolved path.

Discoverability is guaranteed by the directory plus valid frontmatter — do not write any registry row anywhere.

### 6. Validate the Skill

Run quality checks before reporting completion. See [the quality checklist](./references/skill-creation-quality-checklist.md) for the full validation workflow.

Minimum checks:
- [ ] Frontmatter: `name` matches directory, `description` has triggers
- [ ] Body: clear steps, no vague placeholders
- [ ] Resources: relative paths, no broken links; standard generated resource directories are acceptable
- [ ] Discoverability: the Skill exists at its **resolved** root path with valid frontmatter `name`/`description` — no registry to update
- [ ] Size: `SKILL.md` < 500 lines
- [ ] No unrelated documentation files
- [ ] Topology & links (when the host keeps a skill-topology registry or fans Skills out to several agent load directories): registry updated, dangling-symlink scan returns zero, each load directory resolves to the new content, and description-caching host registries refreshed — see [name-collision-and-layering.md](./references/name-collision-and-layering.md) §3
- [ ] Self-Improvement: `## Self-Improvement Contract` is present exactly once immediately before Feedback and references the canonical workflow
- [ ] Feedback: a `## Feedback` section is present as the final workflow section, beginning with the runtime-mode gate. Spec Kit project mode requires the skill reference form from `.specify/shared/workflow/feedback-step.md` § *Embedded reference forms* — a pointer plus `--unit-id "skill:<name>"`, not a restatement of the owner's rules; standalone mode requires the self-contained variant (no engine call). A Skill without the section is non-conformant — fix before reporting completion.
- [ ] Standalone mode only: format is consistent with sibling skills in the host directory, and no `.specify/**` path is referenced
- [ ] Spec Kit project mode: **run the existing skill-conformance contract suite** (`pytest tests/contract/ -q -k "skill or runtime_mode"`) before reporting completion — new skills are subject to ALL pre-existing conformance contracts (runtime-mode gate, feedback-section shape); a later full-suite regression is the wrong place to discover a miss. **Fallback**: if the project has no `tests/` or `tests/contract/` directory, the suite is not applicable — verify conformance via the manual checklist items above (frontmatter / Feedback section / registry / size) and state "contract suite not applicable" explicitly in the completion report; do not spin on the missing suite or report it as a failure
- [ ] Spec Kit project mode: **attribute every red before reporting it** — when that suite is red, re-run it with `--tb=line` (`pytest tests/contract/ --tb=line -k "skill or runtime_mode"`) and read, per failing assertion, **which skill it names**; then split the failures into **pre-existing debt** (skills this run never touched — an unsynced `.specify/skills/**` mirror is the common case) and **this new Skill's regression**. Quote the attribution command and that split in the completion report. A bare pass/fail count attributes nothing: while several skills of one family are edited in parallel, an unattributed red cannot be routed back to its author

### 6.5 Pressure Test (RED-GREEN)

Apply the method in [pressure-testing.md](./references/pressure-testing.md) before registering a **discipline/workflow skill** (one that constrains agent behavior):

1. **RED** — dispatch a fresh subagent on a realistic pressure scenario WITHOUT the skill; record its failures and rationalizations verbatim.
2. **GREEN** — repeat WITH the skill loaded; verify the RED failure modes do not recur (observed compliance, not a plausibility argument).
3. **REFACTOR** — close every loophole GREEN exposed (MUST/MUST NOT lines, red-flag phrases), re-run until clean.

Pure utility skills (deterministic script wrappers) may substitute a smoke invocation — state which case applied. The user may explicitly waive this step; record the waiver in the completion report either way.

### 7. Propagate the Skill to built-in agents

Applies only when creating a **new** Skill **in Spec Kit project mode** — in standalone mode skip this step (no built-in role agents exist). Wire it into the built-in role agents so they prefer it for role-relevant work, following the Skill Enablement convention (the `## Skill Enablement` section pattern on the built-in role agents under `.specify/agents/templates/`).

1. **Guard**: skip if the new Skill is non-declarable (reference-only/meta: `create-agent`, `improve-agent`, `create-skills`, `improve-skills`, `create-team`, `improve-team`, `create-tools`, `improve-tools`). Normal user-created Skills proceed.
2. **Analyze**: read the 7 built-in role agents from `.specify/agents/templates/` (`requirements-analyst`, `system-designer`, `module-designer`, `test-engineer`, `qa-engineer`, `knowledge-manager`, `ux-analyst`) and judge each agent's role against the new Skill's capability + trigger keywords.
3. **Match**: pick the agents whose role operations the Skill covers; draft a one-line "when to use" per match. If none match, report "no role-relevant agents" and skip edits (no forced use).
4. **Propose then apply**: show a `| Agent | Skill | When to use |` table and wait for confirmation. On confirm, for each matched agent edit BOTH `agents/<slug>.agent.md` and `.specify/agents/templates/<slug>.agent.md`:
   - Append the canonical Skill slug to the `skills:` frontmatter list (dedup; preserve order and all other keys).
   - Add a `| <skill> | <when-to-use> |` row to that agent's `## Skill Enablement` table.

**Invariants**: use the canonical slug; it MUST resolve to an installed `.specify/skills/<slug>/SKILL.md`; never add a non-declarable slug; preserve all existing frontmatter. Generator templates (`agent-capacity-*-template.md`) are intentionally NOT updated — a later regeneration would drop the added Skill.

### 8. Report completion

Summarize:
- Detected runtime mode (Spec Kit project vs standalone) and which Spec-Kit-specific steps were skipped
- Skill capabilities and directory structure
- `SKILL.md` path and `skill_id`
- Example prompts
- Which built-in agents the Skill was propagated to (or "none" if no role match)
- Suggested next-step customizations (e.g., add references, scripts, or personalized trigger keywords)

## Design Principles

### Manage Degrees of Freedom

- **High freedom**: Text strategies for multi-path problems
- **Medium freedom**: Pseudocode / parameterized scripts for configurable primary paths
- **Low freedom**: Fixed scripts / steps for high-risk error-prone operations

### Discoverable Descriptions

`description` must include keywords and trigger scenarios. Avoid vague one-liners. It states capability + triggers ONLY — never a summary of the workflow steps (a workflow summary invites the agent to skip the body).

### Anti-Patterns

- Vague descriptions that fail to trigger
- Descriptions that summarize the workflow body (agent skips loading the body)
- `SKILL.md` too large without splitting into `./references/`
- Directory name inconsistent with `name` in frontmatter
- Missing executable steps (only background prose)
- Inconsistent or broken resource paths

## Slash Behavior Notes

Skill behavior in the `/` menu is controlled by frontmatter:
- Default: Manually invocable + auto-triggerable
- `user-invocable: false`: Not manually invocable
- `disable-model-invocation: true`: Not auto-triggerable
- Both set: Both disabled

## Self-Improvement Integration

A created Skill is an Execution Subject. Before validation, add a compact `## Self-Improvement Contract` immediately before `## Feedback`; it MUST identify the canonical Skill directory, own-run observation sources, `improve-skills` as the mutation route, validation/pressure-test route, later comparison signal, and escalation boundary. Follow the framework's Create-Flow Integration (`.specify/shared/workflow/self-improvement-workflow.md` and `.specify/shared/guidelines/self-improvement.md`, when present; standalone deployments keep an equivalent embedded contract); do not copy their workflow or evidence-state definitions into the generated Skill. The current creation run establishes capability only—it is not evidence that the new Skill has improved.

This `create-skills` Skill is itself an Execution Subject: its own qualified run evidence routes through `improve-skills`, with the same canonical-owner and outcome-pending rules.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-skills" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-skills" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-skills" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
