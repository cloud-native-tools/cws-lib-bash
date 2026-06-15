> Note
>
> `/speckit.skills` is the orchestration entrypoint for Skill management. It determines whether the target Skill already exists, then delegates:
> - **Missing target** → `create-skills` for new Skill creation (scaffolded directly against the current spec).
> - **Existing target** → `improve-skills` for Skill refinement, **including a mandatory spec-compliance modernization pass** that brings the existing Skill in line with the current spec (directory layout, frontmatter fields, `${SKILL_HOME}` / `${SKILL_WORKDIR}` path conventions, Migration Mapping legacy idioms, etc.) before applying any user-requested optimization.
>
> Detailed creation methodology lives in `skills/create-skills/SKILL.md`. Detailed improvement methodology lives in `skills/improve-skills/SKILL.md`.

## User Input

```text
$ARGUMENTS
```

## Orchestration Workflow

### Step 1: Parse target Skill

Extract the target Skill name from `$ARGUMENTS`:

- If the user explicitly names a Skill (e.g., `docx-utils` or `testing - Unit testing utils`), use that name.
- If `$ARGUMENTS` is empty, infer the target from the current conversation or ask one targeted clarification question.
- The name must be a concise command-like identifier using only letters, digits, hyphens (`-`), and underscores (`_`).

### Step 2: Check target existence

Determine whether `.specify/skills/<name>/SKILL.md` already exists:

- Run `.specify/scripts/bash/create-new-skill.sh --json <name>` or check the filesystem directly.
- Consider `.github/skills/<name>/SKILL.md` only after confirming `.specify/skills/` is the canonical source.

### Step 3: Route to the correct Skill

**If the target Skill does NOT exist**: Delegate creation to `create-skills`.

