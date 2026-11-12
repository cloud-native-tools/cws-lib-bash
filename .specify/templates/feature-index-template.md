# Feature Index

This index tracks all functional and non-functional features managed within the project. It serves as the central directory for specifications, plans, and implementation status.

<!--
  ACTION REQUIRED for any command that mutates this table (`/speckit.feature`,
  `/speckit.plan`, `/speckit.implement`):

  The `Total Features` value below MUST be auto-derived from the number of data
  rows in the table (count rows that begin with `| ` and a feature ID — exclude
  the header and separator rows). Do NOT maintain it by hand and do NOT bump it
  separately when adding a feature row; recompute on every write.

  Reference shell expression a human can paste to verify:
      awk -F'|' '/^\| [0-9]{3} \|/ {n++} END{print n}' .specify/features.md
-->

**Total Features**: [FEATURE_COUNT] _(auto-derived; recompute on every edit — see comment above)_

**Status vocabulary** (closed — these seven values are the entire domain a `Status` cell may carry): `Draft` | `Planned` | `Implemented` | `Blocked` | `Ready for Review` | `Sealed` | `Completed`.
The transition rows and row semantics are owned by `.specify/templates/feature-details-template.md` § Canonical Status State Machine and are not restated here; this index carries the value domain itself, so a writer filling the `Status` column never has to open another file to learn which values are legal.

| ID | Name | Description | Status | Feature Details | Last Updated |
|---|---|---|---|---|---|
