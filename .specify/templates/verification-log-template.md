# Verification Log — [REQUIREMENTS_KEY]

<!--
  ACTION REQUIRED for /speckit.implement:
  Populate this file during the run. The shape is intentionally structured (key=value
  + per-SC rows) so that /speckit.review, /speckit.analyze, and CI can derive
  pass-rates programmatically without grepping prose.

  SEEDING INSTRUCTION:
  At the start of the /speckit.implement run, copy this template into the spec
  directory and perform these replacements:
  1. Replace [REQUIREMENTS_KEY] with the actual key (e.g. "008-supervisord-stdout-logs").
  2. Parse requirements.md for all Success Criteria (SC-001, SC-002, ..., SC-NNN).
  3. Emit one complete three-field block (SC-NNN_status= / SC-NNN_value= / SC-NNN_note=)
     for EVERY SC found. Do NOT leave the generic "SC-001 / SC-002" placeholders.
  4. For every SC whose status is blocked / deferred / partial, emit the five
     SC-NNN_-prefixed measurement-ladder fields listed below. A missing field makes
     the row illegal, not merely thin.
  5. Record the feature's smoke test exactly once, in its own section below.
  This prevents ad-hoc formats and ensures every SC is tracked from the start.

  Conventions:
  - One key=value per line. Values are free text unless schema below says otherwise.
  - Lines starting with `#` are comments.
  - THE KEY=VALUE BLOCK IS THE RECORD; A TABLE IS A VIEW OF IT. The closure judgement
    (`scripts/python/closure-acceptance-check.py`) parses `SC-NNN_status=` lines and nothing else, so a
    `pass` written only into a Markdown table row is read as NO ROW AT ALL (`unknown`, never `pass`). A
    run that also renders a human table MUST emit this block as well, and the two MUST agree — where they
    disagree, the block is what downstream reads and the table is stale.
  - `smoke_command` carries ONE simple command and no leading environment assignment: the parser reads
    `key=value`, so `VAR=x pytest …` would be parsed as the key `VAR`. Put the interpreter/probe switch in
    the recorded command's argument position, or record the wrapper's own script path instead.
  - A key=value line ANYWHERE in this file is a record line — including inside a section written for humans.
    Do not paste a second copy of the smoke record or of an SC row into a prose section: a second
    `smoke_command=` is a defect (see below), and it is the defect a copy silently creates.
  - SC rows MUST follow `SC-NNN_<field>=<value>` with fields {status, value, note}.
  - `status` is one of: pass | fail | partial | blocked | deferred | unknown. THIS FILE OWNS THAT VOCABULARY:
    the set is CLOSED — no DoD row, gate or task row may narrow it to a subset, because a narrower set silently
    forbids an honest value and forces a reclassification judgement. A DoD row reading "record `pass` or
    `deferred`" silently forbids `partial`, so an honest `partial` (mechanical half measured, stated measurement
    condition not met) then fails the DoD.
  - When a metric is numeric, also record the raw measurement via `SC-NNN_value=`.
  - When status=deferred, ALSO write `SC-NNN_deferred_reason=`.

  OWNER: the schemas projected here are owned by `shared/workflow/acceptance-hardening.md`
  § Verification Vocabulary. This file is a declared carrier — it holds the rules where the run
  writes its statuses, it may not widen a value domain, and where it and the owner disagree the
  owner wins and this file is stale.

  THE SIX VALUES, AND `blocked` VERSUS `deferred`:
  - `blocked` means the environment cannot measure this assertion, so the feature is NOT ACCEPTABLE. It is a
    refusal, and it is why the feature status `Blocked` exists: honest bookkeeping is not acceptance.
  - `deferred` means the assertion was not attempted this round and the feature MAY STILL be acceptable — which
    is legal only on a `supporting`-path criterion. On a `final` path, "not attempted" is `blocked` or `fail`.
  - `pass` / `fail` / `partial` / `unknown` keep their plain meanings: the assertion held, it did not hold, part
    of it was measured, and nothing was measured and nothing is claimed.

  THE FIVE MEASUREMENT-LADDER FIELDS — required on every blocked / deferred / partial row:
  every field name carries the criterion id as its prefix, spelled exactly:

    SC-NNN_blocked_at                 ISO date, or the name of the reason it is blocked
    SC-NNN_reduced_measurement        what CAN be measured instead
    SC-NNN_reduced_measurement_run    yes / no
    SC-NNN_why_reduced_insufficient   why the reduced measurement does not stand in for the assertion
    SC-NNN_unblock                    what would lift it

  ILLEGAL ROW (mechanical trigger, no semantic judgement): `SC-NNN_reduced_measurement` is NON-EMPTY while
  `SC-NNN_reduced_measurement_run=no`. A missing ladder field is illegal in the same way. The trigger reads
  non-empty, never "available": a measurement written down and not run is not an honest substitute for running
  it, it is the same defect the ladder was introduced to stop.

  THE SMOKE RECORD — exactly one per feature, three fields:
    smoke_command        one shell command, verbatim, with no leading `VAR=value` assignment (the parser
                         reads `key=value`, so a leading assignment becomes the key); end-to-end over the
                         feature's main flow, not the whole suite
    smoke_exit_code      0 for a feature claiming `Implemented`
    smoke_evidence_path  repo-relative path to a file that MUST exist and be non-empty
    smoke_comparison     optional: a repo-relative comparison transcript (e.g. the second run's evidence)
                         when the smoke is a determinism comparison; the three fields above MUST carry
                         no annotation — a value the checker parses is a literal
  A second `smoke_command=` line is a defect, not a choice. A feature that cannot run its smoke is `Blocked`:
  "needs a real cluster" or "needs real network" is not an exemption — either the command is made deterministic
  on a local fixture, or the feature is blocked.

  THE STATUS IS A GATE PRODUCT, NEVER A SELF-ASSESSMENT. This file records a verdict; it does not produce
  one. Before ANY `SC-NNN_status=pass` is written here, the run MUST have executed the closure judgement
  (`scripts/python/closure-acceptance-check.py --spec-dir <spec-dir>`) over the tree it is about to record,
  and the recorded statuses MUST be the ones that verdict justifies; a status the checker would refuse MUST
  NOT be written as `pass` here as a way of making the check pass. The judgement, its reason set and its
  counts are owned by `shared/workflow/acceptance-hardening.md` § Closure Verdict — this file cites it and
  never restates it. A gate item, gate row or gate verdict belongs to the gate's own record (the stage's gate
  section), never here.
