# Canonical `## Documentation` Step (Docs-Sync Evaluation)

**Feature 037 — Docs Command.** This file is the single source of truth for the
`## Documentation` docs-sync evaluation step that every **complex** command template
embeds at its wrap-up stage — the same lifecycle point as the `## Feedback` step.
Simple commands MUST NOT embed it. Embedding templates reference this file and keep
their own section to a short pointer; they MUST NOT copy these rules.

## Positioning & Red Lines

1. **Target = the current project's documentation space** (root entry files + `docs/`
   tree, as defined by `/speckit.docs`'s desired-state baseline). This step keeps docs
   consistent with the project's actual state through frequent, small, incremental
   updates — it is NOT a feedback channel and NOT a full reconcile.
2. **Non-blocking.** The evaluation and any resulting write happen after the command's
   substantive work; a "no record needed" outcome or a failed write never blocks or
   degrades command wrap-up.
3. **Incremental only.** Judge ONLY the information produced by this run (new
   capabilities, key decisions, structural changes). NEVER trigger a full R0–R6
   reconcile sweep from this step — that is `/speckit.docs`'s job.
4. **Zero new machinery.** No new storage, counters, or reminder systems. The outcome
   lives in the session output and in the updated documents themselves.

## Evaluation procedure (the embedded step points here)

1. **Gate.** Only evaluate if the run reached wrap-up and did substantial work; skip
   for trivial/no-op runs. If the project has no documentation space at all, suggest
   `/speckit.docs` (bootstrap) once and conclude.
2. **Assess.** List the information this run produced that a reader of the project
   docs would need: new user-facing capability, changed behavior, a decision worth an
   ADR, a structural/layout change, a new convention.
3. **Conclude with exactly one of**:
   - `需记录（目标文档 + 要点）` — name the target document(s) and the bullet points to land, or
   - `无需记录` — one line, done. Repeated "无需记录" across runs is a normal, healthy outcome; never invent doc changes to appear productive.
4. **Write (only when 需记录).** Route semantically per the `/speckit.docs` baseline
   (concepts / tutorials / tasks / reference / decisions / contribute / notes; uppercase
   special names keep their fixed semantics) and apply ONLY safe local writes: create or
   append/update in place, never overwrite same-name content (conflict → `__<ts>` suffix),
   formal zone is archive-not-delete. If the needed change is a move / archive /
   restructure, do NOT execute it here — record the recommendation and suggest running
   `/speckit.docs` instead.
5. **Report.** Surface the conclusion (and any files written) in the command's wrap-up
   summary.

## Notes for embedders

- Place the `## Documentation` section immediately after `## Feedback` and before
  `## Handoffs`.
- The section body is a pointer to this protocol plus the conclusion contract — keep it
  under ~10 lines; rules live here only.
- Commands only run inside a Spec Kit project; no standalone-mode gate is needed.