- Read `skills/create-skills/SKILL.md` for the full creation workflow.
- This covers: explicit-input parsing, conversation distillation, minimal clarification, SKILL.md structure, resource directories, registry updates, and completion reporting.
- The newly scaffolded Skill MUST conform to the current spec on day one (directory layout in [Step 3a](#step-3a-spec-compliance-modernization-checklist), frontmatter fields, `${SKILL_HOME}` / `${SKILL_WORKDIR}` path conventions). Use `.specify/templates/skills-template.md` as the starting point — it already encodes the canonical structure.

**If the target Skill ALREADY exists**: Delegate to `improve-skills`, but require a **two-phase** pass:

1. **Phase A — Spec-compliance modernization (mandatory).** Before addressing any user-requested optimization, run the [Spec-Compliance Modernization Checklist](#step-3a-spec-compliance-modernization-checklist) below against the existing Skill and apply minimal targeted edits to bring every checklist item into compliance. This phase MUST run even when the user only asked for a behavioural improvement, because subsequent edits assume the Skill already follows the current spec.
2. **Phase B — User-requested refinement.** After Phase A completes, proceed with the standard `improve-skills` workflow (evidence collection, root-cause analysis, minimal targeted changes, validation) for whatever optimization direction the user specified.

When delegating, read `skills/improve-skills/SKILL.md` for the full improvement workflow and pass the modernization checklist as the first item in the analysis pass.

#### Step 3a: Spec-Compliance Modernization Checklist

Apply this checklist verbatim to every existing Skill before user-requested refinement. Each item maps to a concrete, mechanical edit; do **not** rewrite Skill behaviour during this phase.

1. **Canonical path & directory layout**
   - Canonical SKILL.md MUST live at `.specify/skills/<name>/SKILL.md`.
   - The Skill directory SHOULD contain (create on demand, do not delete pre-existing custom subdirs):
     ```
     ${SKILL_HOME}/
     ├── SKILL.md         # required
     ├── .specify/scripts/         # executable scripts (optional)
     ├── references/      # on-demand reference docs (optional)
     └── assets/          # output templates / static assets (optional)
     ```
   - `.github/skills/<name>` is a compatibility entrypoint only (symlink or placeholder); never the source of truth.

2. **Frontmatter fields** (in this order)
   - `name`: matches the directory name exactly.
   - `description`: capability summary + trigger keyword list (`Use this when the user mentions [...]`). Multi-line via `description: |` is allowed.
   - `skill_id`: `<SKILL:.specify/skills/<name>/SKILL.md>`. If missing, regenerate via `.specify/scripts/bash/create-new-skill.sh --refresh-only --name <name> --json`.
   - Optional: `argument-hint`, `user-invocable`, `disable-model-invocation`. Keep only when intentional.

3. **Path conventions — `${SKILL_HOME}` / `${SKILL_WORKDIR}`**
   - Every Skill-owned resource reference (scripts, references, assets, sub-files) MUST use `${SKILL_HOME}/<relative-path>` in prose, code blocks, examples, and prompts.
   - Every runtime/user-facing read or write (user inputs, generated outputs) MUST use `${SKILL_WORKDIR}/<relative-path>`.
   - Never conflate the two; never embed agent-specific install paths.
   - For each shell script under `${SKILL_HOME}/.specify/scripts/`, ensure the FR-016 idiom appears at the top:
     ```bash
     SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
     SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"
     ```
   - Scripts nested deeper than `${SKILL_HOME}/.specify/scripts/<name>.sh` MUST adjust the `..` count accordingly.

4. **Migration Mapping (legacy idioms → new form)**
   Apply the [Migration Mapping](#migration-mapping) table mechanically. Common rewrites:
   - Bare relative paths (`./.specify/scripts/init.sh`, `./references/spec.md`) → `${SKILL_HOME}/.specify/scripts/init.sh`, `${SKILL_HOME}/references/spec.md`.
     Exception: links **inside SKILL.md** to sibling files MAY remain as `./references/...` (they are markdown-relative, not path-conventions).
   - `${SKILL_ROOT}/X` → `${SKILL_HOME}/X`.
   - Hard-coded install paths (`~/.copilot/skills/<name>/...`, `.specify/skills/<name>/X` in prose) → `${SKILL_HOME}/X`.

5. **Registry consistency**
   - `.specify/instructions.md` `### Skills` table contains exactly one deduplicated row for the canonical `skill_id`. Add the row if missing; remove duplicates if present.

6. **Hygiene**
   - SKILL.md stays under 500 lines; oversize content moves to `${SKILL_HOME}/references/`.
   - Remove unrelated docs that should not live inside the Skill (`README.md`, `INSTALLATION_GUIDE.md`, `CHANGELOG.md`, process logs).
   - Reference chain depth is at most one level (SKILL.md → resource).

After applying the checklist, exercise the Skill once (or at minimum re-read SKILL.md end-to-end) to confirm behaviour is unchanged — the modernization pass is non-behavioural by design (per SC-004).

### Step 4: Validate and report

After the delegated Skill completes:

- Confirm the target Skill's `SKILL.md` frontmatter is valid (`name`, `description`, `skill_id`) and the canonical path matches the expected `.specify/skills/<name>/SKILL.md`.
- Verify the Skills registry in `.specify/instructions.md` includes one deduplicated row for the Skill.
- For an **existing-Skill modernization** run, additionally verify every Spec-Compliance Modernization Checklist item from [Step 3a](#step-3a-spec-compliance-modernization-checklist) is now satisfied. Re-run any partial check individually if a combined validation command returned only partial output.
- Report:
  - The created or updated paths, `skill_id`, and any registry edits.
  - Which modernization checklist items required edits vs. were already compliant (existing Skills only).
  - Follow-up actions (e.g., run `/speckit.instructions`, exercise the Skill once).

## Path Conventions

Every Skill is written against two named, agent-engine-agnostic path variables. Authoring guidance in `skills/create-skills/SKILL.md` and `skills/improve-skills/SKILL.md` consumes this section verbatim.

- **`${SKILL_HOME}`** — the Skill's **real on-disk directory** containing `SKILL.md`, after symlink resolution. Use it for every reference to a Skill-owned resource: scripts, references, assets, sub-directory files. The value is absolute, post-symlink (physical), and identical across compatibility entrypoints (e.g., `.specify/skills/<name>/` and a symlinked `.github/skills/<name>/` resolve to the same `${SKILL_HOME}`).
- **`${SKILL_WORKDIR}`** — the **runtime working directory** of a Skill-invoked process, typically the user's project root. Use it for every user-facing path: inputs the script reads from the user's project, outputs the script writes for the user. The value is runtime-bound, absolute, symlink-resolved, and stays anchored to the user's directory across nested Skill calls.

**Usage rule**: Use `${SKILL_HOME}` for Skill-owned resources; use `${SKILL_WORKDIR}` for runtime/user-facing paths. Never conflate the two.

The canonical written form is `${SKILL_HOME}` / `${SKILL_WORKDIR}` in every context — SKILL.md prose, code blocks, examples, prompts — regardless of execution environment.

### Computation Idioms

For Skill shell scripts, self-compute the variable using the FR-016 fallback pattern. Copy this verbatim into the top of each script:

```bash
SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"
```

Notes:
- The `${VAR:-fallback}` pattern lets an agent runtime that exports `SKILL_HOME` / `SKILL_WORKDIR` take precedence; the fallback only runs when the variable is unset.
- The `SKILL_HOME` fallback assumes the conventional placement `${SKILL_HOME}/.specify/scripts/<name>.sh`. Scripts nested deeper (e.g., `${SKILL_HOME}/.specify/scripts/sub/<name>.sh`) must adjust the `..` count accordingly.
- `pwd -P` is POSIX (works on stock macOS `/bin/bash` 3.2 without GNU coreutils); avoid `readlink -f` in scripts.
- A *conceptual* recipe — `dirname $(readlink -f SKILL.md)` — is acceptable in prose when reasoning about a known SKILL.md path, but **NOT for scripts**; use the FR-016 idiom there.

### Paired Example

A single script that reads a Skill-owned template and writes a user-facing output uses both variables — `${SKILL_HOME}` for the read, `${SKILL_WORKDIR}` for the write — and they MUST NOT be conflated:

```bash
#!/usr/bin/env bash
set -euo pipefail

SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"

template="${SKILL_HOME}/assets/template.md"   # Skill-owned read
output="${SKILL_WORKDIR}/rendered.md"          # user-facing write

cp "$template" "$output"
```

Reading from `${SKILL_WORKDIR}` (instead of `${SKILL_HOME}`) for the template would fail when invoked from any directory other than the Skill's install path; writing to `${SKILL_HOME}` (instead of `${SKILL_WORKDIR}`) would leak the rendered output into the Skill installation instead of delivering it to the user.

### Non-shell Agents

Agents that do not execute shell commands resolve `${SKILL_HOME}` (and `${SKILL_WORKDIR}`) semantically: the LLM substitutes the right absolute path at read time. The written form `${SKILL_HOME}` stays identical across shell and non-shell agents — only the resolution mechanism differs.

### Nested Invocations

When one Skill's script calls another Skill's script, the caller MUST `unset SKILL_HOME` before the call, so the callee's `${SKILL_HOME:-fallback}` recomputes from the callee's own location. The caller MUST NOT unset `SKILL_WORKDIR` — the user's working directory stays anchored across the chain. The runtime-export-precedence design above applies to the top-level agent runtime; intermediate Skill scripts do not export `SKILL_HOME` for their callees.

## Migration Mapping

Existing Skills migrate opportunistically to the new convention — there is no flag-day requirement (FR-012). When updating a Skill, rewrite each legacy path idiom using the mapping below. Pre-migration Skills continue to function under their existing idioms; the mapping is mechanical, not semantic.

| Legacy idiom | New form | Example before | Example after |
|--------------|----------|----------------|---------------|
| Bare relative path (`./X`) | `${SKILL_HOME}/X` | `./.specify/scripts/init.sh` | `${SKILL_HOME}/.specify/scripts/init.sh` |
| `${SKILL_ROOT}/X` reference | `${SKILL_HOME}/X` | `${SKILL_ROOT}/references/spec.md` | `${SKILL_HOME}/references/spec.md` |
| Agent-specific install path (`~/.copilot/skills/<name>/X`, `.specify/skills/<name>/X`, etc.) | `${SKILL_HOME}/X` | `~/.copilot/skills/my-skill/assets/x.png` | `${SKILL_HOME}/assets/x.png` |

After applying the mapping, exercise the Skill once to confirm behaviour is unchanged (per SC-004); the rewrite is non-behavioural.

## Handoffs

- After creation or modernization+improvement, run `/speckit.instructions` to update project instructions so the Skill remains discoverable.
- If Step 4 validation surfaces remaining checklist gaps, re-route to `improve-skills` for another targeted pass — do not silently leave the Skill partially modernized.