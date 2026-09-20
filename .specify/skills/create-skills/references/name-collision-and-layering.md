# Name collisions across SSOTs, and layered Skills

Two situations that the main workflow only points at: a target Skill name that
already exists **somewhere else**, and the layered shape that such a collision
often resolves into.

## 1. Cross-SSOT name collision

`.specify/skills/<name>/SKILL.md` being absent does **not** mean the name is free.
The same name may already be an entity in another single-source-of-truth (SSOT),
with live wiring pointing at it. Creating a second entity silently produces two
Skills with the same `name` and overlapping triggers — the agent then picks
unpredictably between them.

### Scan before creating (Step 1)

Check every location the host machine can load Skills from, not just the current
project:

| Where | What to look for |
|-------|------------------|
| `<project>/.specify/skills/<name>` | entity **or** symlink — resolve it (`readlink`) and note the real owner |
| global/user skills library (e.g. a `config/skills/<name>` managed tree) | entity owned by a config repo rather than a code project |
| agent load directories (`~/.<agent>/skills`, host app skill dirs) | links named `<name>` pointing at any of the above |
| other code projects' `.specify/skills/<name>` | the same capability vendored per project |
| name-field scan (every discovered `SKILL.md` frontmatter `name`, host app skill DBs/JSON) | a `name` value already claiming the word (directories are the registry — scan them) |

Report the finding as **entity location + who references it**. That pair decides
the path below; a bare "it exists" is not enough to choose.

### Decision paths

| Path | When | Consequence |
|------|------|-------------|
| **Improve in place** | same scope, same purpose | go to `improve-skills`; do not create a duplicate |
| **Adopt the existing entity** | the entity belongs elsewhere but is generic and portable, and its owner should keep it | leave the entity, wire a link from the current scope so directory discovery finds it; no copy |
| **Split into layers** | the entity's home cannot hold everything the capability needs (see §2) | rename/keep the lower layer where it lives, create a front door in the current scope |
| **Rename the new Skill** | genuinely different capability that merely wanted the same word | pick a distinct name; note the boundary in each SKILL.md's description so triggers stay disjoint |

Ask the user which path applies **only** after presenting the scan result and the
consequence of each path. Never resolve a collision silently.

## 2. Layered Skills: portable lower layer + local front door

The typical trigger: the capability's implementation lives in a project that is
published or shared, while the working setup needs machine-local or
organization-internal material (absolute paths, credential retrieval, private
commands, internal service names) that must not be published.

**Split of responsibility**

| Layer | Holds | Must not hold |
|-------|-------|---------------|
| Lower layer (in the published project) | command/API surface, options, coverage, practices, pitfalls — the single source of truth for details | machine paths, credential mechanics, private commands, internal names |
| Front door (in the private/local scope) | preflight checks, intent routing, local paths and credentials, private commands, orchestration, safety rules | copies of lower-layer detail |

**Authoring rules for the front door**

- State the delegation contract explicitly: *"this Skill does not maintain any
  lower-layer detail; command names, options and return shapes come from
  `<lower-layer>`"* — otherwise the two copies drift.
- Include a **preflight** block that verifies the lower layer is actually
  reachable (repo root variable set, interpreter present, skill directory
  exists) and stops with a clear message when it is not. A front door whose
  delegate is missing must fail loudly, not improvise.
- Reference the lower layer by resolved path (via an environment variable with a
  documented local default), and keep a **document map** of which lower-layer
  file answers which question, so the agent reads one file instead of all.
- Name the layers for their role (e.g. `<domain>-<semantic>` for the front door,
  `<domain>-py-<kind>` for a library-backed lower layer) so a reader can tell
  which one to edit.
- Keep the counting/coverage numbers that differ between layers (public vs
  local surface) in the front door, with the command that reproduces them.

**Wiring rule**: point every load directory at the **front door only**. Linking
both layers into the same agent restores the ambiguity the split was meant to
remove.

## 3. Topology and link integrity (Step 6)

When the host keeps a skill-topology registry (a map/manifest of skill locations
and link counts) or fans skills out to several agent load directories, a create /
rename / relink is not finished until:

1. the registry is updated (entries, per-target link counts, and any note that
   records why the topology changed);
2. a dangling-symlink scan over every load directory returns **zero** — a rename
   in the entity's home silently breaks every link that pointed at the old path;
3. each load directory resolves to the new content (grep a distinctive string
   from the new `SKILL.md` through the link, not just `ls`);
4. host registries that cache the description (skill DBs, catalog JSON) are
   refreshed, so discovery does not route on stale text.

Residual-reference scans MUST cross skill boundaries: a removed or renamed path
is often referenced from a **sibling** Skill's references or generator, and
grepping only the Skill you changed misses it.