-->

# -- Baseline (recorded once, BEFORE any /speckit.implement work changes the tree) --

baseline_commit=[GIT_SHA_AT_RUN_START]
baseline_date=[YYYY-MM-DD]
baseline_branch=[BRANCH_NAME]

# Free-form baseline counters used to evaluate SCs. One per line.
# Example:
# baseline_useradd_service_count=0
# baseline_user_directive_count=18
baseline_[METRIC_KEY_1]=[VALUE]
baseline_[METRIC_KEY_2]=[VALUE]

# -- /speckit.implement results --

implementation_date=[YYYY-MM-DD]
post_change_commit=[GIT_SHA_AT_RUN_END]

# Free-form post-change counters mirroring the baseline keys above.
# Example:
# post_change_useradd_service_count=22
post_change_[METRIC_KEY_1]=[VALUE]
post_change_[METRIC_KEY_2]=[VALUE]

# -- Smoke test record (exactly one per feature) --
# One command, verbatim, run end to end over the feature's main flow. `smoke_exit_code` MUST be 0 for a
# feature claiming `Implemented`; `smoke_evidence_path` is the evidence path — a repo-relative path to a file
# that MUST exist and be non-empty. A feature that cannot run its smoke record is `Blocked`, never
# `Implemented`.

smoke_command=[ONE_SHELL_COMMAND_VERBATIM]
smoke_exit_code=[0]
smoke_evidence_path=[REPO_RELATIVE_EVIDENCE_FILE]
smoke_comparison=[OPTIONAL_REPO_RELATIVE_COMPARISON]

