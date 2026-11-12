# Checkpoint Protocol

**When**: after every stage U4 passes and before the next stage is dispatched. A checkpoint is a coordination point, not a stage and not a new gate; the U4 verdict and the stage sentinel remain the completion authority.

**Where**: `.specify/specs/<NNN-slug>/checkpoints/<NN>-<stage>.md`; a final `closure.md` records the terminal goal degree table and the archived team state.

## The five parts (all mandatory)

Parts 1–5 below are the standing agenda. Part 5's territory question acquires one mandatory
branch whenever the stage corrected history — **5b. Published-state check** — and the
terminal `closure.md` repeats the same check (see `## The published-state check (5b)`).

### 1. Artifact verification

- Consume the stage U4 verdict and a `loop-state.py --action snapshot` record.
- Record the artifact paths, the sentinel, the U4 evidence pointer, and any `ANOMALY:` line.
- Never infer completion from an executor's self-report.

### 2. Goal progress

- For each criterion of the goal the run is bound to (resolved from `goal_slug`, never from a path position), record `criterion / degree / evidence_ptr`.
- `degree` is a progress reading, not a binary checkbox; a missing measurement is `not_evaluated`, never zero.
- Goal content changes only through the goal engine (`/speckit.goal modify`); the checkpoint never writes `goal.md`.

### 3. Team configuration review

- Gather evidence from `wp-report.py`, the team's `runs/<run_id>-report.md`, and the ledger.
- Detect one named symptom and propose **at most one** exact delta from the closed candidate space:
  `concurrency`, `stage max_parallel`, `roster add/remove`, `pattern`, `verifier reserve`.
- The proposal names its evidence, the exact before/after values, and the expected effect.
- Ratify according to `checkpoint_policy.ratification` (`standing` for reversible config changes declared at U0, or `human`). Never apply silently.
- Apply through `improve-team` / `/speckit.team modify`; territory changes remain explicit modifications and are never optimizer output.

### 4. Concurrency and roster decision for the next stage

- Resolve the next stage's requested/effective concurrency and `stage_seats.<stage>.max_parallel`.
- Record the verifier reserve and the reason for any downgrade.
- The decision is written before the next dispatch; a later change requires another checkpoint.

### 5. Direction audit

- Reload the loop anchor before answering: **T0** the state spine's `driver_contract` + `direction_contract` +
  `next_action` at every checkpoint; **T1** the driver `SKILL.md` Hard Requirements block plus this protocol at
  every stage boundary, after any subagent turn-limit stall, and after a detected context compaction; **T2** the
  full manual plus a reference only when a dispatch form is unclear or a stall is being handled. A full reload of
  every reference at every step is forbidden: it is ceremony and it buries the anchor in noise.
- **The audit's primary object is the RULES, not the goal.** The current action and the next one already carry
  the goal; a dropped rule leaves no trace in them (the canonical failure: "unattended" was ignored — package
  boundaries asked for permission and the spine lagged — while the work itself kept advancing step by step).
  So the rule verdict and the action it licenses are stated **before** any goal statement: the first question
  asks the rules, the last two ask the process and the territory, and the goal is asked by no question of its
  own.
- Answer five binary questions, each with a path or a reading as evidence:
  1. Which rules govern this step, and is each still in force (`unattended` / no approval request / U4 -> next
     stage / spine written before acting / `workspace-guard --check` / fast-fail / the gate discipline / budget /
     report discipline)?
  2. Was the last action completed under those rules — no report substituting for execution, no subagent
     turn-limit treated as a reason to hand back?
  3. Is the next action the one the plan or assignment names? (The goal is implicit in it; do not ask the goal
     as a separate question.)
  4. Is the state spine fresher than the last checkpoint/commit (HR4)?
  5. Did the last package stay inside its territory and leave `workspace-guard --check` clean?
- The verdict is exactly one of `on-track`, `correction-applied`, `decision-needed`. Only `decision-needed` is
  surfaced (fast-fail); the other two are recorded and the loop continues.
- The audit is a statement, never an approval request: it MUST NOT end with a question to the user.
- Two consecutive audits flagging the same drift escalate as a recurring anomaly (fast-fail growth rule).

## The published-state check (5b)

**This section owns one obligation of the checkpoint and of `closure.md`: after a history correction, the
decision for the corrected trunk is executed on every declared remote, and published state is read back and
verified — never assumed.** Every other branch fact is reached by pointer and never restated here: the
declaration rows (`Trunk`, `Feature branch convention`, `Closeout`, `Closeout remotes`, `Remote roles`) live in
`.specify/workflow/git.md`; the command surface that derives and executes the push lives in
`.specify/skills/git-utils/references/closeout-commands.md`; the executor's stop-on-first-failure and no-force
rules live in the feature-091 close-out executor contract.

