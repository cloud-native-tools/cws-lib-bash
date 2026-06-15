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
  This prevents ad-hoc formats and ensures every SC is tracked from the start.

  Conventions:
  - One key=value per line. Values are free text unless schema below says otherwise.
  - Lines starting with `#` are comments.
  - SC rows MUST follow `SC-NNN_<field>=<value>` with fields {status, value, note}.
  - `status` is one of: pass | fail | partial | deferred | unknown.
  - When a metric is numeric, also record the raw measurement via `SC-NNN_value=`.
  - When status=deferred, ALSO include SC-NNN_deferred_reason= explaining what would unblock.
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

# -- Success Criteria evaluation --
# One block per SC from requirements.md. Status values: pass | fail | partial | deferred | unknown.
# When status=deferred, ALSO include SC-NNN_deferred_reason= explaining why and what would unblock.

SC-001_status=[pass|fail|partial|deferred|unknown]
SC-001_value=[NUMERIC_OR_EVIDENCE_STRING]
SC-001_note=[ONE-LINE_HUMAN_NOTE]

SC-002_status=[...]
SC-002_value=[...]
SC-002_note=[...]

# (Repeat for every SC declared in requirements.md.)

# -- Deferred tasks (mirrors `[~]` rows in tasks.md) --
# Comma-separated list of task IDs that were intentionally deferred to the user.
# An empty value means nothing was deferred.

deferred_tasks=[T020,T021,...]
deferred_reason_summary=[one-line summary of WHY these are deferred — e.g. "Layer-2 docker smoke build requires real docker daemon, deferred to user"]

# -- Free-form notes --
# Anything that doesn't fit the structured fields above. Optional.

notes=[...]
