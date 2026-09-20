# Decommission & Wiring — retiring the source as an independent skill (Phase 7)

A merge that absorbs the source's content but leaves the source **wired** has not consolidated
anything: two skills still exist, both still match the same triggers, and the agent may load
either. Full replacement requires retiring the source's independent existence.

This is the host-specific part of the merge. **This skill is environment-agnostic and hardcodes
no agent paths** — it names the *classes* of cleanup and delegates the actual per-agent work to
the host's agent-management capability.

## Scope is set by the Phase-1 source classification

| Source class | Form carriers | Local wiring | Upstream / marketplace entity |
|--------------|---------------|--------------|-------------------------------|
| Peer / global skill (host-managed) | Remove | Remove fully | n/a |
| Externally-managed marketplace / upstream skill | Remove local copies | Remove local wiring only | **Leave intact — not yours to delete** |

The single most common mistake is deleting an upstream/marketplace entity that the host does
not own. If the source came from a marketplace/CLI install, its upstream entity is self-managed;
you remove only the **local wiring** that made it independently discoverable.

## Cleanup surfaces (delegate, don't hardcode)

Ordered from safest to most destructive. Confirm the destructive ones with the user first.

1. **Staged form carriers** — any raw source files copied into the target during rewrite.
   Remove with `git rm` (recoverable from history). Safe once Phase 5 passed.
2. **Load-directory symlinks** — the source's entries in each agent's skills load directory.
   In an environment with an agent-management front door (e.g. a `manage-agents` /
   `profiles-agents` skill and its `wire_agents.sh`-style scripts), **delegate** symlink
   removal to it — do not enumerate per-agent paths inside a merge. Destructive → confirm.
3. **Declarations that name the source by slug** — two opposite operations, both required:
   - **Re-point, don't delete**: agent skill declarations (`skills:` frontmatter and any
     `## Skill Enablement` row) naming the source must be changed to name the **target**.
     Deleting them instead silently strips the capability from that agent, and a dangling slug
     breaks the host's skill-enablement contract (spec-kit:
     `tests/contract/test_agent_skill_enablement.py` asserts every declared slug resolves to an
     installed skill).
   - **Register the retirement**: when the host repo ships an obsolete-asset reclaim registry,
     add the retired name to it (spec-kit: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`,
     covered by `tests/contract/test_cleanup_obsolete_assets.py`). An init/upgrade that copies
     additively never deletes, so an unregistered retirement is **resurrected in every upgraded
     workspace** — the retired skill keeps competing for its old triggers.
4. **Registry rows** — description-caching or registry-driven loaders (e.g. a JSON registry an
   app reads at startup) need their source entry removed. Destructive → back up the registry
   file first, then remove the one entry.
5. **Database records** — DB-registered loaders (e.g. a sqlite skills DB with a full-text
   index) need the source's row **and** its FTS/index row removed, then the index rebuilt and
   an integrity check run. Destructive → back up the DB first; confirm.
6. **Topology / inventory docs** — any doc that records "which skills are wired where"
   (counts, per-agent link tables, an `[EXT-*]` inventory) must be updated to reflect the
   source's removal so the docs don't drift from reality.

## Danger-op discipline

Symlink removal, registry edits, and DB row deletion are **destructive and irreversible**. Per
the host's confirmation-gate convention:

- Enumerate the exact targets (which links, which rows, which files) and **confirm with the
  user before executing**.
- **Back up** any registry file or DB before editing (a timestamped copy).
- Prefer `git rm` over `rm` for tracked files so the change is reversible from history.
- Never batch a destructive wiring change silently inside an otherwise routine edit.

## Verification after decommission (feeds Phase 8)

- **Dangling-link scan** across all load directories returns zero (no symlink now points at a
  removed source).
- The **target** still resolves in every load directory it should (the decommission removed the
  source, not the target).
- Description-caching registries **refreshed** (app may need restart to reload).
- **No declaration still names the retired slug**, and the host's skill-enablement /
  obsolete-asset contract checks pass (spec-kit: `pytest tests/contract/ -q -k
  "skill_enablement or obsolete_assets"`).
- **No residual reference** to the source skill name anywhere in the target's docs or the
  host's topology docs (grep the source name; expect only intentional "merged into …" notes).
- DB integrity check passes; index rebuilt.

## Mirror sync

Applies only when the host keeps a canonical↔mirror pair for skills (spec-kit: `skills/` is
canonical, `.specify/skills/` is the mirror). Sync with the host's own tool — **never** hand-copy,
which is how the two trees silently diverge:

```bash
python3 scripts/python/sync-mirrors.py --write  --only skills/<target>
python3 scripts/python/sync-mirrors.py --check  --only skills/<target>   # must report no drift
```

Two host gotchas worth expecting: the sync is additive and never deletes, so a mirror directory
left behind by the decommission must be removed explicitly; and pre-existing root-owned files
under the mirror make `--write` fail per file (the engine keeps going, then exits non-zero with a
`FAIL` summary) — fix ownership and re-run rather than trusting a partial pass.

## Record the decommission

Leave a durable trail: in the host's topology/inventory doc, note that the source was merged
into the target on <date>, what was removed (links / DB row / registry entry), and what was
left intact (upstream entity). This prevents a future session from "repairing" the intentional
removal or re-wiring the retired source.