**Firing condition (decidable, closed).** Any checkpoint whose part 5 records `correction-applied` for a branch
correction is in scope — `checkpoint_policy.ratification=standing` on the part 5 record is the form it takes, and
the driver applies the check without asking. The trigger is the recorded status, not the driver's memory of what it
moved, so a correction noticed late still fires the check. A checkpoint that recorded no correction carries part 5b
as `n/a — no history correction`, which is a recorded answer, never an omission.

**The check is five steps, in this order.**

1. **Enumerate the declared remotes.** Read them from the `Closeout remotes` row through the derivation the
   close-out command surface owns. This step adds no second rule and no remote literal of its own: `origin`, the
   write-forbidden upstream, stays excluded by the role marking the block already carries.
2. **Name the trunk and its expected SHA.** The trunk comes from the `Trunk` row, its corrected commit from the
   local ref as recorded in part 5 — not from `HEAD`, which on a feature branch is a different commit.
3. **Read every published head, before deciding anything.** One reading per declared remote, and the reading is the
   executable form of this rule:

   ```bash
   for remote in $DECLARED_REMOTES; do
     printf '%s %s: ' "$remote" "$TRUNK"; git ls-remote "$remote" "refs/heads/$TRUNK"
   done
   ```

   `$DECLARED_REMOTES` and `$TRUNK` are shell variables substituted from steps 1 and 2; this section spells out no
   remote name and no branch name of its own.

   The expected end state is one SHA — the corrected local trunk — for every declared remote. The read happens
   before the disposition, so the number of steps 4 and 5 at most read is exactly the number of divergences step 3
   found.
4. **Disposition — every declared remote is either converged or named.** Each remote's verdict is one of the two
   closed outcomes:

   - **converged** — the read SHA equals step 2's; nothing to do, and the checkpoint records the equality.
   - **named residue** — a row `residual: published-<remote>-diverged` carrying its own `unblock`: the exact
     command that converges it, the authorization the declared `Closeout` value supplies, and the owner who
     executes it. The residue is a recorded fact, never a silent skip, and it is carried into the next checkpoint
     and into `closure.md` until it reads converged.

5. **Converge through the one owner that may push.** When the declared `Closeout` value authorizes a push, the push
   runs through the close-out command surface — one target per derived sequence, in the substituted
   `git push <remote> <src>:<dst>` form, with the read-only role re-checked immediately before each target. The
   checkpoint writes the corrected trunk; it never improvises a push of its own, never retries, and never forces: a
   **diverged** remote (a non-fast-forward reading) is a stop for that remote, not a reason to reach for
   `--force`, and a **rejected** push (protection / hook / lease) is a stop with its class reported. Steps 1–3 then
   re-run, and their second reading is the evidence that the residue closed.

**What the correction owes, stated plainly.** A history correction that stops at the local clone has not finished:
the spine, the checkpoints and the corrected branch agree while the published mirrors still hold the moved-from
content, and the next close-out reads those mirrors as the declared state. The failure is silent because every
local reading is green — so the obligation of this section is an *executed* step, not a note that the mirrors were
left behind. A named residue discharges the checkpoint only when its `unblock` is named too; "left behind" without
a residue row is the defect this section exists to forbid.

**Failure handling, by reading.**

| Reading at step 3 (or at its re-run) | Disposition |
|---|---|
| every declared remote equals the corrected trunk | converged; record the SHAs and the read command |
| a remote older than the corrected trunk, push authorized | push that remote through the close-out surface, then re-read; converged or a stop with its class |
| a remote that will not fast-forward (diverged) | stop for that remote, no `--force`, `residual: published-<remote>-diverged` with its `unblock` |
| a push rejected (protection / hook / lease) | stop for that remote, its class verbatim, residue row with the `unblock` naming the owner |
| a remote unreachable | not converged and not divergent: record `unreachable` with the probe's evidence, residue row, and a re-check at the next checkpoint |
| no declared remotes (explicitly empty or absent row) | `n/a — no pushable remote`; the check records the row it read, and no residue is invented |
| `correction-applied` recorded but no correction can be named in part 5 | the check cannot be scoped: `decision-needed`, surfaced (fast-fail) |

**Terminal check.** `closure.md` runs steps 1–3 and records one row per declared remote — its name, its published
`<trunk>` SHA, the expected SHA and the verdict — and MUST NOT record `converged` for any remote on a reading taken
before the last correction of the run. A residue that is still open at closure is named in closure, and it is the
one thing an "everything closed" closure sentence is not allowed to hide.

## Rules

