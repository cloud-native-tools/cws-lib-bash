# Target Resolution (目标解析) — SDD-driving external skills

Single source of truth for how the three SDD-driving external skills resolve the **target
project**. Resolution depends on the skill's dependency class, not on one universal rule.

## Skill dependency classes

### `sdd-project-setup` — no `.specify/` dependency

- Explicit target (local path or complete remote triple) wins.
- No target → the current project: `git rev-parse --show-toplevel` from the session working
  directory; a non-git directory → the session working directory.
- It **MUST NOT require `.specify/`** and MUST NOT use an upward `.specify/` search to pick a
  target: setup is the skill that creates/refreshes the `.specify/` baseline at the target.
- A project with no `.specify/` is a valid setup target.

### `sdd-house-keeping` / `sdd-loop-driver` — strong `.specify/` dependency

These two skills MUST operate on an initialized Spec Kit project; they cannot create the
baseline.

- Explicit target (local path or complete remote triple) wins. For a local explicit path,
  start the search at that path (if it is a file, its parent). With no target, start at the
  session working directory.
- Walk **upward** from the start directory and return the first ancestor `p` where:
  - `p/.specify/` is a directory, and
  - `p` is not named `.specify`, and
  - `.specify/` looks like a Spec Kit store: it contains at least one of `.specify/memory/`,
    `.specify/scripts/`, `.specify/templates/` (this skips a stray empty `.specify/`).
- **If no such ancestor is found, refuse to execute.** Report the start path searched and
  the remediation:
  - run `sdd-project-setup` in `install` mode, or
  - run `specify init <project-dir>` directly;
  - if the caller wants automatic remediation, hand off to `sdd-project-setup`.
- A `.specify/` directory is never itself a project root; its parent is.
- For a **remote** target, run the same upward search on the execution side before any
  mutation (see the remote probe below). If it returns empty, refuse and hand off to
  `sdd-project-setup`; do not guess a local project.

## Remote target-root probe

Run on the execution side as the run user; the printed path is the resolved project root,
which MUST be used as `<project-dir>` for subsequent commands:

```bash
ssh <alias> "su - <run-user> -c 'p=<project-dir>; while [ \"$p\" != \"/\" ] && [ ! -d \"$p/.specify\" ]; do p=$(dirname \"$p\"); done; [ -d \"$p/.specify\" ] && echo \"$p\"'"
```

Empty output = no `.specify/` ancestor → refuse and hand off `sdd-project-setup`.

## Common rules

- Resolve to an absolute path before any read or write; record it in the run
  report/credential.
- **Reject a root whose basename is `.specify`.** A `.specify/` directory is a runtime
  store, never a project root.
- **Warn, then continue**, when the resolved target is the framework source repository (the
  root owns `templates`, `skills`, `shared`, `scripts`, `src/specify_cli`) and the target was
  not explicit.
- **No silent local fallback for a partial remote triple**: if only the host or only the run
  user is given, ask one clarifying question.
- **No execution-side substitution**: a remote target is scanned and mutated only on the
  execution side (see `.specify/shared/workflow/execution-topology.md`).

## Mode and tool defaults (owned by each skill)

Target resolution is shared; **mode** and **tool** defaults are not:

- `sdd-project-setup`: mode from the S1 grade (absent=`install`, degraded/partial=`refresh`,
  complete=`bootstrap-content-check`); tool default `all`.
- `sdd-house-keeping`: mode default `check`; explicit `cleanup` only when the user asks for
  cleanup; no re-init.
- `sdd-loop-driver`: no install mode; the target must already be an initialized project.

## Verification

Contract tests assert the dependency-class split: setup has no `.specify/` requirement and no
upward `.specify/` search; house-keeping and loop-driver require the upward search and the
refuse/handoff behavior.
