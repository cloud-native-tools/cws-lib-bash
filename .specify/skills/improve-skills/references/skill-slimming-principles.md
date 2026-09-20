# SKILL.md Slimming Principles

`SKILL.md` is a **contract**, not a manual. Implementation details belong in `./references/`. This document defines what counts as contract content, what counts as detail, and how to slim a Skill without losing information.

Apply these principles whenever an improvement loop touches `SKILL.md`, especially when the file has grown past the point where a reader can grasp the workflow at a glance.

The verdict is **not** a judgement call. Run the gate and read its findings:

```bash
python3 "${SKILL_HOME}/scripts/skill-shape.py" <path/to/SKILL.md>
# exit 0 = contract-shaped; exit 10 = blocking findings (slim before finishing the loop)
```

---

## Principle 0 — The budget binds what you ADD, not only what you remove

Slimming has two directions, and the authoring direction is the one that gets skipped:

- **Cleanup** — relocate manual content that is already in the body (Principles 1–7 below).
- **Authoring** — new detail written *during this loop* defaults to `references/` (explanations,
  worked examples, checklists) or `scripts/` (deterministic logic). `SKILL.md` gains only
  contract lines: a step heading + one-sentence goal, a hard rule, a decision branch, a
  resource-index row, a pointer with an anchor.

A correct, freshly-written 30-line command example is still L2 material. "It is new and it
works" is not an argument for putting it in the contract.

**Measured failure case (2026-08)**: this rule previously read "evaluate whether *existing*
sections should be moved out". A loop that added a decomposition capability to a skill
authored ~190 new lines of worked examples and command sequences and remained fully
compliant with the rule as written — the body reached **10,334 tokens (2× the L1 budget) with
42% of its lines inside code fences**, and the reviewer, not the loop, caught it. Three
compounding causes, all now closed:

1. **Scope** — the rule only governed pre-existing content (fixed by this principle).
2. **Placement** — the rule sat as one bullet among eleven inside the longest step of a body
   that was itself 56% over budget, i.e. the attention low-zone its own
   [constraint-placement.md](./constraint-placement.md) measures at ~76% compliance (fixed by
   a consolidated `## Hard Constraints` block placed late in `SKILL.md`).
3. **No objective condition** — the quantitative facts lived only here in L2, so a loop that
   never opened this file never saw a number and "slim enough?" had no verdict (fixed by
   `scripts/skill-shape.py` plus a mandatory gate in the validation step).

The general lesson: *a discipline that depends on the agent voluntarily reading a reference
is not enforced.* Give it a number, a script, and a late-positioned rule.

**Failure mode prevented**: the body grows unboundedly through additions while every
individual edit passes review.

---

## Principle 1 — Keep `SKILL.md` to contract-only content

`SKILL.md` should answer four questions and stop:

1. **Who am I?** — frontmatter (`name`, `description`, `version`, `skill_id`).
2. **What resources exist?** — a flat resource index pointing to references, scripts, assets, templates.
3. **What is the workflow skeleton?** — ordered step headings, each with a one-sentence goal and a link to the reference that holds the details.
4. **What is non-negotiable?** — strict requirements (absolute rules) and conventions (default behaviors / decision branches).

Move everything else out:

| Content type | Belongs in |
|--------------|------------|
| How-to checklists for a single step (e.g. "选择输出格式 / 链式调用 / 解析返回") | A reference; SKILL.md keeps only the step heading + link |
| Error tables (symptom / cause / fix) | A reference; SKILL.md keeps a single sentence "report the error verbatim and consult the reference" |
| Comparison tables of frequently-confused command pairs | A reference such as `common-workflows.md` |
| Environment-detection scripts (`uname -s` branches, WSL bridges, OS matrices) | Either a reference or removed entirely (see Principle 5) |
| Install/bootstrap commands | Removed; the user installs the underlying CLI before invoking the Skill |
| Intra-domain priority / routing tables | The reference for that domain |

