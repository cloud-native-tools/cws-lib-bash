---
name: manage-instructions
description: Generate or update the project-wide AI instruction file `.specify/instructions.md` and its per-tool compatibility symlinks as a non-destructive reconcile engine — establish the refresh base, take the section observation snapshot, recover content lost to older overwriting runs, analyze project context, converge the file section-by-section through the tolerance band (with size-budget routes R1/R2), validate coverage against the backup history, and emit the residual report; also seeds the project glossary and converges legacy registry / inline Git-Workflow sections. Use this when the user mentions ["instructions", "instructions.md", "项目指令", "生成指令文件", "更新指令", "刷新指令", "instruction refresh", "refresh instructions", "compatibility symlinks", "兼容符号链接", "CLAUDE.md", "QODER.md", "AGENTS.md", "Documentation Map"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-instructions/SKILL.md>"
---

# manage-instructions

## Goal

Generate or update `.specify/instructions.md` — the single source of truth for project-level
AI instructions — so a fresh AI instance is immediately productive, and keep the per-tool
compatibility symlinks (`CLAUDE.md`, `QODER.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
`.github/skills`) honest. The run is a **reconcile**: observe, diff through a tolerance band,
converge non-destructively.

Owning command: `/speckit.instructions`. Canonical extraction source:
`.specify/templates/commands/instructions.md` § Overview content guidelines, § Update Strategy,
§ Glossary Initialization, § Error Handling, and § Actions 1–8. Content moved here in
substance; the command template keeps entry, user-input handling, the frontmatter `scripts:`
wiring, and the wrap-up lifecycle steps only.

**Existing delegations (not absorbed)**: the memory face is already delegated and stays at
command level — prior-memory recall (touched by Action 4) lives in the native `memory-recall`
skill (`.specify/skills/internal/memory-recall/SKILL.md`), and run-outcome recording (Action 8) lives
in the native `memory-record` skill (`.specify/skills/internal/memory-record/SKILL.md`). This skill
references them where its workflow touches them; it does not restate their rules.

## Input Contract

- **Intent**: full reconcile (empty arguments → comprehensive creation/update) or targeted
  partial update (arguments carry section-level update requests for
  `.specify/instructions.md`, supplemental context to refine project guidance, or constraints
  requiring specific content ranges preserved/excluded). The owning command's User Input
  Protocol processes `$ARGUMENTS` and hands over the processed substance; input with clear
  ambiguity, confusion, or likely misspellings that materially affect interpretation is sent
  back for a rephrase before this skill starts.
- **Operating surface**: `.specify/instructions.md`, its timestamped backups
  (`.specify/instructions.md-<TIMESTAMP>`), and the compatibility symlinks.

## Target Artifact Quality Bar

Content guidelines for `.specify/instructions.md` — what the convergence pass writes toward:

- **Map, not manual (地图而非手册)**: the file's job is to answer *what exists* and *where it
  lives*, then point to the owning document — never to teach *how*. Operational detail
  (workflows, step sequences, invocation rules) belongs in the documents the map points to
  (constitution, `docs/`, `.specify/shared/` definitions, skill/command files); when tempted to explain
  a procedure here, replace it with a pointer to the canonical doc that owns it.
- If `.specify/instructions.md` already exists, merge intelligently: preserve valuable content
  and update only what is outdated.
- **Non-destructive guarantee**: the existing instructions may contain accumulated,
  hand-authored knowledge that is NOT reproducible from a fresh codebase scan (custom
  governance rules, tribal knowledge, decision rationale). This MUST NOT be lost. When the
  file already exists, the setup script keeps it **in place as the refresh base** (it does not
  render the template over it), so refresh it *in place, section by section* — updating only
  sections whose described state no longer matches project reality and preserving everything
  else verbatim (Actions 2 and 5).
- Keep it concise and actionable (~20–50 lines) using Markdown structure.
- Use concrete examples from this repo when describing patterns; avoid generic advice;
  document only this project's specific approaches; document only what is observable in the
  codebase (not aspirational practices); reference key files/directories that exemplify
  important patterns.

Knowledge the discovery pass hunts for (fresh-instance productivity): the big-picture
architecture that requires reading multiple files to understand (major components, boundaries,
data flows, rationale behind key structure); critical developer workflows (build, test,
debug), especially commands not obvious from file inspection alone; conventions and patterns
that differ from common defaults; integration points, external dependencies, and
cross-component communication patterns; potential pitfalls or common development environment
issues; key files/directories that exemplify patterns. Explore the codebase via subagent,
1-3 in parallel if needed. Build/test commands matter doubly — agents run these
automatically — so they must be present and correct.

## Reconcile Model (Update Strategy)

The run is a **reconcile engine** over the instructions space (pattern:
`.specify/shared/patterns/reconcile-pattern.md`): the **desired state** is the latest template
structure + current project reality + user-authored accumulated knowledge + this run's
`$ARGUMENTS`; the **current state** is the existing `.specify/instructions.md` + compatibility
symlinks + glossary seed. Each run observes, diffs section-by-section through a **tolerance
band**, and converges non-destructively — fresh generation is just the bootstrap case (empty
current state), and partial update is directed convergence.

- **Tolerance band**: a section whose described state still matches project reality is marked
  consistent and left **byte-for-byte untouched** — never rewrite a section to change nothing,
  never churn cosmetic wording.
- **Archive-not-delete**: user-authored content is never dropped; superseded snapshots live on
  as `.specify/instructions.md-<TIMESTAMP>` backups, and lost content is recovered from them
  (Action 3).
- **Scope zones**: `docs/git-workflow.md` is owned by the `git-utils` skill (scope A) —
  observed but never converged here. No managed registry ranges exist in the current template:
  skills and tools are discovered via their directories (`.specify/skills/`,
  `.specify/memory/tools/`), not registered.

When `$ARGUMENTS` is empty (full reconcile):

- **Auto-update sections**: Documentation Map, Spec Kit Framework Map, Tech Stack & Resources,
  Key Directories, Build/Test commands.
- **Preserve sections**: project-specific custom notes, manually added governance rules, and
  hand-authored lessons.
- **Conflict policy**: if generated content conflicts with clearly user-authored content,
  preserve the user-authored content and update only stale factual items.

When `$ARGUMENTS` has content (partial update), modify only the requested sections and keep
unrelated sections untouched.

## Glossary Initialization

Ensure the single project-wide glossary exists and seed it with observed domain terms
(protocol owner: `.specify/shared/workflow/glossary.md`):

- The setup script creates `.specify/memory/glossary.md` from
  `.specify/templates/glossary-template.md` **only if absent** (non-destructive — never
  overwrite or discard an existing glossary; user-authored entries are authoritative).
- Propose **project-specific** terms observed from the constitution, `features.md`, feature
  names, and high-frequency documentation phrases as `origin=auto`, `status=proposed`.
  **Exclude common everyday words.**
- Record proposals via
  `python3 .specify/scripts/python/glossary-utils.py --action add --canonical "<T>" --meaning "<M>" --origin auto --status proposed`,
  writing non-conflicting terms directly (non-blocking, merged into the wrap-up report); only
  conflicts or overwrites of user entries go through user resolution before writing.
- Confirm the generated `.specify/instructions.md` Documentation Map includes the **Glossary**
  row so the glossary is ambient for every command.

## Error Handling

Classify failures before deciding to stop:

- **Critical (must stop and report)**:
  - `.specify/instructions.md` cannot be created or written.
  - Required root metadata exists but is unreadable (for example
    `.specify/memory/constitution.md`).
  - Permission denied on required paths.
- **Warning (continue with fallback)**:
  - `{SCRIPT}` exits non-zero but required directories/files already exist.
  - Individual tool/skill docs are empty.
  - Symlinks already exist and point to valid targets.

Fallback behavior:

1. If setup script fails but workspace prerequisites are already present, continue with manual
   analysis and update.
2. If symlink check fails, retry validation and provide actionable repair commands in report.
3. Always report whether completion is full-success or success-with-warnings.

## Workflow (Actions 1–8)

### Action 1 — Setup

Run `{SCRIPT}` (`.specify/scripts/bash/generate-instructions.sh`, mirrored at
`.specify/scripts/bash/generate-instructions.sh`) to ensure the basic directory structure,
`.copilotignore`, and template `.specify/instructions.md` exist.

- This script handles the "heavy lifting" of creating directories, ignoring files,
  establishing symlinks for supported AI tools (`.github`, `.qoder`, `.claude`), and cleaning
  up deprecated tool artifacts (`.clinerules`, `.lingma`, `.trae`, etc.).
- It renders a fresh `.specify/instructions.md` from the template **only** when one does not
  already exist.
- It also creates `.specify/skills.md` and `.specify/tools.md` **only if absent** (copied from
  `.specify/templates/skills.md` / `.specify/templates/tools.md`) — the explanation docs for
  the skills/tools discovery model. Existing copies are never overwritten.
- When `.specify/instructions.md` already exists, the script is **non-destructive**: it keeps
  the existing file **as the refresh base** (never rendering the template over it) and writes
  a non-clobbering timestamped backup (`.specify/instructions.md-<TIMESTAMP>`). It no longer
  fuses only `## Project Overview`; the full section-by-section refresh is performed by
  Actions 2–6 below.
- If the script returns non-zero, apply the **Error Handling** rules above instead of failing
  immediately.

### Action 2 — Establish the Refresh Base + Observation Snapshot

(Skip entirely if no `.specify/instructions.md` existed before this run.)

- The existing `.specify/instructions.md` **IS** the refresh base — the setup script left it
  in place untouched, so refresh it *in situ*. Do NOT regenerate from the template and do NOT
  rebuild the file from decomposed fragments.
- **Safety net**: the setup script wrote a non-clobbering timestamped backup and never
  overwrites earlier ones, so `.specify/instructions.md-*` is a durable history. If the script
  did not run or produced no backup, copy the current file to such a snapshot before starting
  to edit, so any mistaken edit is recoverable.
- **Read for reconciliation**: read (a) the current `.specify/instructions.md` (the base) and
  (b) the latest `.specify/templates/instructions-template.md` (the target structure a fresh
  spec-kit version expects). The template tells which sections/markers *should* exist; the
  base holds the authoritative user content.
- **Inventory sections (mandatory artifact — observation snapshot)**: take the sizes and the
  two classifications **from Action 1's section table**, never by re-measuring the file by
  eye. The script already compared every top-level section of the base against the rendered
  template and emitted one row per section —
  `section | live B | tmpl B | delta | placeholder | project-owned`. Those columns are the
  machine's verdict: consume them as-is, and add exactly one column of your own — whether the
  section is auto-derivable from a codebase scan (e.g. raw Tech Stack facts, Documentation Map
  paths) or hand-authored / non-reproducible (custom governance rules, recurring lessons,
  decision rationale). Hand-authored sections are must-keep and are only touched to correct a
  clearly stale fact. This table-plus-one-column is the diff baseline for Action 5, and Routes
  R1/R2 draw their candidates **only** from it — a section with no row is not a candidate, and
  a candidate's size and marks are read off its row rather than argued.

### Action 3 — Recover content lost to older overwriting versions

(Run whenever any `.specify/instructions.md-*` backup exists; this is the repair path for
projects damaged before the non-destructive fix.)

- **Motivation**: earlier versions of the setup script rebuilt the file from the template and
  preserved **only** `## Project Overview`, silently dropping every other hand-authored
  section on each run. A project that ran those versions may have a current base that is
  already missing content which still survives in a backup.
- **Gather the history**: list every `.specify/instructions.md-*` backup (there may be several
  timestamps). Treat the whole set as the recovery source — the most recent backup may itself
  be post-damage, so do **not** rely on it alone; scan older ones too.
- **Detect loss**: diff the current base against the backups. Flag any section or bullet block
  that is present in some backup but **absent** from the current base.
- **Recover — additively, user-authored only**: re-inject flagged content that is clearly
  hand-authored / non-reproducible (custom governance rules, recurring lessons, decision
  rationale, tribal knowledge). Restore the fullest surviving wording and recreate the
  containing section/heading if it no longer exists. Do **NOT** resurrect stale
  auto-derivable facts (old tech-stack numbers, moved doc paths, obsolete feature counts) or
  legacy registry tables — those are refreshed or superseded in Action 5.
- **Reconciliation rules**: when backups disagree, prefer the fullest user-authored version;
  when a backup and the base describe the same item differently, keep the base unless the base
  is a clear truncation/loss, in which case restore from backup. This step is strictly
  **additive** — never delete or shrink current content while recovering.
- **Backup retention rule**: the keep-set is the **newest 5** backups plus every backup that
  still holds a `## ` heading absent from the live file — that heading is unrecovered content,
  so such a backup stays load-bearing however old it is. Name every backup **outside** the
  keep-set in the residual report (Action 7) as the prunable set; naming them is what stops
  `.specify/instructions.md-*` from growing invisibly across runs. This skill never removes a
  backup itself — pruning is the user's call on that list (Archive-not-delete, Reconcile Model
  above).
- If no backup exists, or the base already contains everything the backups do, skip.

### Action 4 — Analyze Project Context

- Read `README.md` to understand the project's purpose and existing features.
- Inspect configuration files (`pyproject.toml`, `package.json`, `pom.xml`, `Makefile`, etc.)
  to determine the tech stack.
- Check `.specify/memory/constitution.md` (if exists) to identify any mandated project rules.
- Check `.specify/memory/features.md` (if exists) for feature status reference.
- **Recall face — existing delegation**: prior project memory is retrieved by the native
  `memory-recall` skill (`.specify/skills/internal/memory-recall/SKILL.md`), which stays at command
  level and is not restated here. Its recalled conventions, user preferences, durable
  decisions, and prior-run outcomes are treated in this workflow as hand-authored /
  non-derivable inputs to Action 5 — must-keep knowledge on par with content recovered from
  backups. Never contradict a recalled user decision — pause and ask the user first
  (user-decision protection, kept).
- **Check `.specify/` Directory**: when referencing the `.specify/` directory (if exists),
  **ONLY** consider the one in the **project root** (same level as
  `README.md`/`pyproject.toml`). Ignore any `.specify/` directories found inside
  subdirectories or submodules (as they belong to other projects).

### Action 5 — Section-by-section refresh

The diff-and-converge pass — operate directly on the base file; a newly created file starts
empty-of-user-content, so its sections are simply filled in.

- **Iterate over the base file's sections in place.** For each existing section, decide the
  action by comparing its *described* state against current project reality (tolerance band
  first):
  - **Matches reality (within tolerance)** → leave it untouched — do not enter the convergence
    set (this includes all hand-authored / non-reproducible sections: custom governance rules,
    recurring lessons, decision rationale).
  - **Drifted / stale** → update *only* the stale facts within that section, preserving the
    surrounding hand-authored prose and structure. Do not rewrite a whole section to change
    one fact.
  - **Placeholders** → replace any bracketed placeholders (`[Brief summary...]`,
    `[Detected tech stack...]`) with concrete details from the analysis.
- **Documentation Map**: verify each row still points to a file that exists in the repo — run
  a scripted existence check (loop every Location cell through `test -e`) instead of
  eyeballing; fix paths that moved and add rows only for genuinely new canonical docs. Also
  re-verify numeric facts quoted in Key Content cells (e.g. feature counts) against their
  source files — these drift silently and have survived previous refreshes.
- **Spec Kit Framework Map**: keep this section in the template's **summary + pointer** shape
  (short highlights paragraph linking `.specify/shared/definitions/framework-map.md`) — never expand it
  back into an inline table or manual. Verify the link target exists; add genuinely new
  framework locations to the external doc, not to this section. If prose here starts
  explaining procedures, compress it back to a pointer.
- **Size-budget convergence (triggered by the setup script's report)**: Action 1's script run
  prints the file's byte size against its budget and, on every run, the section table Action 2
  turns into the observation snapshot. That report is this step's trigger — treat "budget
  reached" as a convergence condition in its own right, not as a cosmetic warning to relay.
  The budget value is owned by the script (`INSTRUCTIONS_BUDGET_BYTES` in `{SCRIPT}`); read it
  from the report and never restate the number here. Both routes below read their candidates
  and their sizes off the snapshot's rows; neither re-measures the file. Two routes, applied
  largest-section-first until the report comes back within budget:
  - **Route R1 — a template-owned section has drifted thicker than the template's own shape.**
    **Filter before reading any prose**: drop every snapshot row marked `placeholder=yes`,
    every row marked `project-owned=yes`, and every row whose `delta` is not positive. Both
    marks are machine-checked columns of the script's table — the placeholder discriminator is
    a `[`…`]` or `{{VAR}}` token surviving in that section's *rendered template* version — so
    the filter is a lookup on the row, never a judgment call. What survives, largest `delta`
    first, is R1's entire candidate pool. Each surviving row is a template-owned section whose
    live version *may* have accumulated inline detail the template deliberately keeps out;
    compress it back to the template's summary + pointer form. Two filters decide whether it
    actually may, and skipping either one turns R1 into deletion:
    - **Exclude project-filled sections first.** A section whose template version still
      carries a placeholder token (`[Bracketed ...]`, `{{VAR}}`) is a *scaffold the project is
      supposed to fill*, so live-larger-than-template is its correct end state, not drift —
      `## Documentation Map`, `## Tech Stack & Resources` and `## Project Overview` are all of
      this kind, and on a mature project they are among the largest sections in the file.
      Compressing one back to the skeleton deletes real project content. That is why the
      exclusion above is the route's opening act rather than a check applied to a shortlist
      somebody already picked.
    - **Then verify the pointer target carries the detail** you are about to remove. Open it
      and confirm. If it does not, the section is **not** an R1 candidate: either leave it
      alone, or move the detail into the owning document first (R2's mechanism) and then
      compress. A live section that is thicker because it holds information nobody else holds
      is a gap in the owner document, not drift — and the fix is to fill the owner, never to
      shrink the instruction.
  - **Route R2 — a project-specific section has grown past the relocation threshold.**
    Project-owned sections are exactly the snapshot's `project-owned=yes` rows (any `## `
    heading the template lacks, e.g. `## Recurring Operational Lessons`); they have no
    template shape to converge to, so they grow without bound as lessons accumulate, and they
    are typically the single largest source of inflation. When one exceeds **4 KB**, promote
    its body to an owner document under `docs/` — reusing the owner the section already names
    when it names one — register that document as a Documentation Map row, and leave behind a
    normative one-line summary plus the pointer. **The migration MUST be mechanical, never
    transcribed by hand**: script-extract the section's bullets, write them into the owner
    document, then assert both directions before deleting anything from the instructions file
    — every extracted bullet landed in the owner document exactly once, and each original
    bullet string is findable there. Hand transcription silently drops items, and the drop is
    invisible afterwards because the instructions file looks intentionally short.
  - Report which route each shrunken section took, and leave sections untouched when neither
    route applies — a section that is within its shape is tolerated, not a candidate.
- **Add missing scaffolding**: if the latest `.specify/templates/instructions-template.md`
  defines a section that is **absent** from the base, insert it at the structurally
  appropriate place. Never remove a base section merely because the template lacks it (e.g.
  project-specific sections like `## Recurring Operational Lessons` are kept — kept does not
  mean unbounded; Route R2 above is how such a section is converged without being dropped).
- **Supersede legacy registry/Git Workflow sections**: bases refreshed by older template
  versions may still carry a `## Resource Registry` section (`### Agents` / `### Skills` /
  `### Tools` marker-delimited tables) and an inline `## Git Workflow` block. These were
  **machine-maintained, not user-authored** — they no longer belong in the file. Converge
  them, don't preserve them:
  - Migrate the inline `## Git Workflow` block's branch roles into `docs/git-workflow.md`
    first (create it from the `git-utils` skill's asset template if absent — the branch
    table is real data and MUST NOT be lost), then replace the section with the template's
    pointer paragraph.
  - Replace the registry tables with the template's `## Skills & Tools` pointer section. The
    rows are re-derivable from `.specify/skills/` and `.specify/memory/tools/` directories, so
    dropping them loses nothing; note the removal in the residual report.
  - Never delete hand-authored rows that clearly differ from machine-generated shape (e.g. a
    user-written note under `### Tools`); move such content into the owning section or report
    it as pending.
- **Conflict policy**: when the fresh analysis conflicts with clearly user-authored content,
  keep the user-authored content and update only the stale factual item (mirrors the
  Reconcile Model conflict policy).
- **Incorporate user input**: if the processed arguments provided specific instructions or
  context, integrate them into the relevant sections.
- **No wholesale replacement**: modify only what mismatches; everything else stays
  byte-for-byte.

### Action 6 — Validation

- Ensure the file is well-formatted Markdown.
- Verify that the resulting instructions clearly describe the project to a fresh AI instance.
- **Coverage check**: compare the result against **every** `.specify/instructions.md-*`
  backup by **set membership of section headings** (`grep '^#' | sort` on both sides, then
  `comm`), not positional line diff — a reordered section is not a lost section, and a
  positional diff trains the agent to dismiss its own warnings. Exempt `| None yet. |`-style
  registry placeholder rows from the comparison. Confirm no user-authored section present in
  the history was silently dropped; if any heading is genuinely missing, restore it from the
  backup before finishing.
- **Every item in the difference needs an attribution, not a blanket assurance.** Two more
  shapes besides reordering are convergence rather than loss, and both land in the
  `comm -23` difference: a **folded sub-heading** (a `### Loop A` / `### Loop B` pair folded
  into a compact parent section that the template ships in that shape) and a **de-decorated
  heading** (a parenthetical provenance note dropped from a heading whose content moved to an
  owner document). Saying "reordering is not loss" and then declaring nothing lost is not
  evidence — walk the difference and give each item one of: the owner document path that now
  holds it (Route R2), the section that superseded it (Route R1 or the template's own compact
  form), or "genuinely missing" plus the restore. An item with no attribution is treated as
  missing until one is supplied.

### Action 7 — Report (mandatory artifact — residual report)

- Report the full path of the instructions file (`.specify/instructions.md`).
- Structure the summary as a residual report: **converged** (sections with stale facts updated
  / new template sections added / sections shrunk by Route R1 or R2, each naming its route
  and, for R2, the owner document that received the body), **tolerated** (sections verified
  and left untouched), **recovered** (content restored from backup history), **pending**
  (items needing user decision, if any). If nothing converged, state plainly that all
  sections were within tolerance.
- **Report the size outcome**: bytes before → bytes after, the budget as the setup script
  stated it, and the resulting headroom. When the run started over budget, say whether it
  ended within budget; when it did not, name the sections still over and what a further pass
  would have to move — an unconverged budget is a pending item, not a silent one.
- **Name the prunable backups**: list every `.specify/instructions.md-*` backup that Action 3's
  retention rule placed outside the keep-set. The rule itself is owned by Action 3; this
  bullet only carries its output into the report, so the history's growth stays visible to the
  user rather than accumulating silently.
- Confirm that symlinks for Copilot, Qoder, and Claude have been established (or explicitly
  report warning/fallback actions if the setup script partially failed).
- Ask the user for feedback on anything unclear or incomplete so the next run can iterate.

### Action 8 — Record run outcome

**Record face — existing delegation** (stays at command level; the memory skill's rules are
not restated here): the native `memory-record` skill
(`.specify/skills/internal/memory-record/SKILL.md`) persists this run's outcome — skipped for trivial
no-op runs where all sections were within tolerance and the arguments were empty. What this
workflow hands it:

- **Session scope**: a working note of this run's residual report (converged / tolerated /
  recovered / pending) so the next run can recall what changed and why (feeds Action 4's
  recall on the next run).
- **Knowledge scope**: when the run surfaced a durable convention, user preference, or
  decision (including one carried by the processed arguments), upsert it as long-term
  knowledge so future refreshes classify it as must-keep.

## Boundaries

- User-input processing, the frontmatter `scripts:` wiring, and the wrap-up lifecycle steps
  (Artifact Commit, Feedback, Documentation) stay with the command template
  `.specify/templates/commands/instructions.md`; this skill starts from the processed intent and ends
  before the wrap-up wiring.
- The memory face stays with the existing `memory-recall` / `memory-record` skills (Action 4 /
  Action 8) — this skill neither duplicates nor replaces them.
- Route R2 creates and registers the owner document itself — that is in scope here; broader
  docs-tree governance remains `/speckit.docs` territory.
- Backup pruning is never executed here — Actions 3 and 7 only name the prunable set; removal
  is the user's call (Archive-not-delete).

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-instructions" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-instructions" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-instructions" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