# -- Evidence records (bind every `pass` claim to archived evidence) --
# One record per evaluation sample, block shape mirroring the SC blocks below.
# Rules: a `pass` verdict REQUIRES a complete evidence row — all four keys, no
# blanks. `evidence_sha256` is SHA-256 over the archived file's bytes
# (deterministic; `sha256sum`-compatible). `evidence_path` is repo-relative
# (resolvable from any checkout). A `pass` without a complete evidence row is
# `unverified` and MUST NOT be cited as passing evidence anywhere downstream.
# The registered gate `gate-implement-evidence-binding` checks every recorded
# `pass`: the archived artifact exists, is non-empty, and its computed SHA-256
# equals the recorded hash — missing/empty/mismatch is RED naming the sample id
# and the reason, never downgraded to "self-disclosed and continue". Verdicts
# other than `pass` carry no binding duty.

sample_id=[SC-NNN_OR_SAMPLE_KEY]
evidence_path=[REPO_RELATIVE_ARCHIVED_ARTIFACT]
evidence_sha256=[SHA256_HEX_OF_THE_ARCHIVED_FILES_BYTES]
verdict=[pass|fail|partial|blocked|deferred|unknown]

# -- Success Criteria evaluation --
# One block per SC from requirements.md. Status values: pass | fail | partial | blocked | deferred | unknown
# (the closed set declared at the top of this file — never a subset of it).
# Every blocked / deferred / partial row ALSO carries the five ladder fields.
# THIS IS THE RECORD. A human-readable table elsewhere in the file is a view rendered FROM these rows;
# a status that exists only in the table is `unknown` to every downstream program.

SC-001_status=[pass|fail|partial|blocked|deferred|unknown]
SC-001_value=[NUMERIC_OR_EVIDENCE_STRING]
SC-001_note=[ONE-LINE_HUMAN_NOTE]

# A blocked / deferred / partial row keeps the same shape plus the ladder, e.g.:
# SC-002_status=[blocked]
# SC-002_value=[WHAT_WAS_MEASURED]
# SC-002_note=[ONE-LINE_HUMAN_NOTE]
# SC-002_blocked_at=[YYYY-MM-DD_OR_NAMED_REASON]
# SC-002_reduced_measurement=[WHAT_CAN_BE_MEASURED_INSTEAD]
# SC-002_reduced_measurement_run=[yes|no]
# SC-002_why_reduced_insufficient=[WHY_IT_DOES_NOT_STAND_IN_FOR_THE_ASSERTION]
# SC-002_unblock=[WHAT_WOULD_LIFT_IT]
# SC-002_deferred_reason=[REQUIRED_WHEN_status=deferred]

# (Repeat for every SC declared in requirements.md.)

# -- Joint acceptance (one row per `in-scope` runtime-stack row in requirements.md) --
# A `runtime-dependency-not-owned: RS-NNN` finding is refused only when the runtime-stack row is named
# here with a verdict; the row's `Form` and obligations are owned by
# `shared/workflow/acceptance-hardening.md` § Closure Verdict.

RS-001_joint_acceptance=[pass|fail|partial|blocked|deferred|unknown]

# -- Deferred tasks (mirrors `[~]` rows in tasks.md) --
# Comma-separated list of task IDs that were intentionally deferred to the user.
# An empty value means nothing was deferred.

deferred_tasks=[T020,T021,...]
deferred_reason_summary=[one-line summary of WHY these are deferred — e.g. "Layer-2 docker smoke build requires real docker daemon, deferred to user"]

# -- Free-form notes --
# Anything that doesn't fit the structured fields above. Optional.

notes=[...]