**Failure mode prevented**: SKILL.md becomes a wall of detail; the reader cannot tell what the Skill actually does in 30 seconds.

---

## Principle 2 — Split details by scope: cross-domain vs domain-specific

When a section moves out of `SKILL.md`, route it by scope:

- **Cross-domain conventions** (command construction discipline, output format selection, generic error/recovery, frequently-confused command pairs that span multiple domains) → a single shared reference such as `common-workflows.md` or `common-conventions.md`.
- **Domain-specific specifics** (e.g. multi-channel routing within one domain, status-field interpretation for one product, domain-only flags) → that domain's own reference.

Avoid letting domain specifics leak into the cross-domain reference; avoid letting cross-domain conventions get duplicated into every domain reference.

**Failure mode prevented**: details migrate to the wrong reference and become hard to find or get duplicated.

---

## Principle 3 — Delete-and-absorb, never delete-and-drop

When removing a section from `SKILL.md`, copy the substantive content into the target reference **in the same edit**. The slimming pass is two operations executed atomically:

1. Append/merge the removed content into the target reference (preserving tables and code blocks).
2. Replace the section in `SKILL.md` with a one-sentence pointer + anchor link to where it now lives.

Never delete a section first and "deal with it later". Detail loss is the most common regression in slimming passes.

**Failure mode prevented**: the slimmed `SKILL.md` looks clean, but the agent silently loses an error-recovery rule that used to be there.

---

## Principle 4 — Link, don't repeat: one source of truth per piece of guidance

Each piece of guidance has exactly one source of truth in `references/`. Other locations (including `SKILL.md` and sibling references) link to it with an anchor. No "two places that explain the same thing".

Concrete rules:

- A topic explained in `repo-commands.md` is **not** also explained in `SKILL.md`. SKILL.md routes to it.
- A convention listed in `common-workflows.md` is **not** also restated in three domain references. Each domain reference links to the common section.
- Routing tables in `SKILL.md` (e.g. intent → domain) reference target files; they do not re-list the operational steps that those references already describe.

**Failure mode prevented**: divergence over time — the duplicated copies drift apart and the agent reads the wrong one.

---

## Principle 5 — Defer environment work to the user

When the underlying CLI is unavailable or misconfigured (`command not found`, wrong shell, missing auth, expired token), the Skill body should:

1. Surface the error message **verbatim** to the user.
2. Provide the fix command (e.g. `a1 auth login --buc`, install link, `a1 link`).
3. Stop the workflow until the user resolves it.

Do **not** try to:

- Auto-install the underlying CLI.
- Auto-switch shells (`wsl bash -c '...'`, `bash -c '...'`).
- Detect OS and branch on `uname -s` from inside the Skill body.
- Recover platform-level state by writing files into the user's environment.

Environment-detection scripts and install commands are not Skill contract content. They either belong in a reference (loaded on demand) or are removed outright. The Skill's responsibility is **command routing and decision-making**, not terminal-environment governance.

**Failure mode prevented**: the Skill silently rewrites user environment, papers over real configuration problems, and accumulates platform-specific recovery code that grows unbounded.

---

## Principle 6 — Match metadata to the slim body

When slimming removes a capability description from the body (e.g. an intra-domain channel table, a removed reference file, a deprecated workflow), update **all metadata** in the same edit so triggers and the slim body stay aligned:

- `frontmatter.description` — drop sentences that referenced the removed capability; do not leave promotional text without a corresponding section.
- `frontmatter.version` — bump for any user-visible scope change (per the project's semver convention).
- `package.json.description` (if the Skill has one) — must match `frontmatter.description`.
- Discoverability invariants — directory name and frontmatter `name` still agree after the slim (no registry table exists to re-check).

**Failure mode prevented**: the Skill is triggered by a phrase the description still advertises, but the body no longer contains the matching workflow.

---

## Principle 7 — Verify no broken links and no leftover details

After slimming, run a final pass:

1. **Grep for broken references**: search the whole Skill directory for the slug, anchor, and filename of every removed section. Clean up any dangling links.
2. **Grep for leaked detail**: confirm `SKILL.md` no longer contains terms that name implementation specifics (concrete command flags, error code mappings, platform names like `WSL` / `macOS` / `Linux`, install URLs) outside the strict-requirements / conventions sections.
3. **Confirm references stay self-contained**: each reference still reads correctly without depending on text that used to live in `SKILL.md`.
4. **Re-list the file inventory**: ensure the resource index in `SKILL.md` matches the actual `./references/` and `./scripts/` directories — no entries pointing to deleted files, no files that the index forgot.

**Failure mode prevented**: dangling links, half-moved content, and a resource index that lies about what the Skill ships.

---

## Quick decision flow

When you find content in `SKILL.md` that looks too detailed:

```
Is it frontmatter / index / step skeleton / strict rule / convention?
  └─ Yes → keep in SKILL.md.
  └─ No → it is a detail. Identify its scope:
       ├─ Cross-domain → move to common-workflows.md (or equivalent shared reference).
       ├─ Domain-specific → move to that domain's reference.
       └─ Environment / platform / install → consider removing entirely (Principle 5).

After moving:
  ├─ Replace the section in SKILL.md with a one-sentence pointer + anchor link.
  ├─ Update frontmatter.description / version / package.json if the body's scope changed.
  └─ Grep the directory for references to the removed slug/file/anchor; fix dangling links.
```

---

## Anti-pattern catalogue

The following shapes indicate `SKILL.md` is no longer a contract and should be slimmed:

- A section longer than 10 lines that consists of bulleted "how-to" steps for a single sub-task.
- Any table whose columns are `symptom | cause | fix` (belongs in a reference).
- Any code block longer than 5 lines that is not a workflow diagram (belongs in a reference or script).
- Two sections whose content overlaps by more than 30% (collapse into one source of truth).
- Sentences containing concrete CLI flag names beyond the strict-requirements / conventions sections.
- An `### Installation` or `### Setup` section describing how to install the underlying CLI.
- Mentions of specific operating systems, shells, or terminal emulators in the workflow steps.

---

## Why this matters

A slim `SKILL.md` makes the agent's behavior **predictable and auditable**:

- The reader (human or agent) can read the contract once and route confidently.
- Detail changes happen in references without churning the contract.
- Triggers (frontmatter description) stay aligned with what the body actually delivers.
- The Skill stops accumulating environment-recovery code that no other Skill needs.

Slimming also has a **measured compliance payoff**. Skill loading is progressive across four levels: **L0** frontmatter `description` (always in context), **L1** `SKILL.md` body (loaded on trigger; keep ≤ ~5K tokens), **L2** `references/` (read on demand), **L3** `scripts/` (executed, near-zero token cost). Hard constraints buried mid-way through a bloated L1 body sit in the attention low-zone and get violated at a measurably higher rate (~72–80% vs ~100% when kept compact and well-placed — see [constraint-placement.md](./constraint-placement.md)). Every manual paragraph left in L1 dilutes the rules that must survive there; moving it to L2/L3 is compliance protection, not just tidiness.

Slimming is not a one-time refactor; it is a steady-state discipline applied every time the Skill changes.

## No History Narration

A Skill document states current facts for the next executor. Corrections replace the
wrong claim outright; they do not report the replacement.

- WRONG (history narration — delete): `> 旧文档断言「个人身份消息无法撤回」已证伪——实测该表明示不要重试。`
- RIGHT (current fact only): `个人身份消息撤回按平台返回码分诊：不支持时直接告知用户，不要重试。`
- WRONG: `（重要勘误：本条不再是限制）`
- RIGHT: delete the line; if a misuse guard is genuinely needed, state it forward: `X 命令已下线，改用 Y。`

Keep two forward-looking markers — they describe current state, not change history:

- confidence markers: `未实测（待验证）`, `文档口径，待二进制实测校准`
- misuse guards: `该 flag 位置与实测不符，以实测为准（示例见下）`
