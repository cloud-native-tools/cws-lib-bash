# Canonical `## Feedback` Step

**Feature 028 — Framework Feedback Mechanism.** This file is the single source of
truth for the `## Feedback` step that every qualifying unit embeds. Skills embed it
as their final workflow section; the 13 **complex** command templates embed it at
their wrap-up / Git-commit-prompt stage. Simple commands MUST NOT embed it.

## Positioning & Red Lines

These four facts govern every part of the mechanism and outrank any embedded wording:

1. **Target = the Spec Kit framework itself.** Feedback describes friction in Spec Kit's
   templates, commands, skills, scripts, and docs — never an assessment of the LLM, the
   agent CLI/harness, or the user's project code.
2. **Feedback is user data and fully optional.** The user may ignore the threshold
   prompt, leave entries unprocessed forever, or delete the store. No flow may block,
   nag repeatedly, or degrade because feedback was not handled.
3. **Zero automated transmission.** Neither the engine nor any embedding unit may
   upload, push, or otherwise send feedback anywhere. The only legitimate transmission
   paths are (a) the user manually sending a packaged zip, and (b) the user committing
   feedback files to their own git repository. `mark-submitted` is local bookkeeping
   ("user confirmed disposition"), not an upload.
4. **Local workaround value.** Until a Spec Kit version update lands, past entries are a
   reference for working around recurring issues — see *Workaround lookup* below.

**Goal anchor (Constitution Principle XIII — Better-Harness Orientation).** Feedback is one
of the framework's Better-Harness instruments: it strengthens the **Learning Capture**
dimension of the goal model defined once in `.specify/shared/guidelines/better-harness.md`.
Vocabulary note: the "harness" in red line 1 means the agent CLI/runtime (the host); the
goal model's "Harness" means the project-level execution environment that Spec Kit's
artifacts help build. The anchor adds orientation only — it never overrides these red lines.

Do not diverge per surface — copy the canonical block below verbatim (adjusting only
the `<unit-id>` / `<unit-type>` placeholders for the embedding unit).

---

## Canonical block (copy verbatim into the embedding unit)

```markdown
## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up (the same lifecycle point where this unit would prompt for a Git commit),
run this self-reflection step. It is agent self-reflection — **never** solicit feedback
content from the user.

1. **Gate on qualification & completion.** Only proceed if this run reached wrap-up and
   did substantial work. Skip entirely for trivial/no-op runs. If the run was aborted or
   failed before wrap-up, follow the *Abort / partial-run rule* below.
2. **Reflect (no user input).** Review the just-completed run against this unit's declared
   purpose/description. Produce a short prose review plus **≥1 concrete, unit-specific
   optimization point**. If the run was clean, record exactly one line:
   `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to *this* unit's operation. Do NOT produce a
   global/whole-project assessment — that is `/speckit.review`'s job. Every entry is
   `scope: local`.
4. **Dedup guard.** Choose a stable `run_id` for this run (e.g. the feature key + a run
   timestamp). If a parent flow already recorded feedback for this same `(unit_id, run_id)`,
   the engine will no-op — do not force a duplicate.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "<skill:NAME | /speckit.COMMAND>" --unit-type "<skill|command>" \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** Read `should_prompt` from the `record` output
   (or run `--action status`). When it is `true`, surface a **single** consolidated
   notification inviting the user to submit collected feedback to the Spec Kit developers;
   on user confirmation run `--action mark-submitted`. Below threshold, do NOT prompt.
   The detailed prompt semantics (package → manual send → mark-submitted, plus the
   skip / silence options) live in the canonical protocol:
   `.specify/shared/workflow/feedback-step.md` § *Threshold prompt protocol*.

**Abort / partial-run rule.** If the run failed or was interrupted before wrap-up, either
skip recording OR record with `--partial` and a `## Review` that begins with
`**Partial run** — `. Never present a partial run as a complete review.

**Nesting rule.** When a command invokes a skill (or a skill invokes a skill), each
qualifying unit records feedback for **its own** scope only, keyed by its own
`(unit_id, run_id)`. The same unit+run MUST NOT be recorded twice.
```

---

## Threshold prompt protocol (canonical semantics for step 6)

When `should_prompt` is `true`, surface **one** prompt offering exactly three choices
(embedded copies that still say only "invite the user to submit" defer to this section):

1. **Package for manual delivery** — run:
   ```bash
   python3 .specify/scripts/python/feedback-utils.py --action package
   ```
   The engine zips all pending entries into `.specify/memory/feedback/packages/`
   (**source files untouched**, no network access), and prints the zip path, the
   detected upstream repo (user-configured `upstream_repo` > PEP 610 install metadata
   `direct_url.json` — the custom spec-kit's GitHub/GitLab origin), and manual send
   guidance (GitHub: issue attachment; GitLab: issue attachment or MR to the feedback
   intake directory). **The agent never sends the zip itself.** After the user confirms
   the batch is dealt with (sent — or deliberately discarded), run
   `--action mark-submitted` to reset the local counter.
2. **Skip this time** — do nothing; the prompt will naturally reappear only after more
   entries accumulate.
3. **Stop prompting** — raise the threshold (`--threshold <N>` or
   `SPECKIT_FEEDBACK_THRESHOLD`); feedback keeps recording but stops prompting.

If the upstream repo cannot be detected, show
`--action upstream --set <repo-url>` as a one-time setup step instead of guessing.

## Workaround lookup (local value of the store)

When a command or skill misbehaves and a Spec Kit update is not yet available, check
whether earlier runs already hit — and worked around — the same issue:

```bash
python3 .specify/scripts/python/feedback-utils.py --action list --unit-id "<skill:NAME | /speckit.COMMAND>"
```

Entries' `## Review` / `## Optimization Points` often name the concrete obstacle and the
workaround applied. This is a read-only aid — it never gates execution.

---

## Notes for embedders

- **Runtime-mode gate is mandatory for skills**: skills are also deployed standalone
  (outside any Spec Kit project — no `.specify/`, no engine). The gate paragraph at the
  top of the canonical block MUST be kept verbatim; detection semantics live in
  `.specify/shared/workflow/runtime-mode.md`. Commands (`/speckit.*`) only ever run
  inside a Spec Kit project, so the gate is a no-op for them.
- **Skills**: `--unit-id "skill:<name>"`, `--unit-type skill`. The section is the last
  workflow section of `SKILL.md`.
- **Complex commands**: `--unit-id "/speckit.<command>"`, `--unit-type command`. Place the
  section next to `## Optional: Git Commit`, never mid-flow.
- **Simple commands** (`agents`, `constitution`, `feature`, `team`): omit this step entirely.
- The engine store lives at `.specify/memory/feedback/`; threshold defaults to `10`
  (`--threshold` / `SPECKIT_FEEDBACK_THRESHOLD`).
