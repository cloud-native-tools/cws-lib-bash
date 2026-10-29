# Directory Governance (目录治理)

Single source of truth for **how a directory may come into existence** in this repository: its
name, its registration, and — when it holds temporary data — its ignore rule. Constitution
Principle XVII and the ambient `## Temporary Directory Discipline` section point here; this file
owns the rules, those surfaces only route to it.

What each directory *contains* is owned where the directory lives (§ 2). This file owns the
obligation that a meaning exists and is reachable; it never copies an area's directory table.

## 1. Naming rules

| Rule | Requirement |
|---|---|
| Lowercase kebab-case | A directory name MUST match `^[a-z0-9]+(-[a-z0-9]+)*$` |
| One concept per directory | The name states the concept held, not its consumer or its stage |
| Path is semantic | `<area>/<topic>/` MUST read as "the `<topic>` of `<area>`" |
| No placeholder names | `tmp/`, `temp/`, `scratch/`, `misc/`, `stuff/`, `new/`, `old/`, `test2/` MUST NOT be created |
| Mandated names exempt | Names dictated by a tool or framework MUST NOT be renamed (`src/`, `tests/`, `.github/`) |

A grouping directory that would hold exactly one child MUST NOT be created; put the child where
the reader would look for it.

## 2. Where a directory's meaning is owned

Each area's directory map lives in its own owner document. This table indexes the owners; it
does not restate their rows.

| Area | Directory map owner |
|---|---|
| Repository root and source directories | `.specify/instructions.md` § Tech Stack & Resources → Key Directories |
| Documentation space | `docs/concepts/documentation-model.md` |
| Framework runtime layout | `.specify/shared/definitions/framework-map.md` |
| Feature artifacts | `.specify/shared/definitions/framework-map.md` (Feature specs row) |
| Agent / team / skill layers | `.specify/shared/definitions/agent-definitions.md` + `framework-map.md` |
| Temporary and scratch data | `.specify/shared/guidelines/temp-directory-discipline.md` |

## 3. Registration obligation (创建即登记)

- A new top-level directory, or the first directory of a new kind under an existing tree, MUST
  be added to its area's map in the same change that creates it. A directory whose meaning is
  documented nowhere MUST NOT be created; "obvious" is not documentation.
- Renaming or removing a directory MUST update the map and every link that referenced it in the
  same change.
- Generated or tool-managed trees (dependency installs, caches, build output) are exempt from
  registration and MUST be covered by `.gitignore` instead.

## 4. Temporary directories

- A temporary or scratch directory MUST use a sanctioned root and MUST be matched by
  `.gitignore` before its first write inside the repository. Roots, the pre-write check,
  cleanup, and exceptions are owned by `.specify/shared/guidelines/temp-directory-discipline.md`.
- A temporary directory MUST NOT become permanent by being left in place: it is either
  registered under § 3 or removed when its work item ends.

## 5. Runtime roots（运行期根）

A skill or engine that must persist runtime state (worktrees, caches, per-run state, scratch)
MAY own one runtime root. A runtime root is lawful only when all three hold:

- It is declared by its owning skill or contract, and only that owner writes there.
- Its location is fixed by that owner; ad-hoc alternatives (`tmp/`, `scratch/`, `work/`,
  `state/` at an arbitrary level) MUST NOT be created.
- It lies outside every repository, or — when the environment forces it inside one — it is
  matched by `.gitignore` before its first write.

Registered runtime roots:

| Root | Owner | Lifecycle | What it holds |
|---|---|---|---|
| `<repo>/.specify/.tmp/sdd-loop/` | `skills/external/sdd-loop-driver` (`.specify/scripts/line-registry.py`, `references/dispatch-recipes.md`) | temporary — covered by `.specify/.gitignore`'s `.tmp/` rule; cleaned up when the work item ends | per-line worktrees, cache, and tmp |
| `<repo>/.specify/state/` | the same skill | long-lived archive — one file per line (`<line_id>.md`), never one shared aggregate | per-line state spines |
| `$XDG_STATE_HOME/spec-kit/lines/` (fallback `~/.local/state/spec-kit/lines/`) | the same skill | long-lived archive, outside any repository | environment-level Line Registry entries, locks, manifests, and reservations |

Runtime data belongs inside the `.specify/` namespace and is split by lifecycle: temporary
data goes to `.specify/.tmp/`, long-lived state goes to `.specify/state/`. The retired
`.spec-kit/` root recorded by older design artifacts MUST NOT be re-created. The loop driver
MUST NOT create runtime directories outside these roots, and no other component may borrow
them. A target project's own directory-governance document wins for that project when it
declares different roots.

## 6. Enforcement boundary

- Enforcement is review plus targeted contract tests
  (`tests/contract/test_directory_governance.py`).
- This discipline MUST NOT be used to justify a directory scanner, a registry generator, a
  generated directory index, or any new tracking engine (Constitution Principle IX).
- Where a tool's mandated layout conflicts with § 1, the tool wins and the exception is recorded
  in the area's map.

## 7. Boundaries with adjacent disciplines

- `.specify/shared/guidelines/temp-directory-discipline.md` — owns temp-dir roots, the pre-write ignore
  check, cleanup, and exceptions; this file only routes to it.
- `docs/concepts/documentation-model.md` — owns the `docs/` directory taxonomy and the notes
  lifecycle.
- Constitution Principle X — owns file naming; this discipline extends the same path-is-semantic
  logic from files to directories.
