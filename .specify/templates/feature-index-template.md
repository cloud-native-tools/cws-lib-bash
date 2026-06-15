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
      awk -F'|' '/^\| [0-9]{3} \|/ {n++} END{print n}' .specify/memory/features.md
-->

**Total Features**: [FEATURE_COUNT] _(auto-derived; recompute on every edit — see comment above)_

| ID | Name | Description | Status | Feature Details | Last Updated |
|---|---|---|---|---|---|