- All five parts are present. An inapplicable part carries `n/a` and a reason; omission is a defect.
- At most one configuration/concurrency/roster change per checkpoint. An explicit human goal edit does not count toward this cap.
- A checkpoint file is committed by the driver immediately after U4 as a driver record, not as a stage deliverable.
- **Rollback**: at the next checkpoint, revert the prior change when U4 fails, new test failures appear versus the stage baseline, `retries_package` increases by at least two, or `parallelism_efficiency` drops by at least 30 percent. A rolled-back change is not re-proposed immediately.
- `coordinate` remains territory-overlap only; with a single team bound to the goal it is a recorded no-op.
- The checkpoint carries paths and verdicts, never raw transcripts or fabricated metrics.
- **Direction audit is mandatory**: every checkpoint carries part 5; a checkpoint without it is a defect. Its reload tier and verdict are recorded in the checkpoint, not only in the conversation.
- **Published state is verified, never assumed**: a checkpoint whose part 5 records `correction-applied` for a branch correction MUST carry part 5b, and `closure.md` MUST carry the terminal check. A correction recorded without a published-state reading — converged SHAs or a residue row with its `unblock` — fails the checkpoint, and a residue left open at closure is named there.
- **No approval request**: a checkpoint's outcome is a statement; asking the user to continue violates HR1 and is itself a drift signal.
- **Workspace signature (2026-11-08 RCA)**: a stage that runs probes, tests or subagents MUST record the measured repository's signature before them and compare it after: `python3 .specify/scripts/python/workspace-guard.py --snapshot <spec-dir>/test-evidence/workspace-<stage>.json --repo <repo>` then `--check`. A difference in branch, refs or `.specify/specs` fails the checkpoint — it means a probe or agent resolved its repository root outside its sandbox (the 2026-11-07 incident created 40 branches and spec dirs).

## Minimal shape

```markdown
# Checkpoint NN — <stage>

## 1. Artifact verification
- sentinel: <STAGE-DONE>
- U4: <pass|fail> — <evidence path>
- artifacts: <paths>
- anomaly: <未发现异常 | ANOMALY: ...>

## 2. Goal progress
| criterion | degree | evidence_ptr |
|---|---|---|
| <criterion> | <0-100% or not_evaluated> | <path> |

## 3. Team configuration review
- evidence: <wp-report path | team run report path | ledger>
- symptom: <one named symptom>
- proposal: <none | one exact delta>
- ratification: <standing | human | not-ratified>
- applied: <yes/no + path>

## 4. Next stage concurrency / roster
- requested: <n>; effective: <n>; reason: <reason>
- stage max_parallel: <n>; verifier reserve: <n>
- roster: <seats>

## 5. Direction audit
- reload tier: <T0 | T0+T1 | T2>
- Q1 rules: <which rules, each in force?> — <evidence>
- Q2 process: <verdict> — <evidence>
- Q3 next action: <verdict> — <evidence>
- Q4 spine freshness: <verdict> — <evidence>
- Q5 territory/workspace: <verdict> — <evidence>
- verdict: <on-track | correction-applied | decision-needed>

## 5b. Published-state check
- scope: <n/a — no history correction | in scope: <what was corrected> >
- trunk / expected: <$TRUNK> = <corrected sha>
- published heads: <remote> <ref> = <sha>; … (one reading per declared remote)
- disposition: <converged | residual: published-<remote>-diverged — unblock: <command + owner> | unreachable — unblock: <owner>>
- re-read after convergence: <sha reading | not applicable>
```

## Review dispositions carried by this file (dated record)

One dated record of which review findings this file answers, and how. It restates no rule: the rule lives in the
sections above, and a later revision of those sections leaves this record as the history of what was asked.

| Finding | Where it is answered | What the answer is |
|---|---|---|
| P0 — the published mirrors were left behind by a branch correction | `## The published-state check (5b)`; the `## Rules` entry on verified published state | the correction is not closed until every declared remote is read and either converged or named as a residue with its `unblock`; `closure.md` carries the terminal check |
| P1 process — the review stage's base commit was six commits behind the entry | not in this file: the rule belongs to `references/state-awareness.md`, which owns when the spine's stage base is written and when a dispatch is refused | recorded here only so the split is visible; this file adds no second statement of it |
| P2 process — the code segment's view of the delta had no generated/authored split | not in this file: the rule belongs to the code-review segment's own program | recorded here only so the split is visible |
| P2 process — `review.md`'s "What Worked" section carried no evidence obligation | not in this file: the rule belongs to the review template | recorded here only so the split is visible |

The three rows that say "not in this file" are pointers, not deferrals: they name the owner so a reader of this
protocol does not mistake this file for the place a fix is missing from.

