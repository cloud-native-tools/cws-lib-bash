# dependency model

## What an edge is

An edge is a **graded, evidence-backed claim** that one repo depends on another.

**无证据不入图 / no evidence, no edge.** Repo names, descriptions and directory
layout are never treated as evidence. Only what was read out of the working tree
counts.

| Type | Evidence grade | Source | Confidence |
|------|----------------|--------|------------|
| `submodule` | `实测` (measured) | `.gitmodules` declares `path` + `url` **and** the gitlink pins a sha | The dependency is a build-time contract; the exact commit is known |
| `manifest` | `半实测` (semi-measured) | A manifest line contains one of `internal_origin_patterns` | A coupling is declared; the version is *not* resolved |

## Edge identity

A `submodule` edge is identified by **(from, to, mount_path)** — not just the repo
pair. The same provider mounted at two paths in one consumer is two edges, and the
mount path is what a human needs to locate it. Recorded fields:

| Field | Meaning |
|-------|---------|
| `from` | Consumer (normalized origin) |
| `to` | Provider (normalized origin, from the `.gitmodules` url) |
| `mount_path` | Where it is mounted inside the consumer |
| `pinned_branch` | `submodule.<name>.branch`, when declared |
| `pinned_sha` | The gitlink commit — the actual pinned version |
| `state` | `ok`, `+` (checkout ≠ gitlink), `-` (uninitialized), `U` (conflict) |
| `observed_in` | Which environment this was read from |

Because `pinned_sha` is per-consumer, **the same provider is usually pinned at
different commits by different consumers.** That spread is a first-class finding: it
tells you how far behind each consumer is, and it is invisible from the provider side
without this graph.

## Both directions are stored

`depends_on` and `depended_on_by` are both materialized on every node. The reverse
direction is not left to be derived at read time, for two reasons:

1. The question "who breaks if I change this?" is asked far more often than the
   forward one, and it must be answerable by opening one file.
2. `git-submodule-edit` requires every PR to list affected consumers, but has no data
   source for that list. This graph is that source.

Per-project documents therefore carry two tables — 依赖 and 被依赖 — mirroring the
two adjacent columns (`直接依赖` / `被组内依赖`) used by hand-curated relations tables.

## Self-declarations are not dependencies

A repo names its own origin in ordinary places:

- `go.mod` → `module git.example.com/org/repo`
- `package.json` → `"repository": { "url": "git@git.example.com:org/repo.git" }`

Text-matching a manifest against internal origin patterns hits these. Any manifest
edge that resolves back to the declaring repo is dropped. Skipping this filter
produced both a large volume of noise and a false dependency cycle.

## Manifest edge resolution

A manifest line is matched against known node keys; the **longest** matching key wins
(so `org/repo-extended` is not mis-attributed to `org/repo`). If nothing matches, the
edge is kept with `to: null` — the coupling was observed, the target simply is not in
the managed scope. Unresolved edges are shown as `（未解析）` rather than silently
discarded, because a dependency on something outside scope is itself worth knowing.

Manifest edges deliberately stop at declaration:

- version constraints are not parsed
- lock files are not followed
- transitive closure is not computed

Anything beyond "a coupling is declared here" needs the language's own tooling and
would be a false promise at this grade.

## Topological order

`deps` emits a dependency-first order: a repo appears only after everything it
depends on. Use it to sequence multi-repo upgrades.

Cycles are reported explicitly and **suppress** the order rather than producing an
arbitrary one. A cycle is either a spurious manifest edge (check for a
self-declaration variant the filter missed) or a genuine circular submodule
relationship that needs breaking regardless.

## Relationship to curated relations views

This graph is derived from **workspace evidence on machines you control**. A
hand-curated relations view derived from a code-hosting platform answers a different
question at a different granularity (all repos in an org, including ones never
checked out) and may encode relation types this graph cannot observe — runtime calls,
image builds, component evolution, fork lineage.

The two are complementary and must not overwrite each other. `--cross-reference`
cites the curated view from each generated document; the citation is emitted **only
when the target file exists**, so groups without one get no dangling link. Nothing in
this skill writes into the curated view.
