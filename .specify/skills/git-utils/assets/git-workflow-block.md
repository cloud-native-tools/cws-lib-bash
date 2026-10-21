<!-- Full-file template rendered by the git-utils skill (scope A) into
     ${SKILL_WORKDIR}/docs/git-workflow.md (created when absent; when the file
     already exists, only the managed block between the markers below is replaced —
     see references/instructions-lookup.md).
     The workflow model is a PER-PROJECT CHOICE (suggestion, not mandate). First fill the
     `Workflow model` declaration line with the confirmed model (menu: single-branch /
     dual-branch / temp-branch (trunk + short-lived feature branches) / MAIN-PRE-DEV three-tier),
     then render ONLY the rows for that model:
       - three-tier: replace <MAIN> / <PRE> / <DEV> with the confirmed branch names,
         <MAIN_TRACKING> / <PRE_TRACKING> / <DEV_TRACKING> with each branch's upstream
         (or `-` when none), and keep/adjust the sync & merge chain lines.
       - other models: replace the bracketed guidance line with the model's own branch
         conventions (e.g. temp-branch: trunk branch + tracking + feature-branch naming
         and merge-back rule; dual-branch: the two long-lived branches and their roles;
         single-branch: the single trunk).
     Always replace <DATE> with the run date and record project-specific cautions (sync
     peers, remote roles) as ⚠ lines when they exist. Keep the marker comments byte-exact. -->
# Git Workflow

Machine-maintained by the `git-utils` skill (scope A) — the managed block below is the
**single source of truth** for this project's declared git workflow model and branch
conventions; do not edit it by hand.
`.specify/instructions.md` carries only a pointer to this file.

<!-- GIT_WORKFLOW_START -->
<!-- Workflow model is a per-project choice (menu: single-branch / dual-branch / temp-branch / MAIN-PRE-DEV three-tier); the declaration below records THIS project's choice, followed by its operating rules. While no workflow is established yet, keep the `None yet.` line as the model declaration so Bootstrap can detect the unfilled state. -->
- **Workflow model**: <MODEL>
<MODEL_SPECIFIC_LINES>

- **Last updated**: <DATE>
<!-- GIT_WORKFLOW_END -->
