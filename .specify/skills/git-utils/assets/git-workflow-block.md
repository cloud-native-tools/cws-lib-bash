<!-- Full-file template rendered by the git-utils skill (scope A) into
     ${SKILL_WORKDIR}/.specify/workflow/git.md (created when absent; when the file
     already exists, only the managed block between the markers below is replaced —
     see references/instructions-lookup.md).
     The workflow model is a FRAMEWORK-LEVEL DECLARATION under Spec Kit (not a developer's
     personal habit: unattended mechanisms follow it too). First fill the
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
     Fill the `Closeout` row with exactly one of `commit+merge+push` / `commit+merge` /
     `commit-only` / `ask`, and the `Closeout remotes` row with a comma-separated list of
     remote names, or an explicitly empty list. The close-out sequence itself is owned by
     the git-utils skill (scope A, operation `closeout`) and is derived per invocation —
     render the two rows, never a per-model close-out table.
     Always replace <DATE> with the run date and record project-specific cautions (sync
     peers, remote roles) as ⚠ lines when they exist. Keep the marker comments byte-exact. -->
# Git Workflow (Spec Kit framework)

Machine-maintained by the `git-utils` skill (scope A) — the managed block below is the
**single source of truth** for the git workflow **under the Spec Kit framework** — the
declared model, branch structure, and close-out discipline followed by both human
developers and the framework's unattended mechanisms; do not edit it by hand.
`.specify/instructions.md` carries only a pointer to this file.

<!-- GIT_WORKFLOW_START -->
<!-- Workflow model is a framework-level declaration under Spec Kit (menu: single-branch / dual-branch / temp-branch / MAIN-PRE-DEV three-tier); the declaration below records THIS project's choice, followed by its operating rules. While no workflow is established yet, keep the `None yet.` line as the model declaration so Bootstrap can detect the unfilled state. -->
- **Workflow model**: <MODEL>
<MODEL_SPECIFIC_LINES>
- **Closeout**: <CLOSEOUT>（四值闭集 `commit+merge+push` / `commit+merge` / `commit-only` / `ask`；缺失或未填即取 default `ask`，不得从相邻行推断取值）
- **Closeout remotes**: <CLOSEOUT_REMOTES>（显式空列表 empty 或未填 absent 即 "no pushable remote"，推送步退化为 skipped 并在报告说明原因）

- **Last updated**: <DATE>
<!-- GIT_WORKFLOW_END -->
