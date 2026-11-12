---
id: "20261112T091921Z-speckit-sanitize"
unit_id: "/speckit.sanitize"
unit_type: "command"
run_id: "sanitize-20261112T091848Z"
scope: "local"
probe: "speckit-sanitize-wrapup"
kind: "internal"
slice: "commands"
partial: false
created: "2026-11-12T09:19:21Z"
summary: "Materials lane run: collect surfaced 2 pending index-inconsistency findings (legacy feedback/session index.json, req 055 residue); zero semantic candidates; single-batch cleanup plan presented and use"
---

## Review
Materials lane run: collect surfaced 2 pending index-inconsistency findings (legacy feedback/session index.json, req 055 residue); zero semantic candidates; single-batch cleanup plan presented and user-released; both repairs executed via the stores own reindex engines (feedback 4 entries, session 1 entry; legacy indexes retired only after state materialization, both git-tracked); sanitize apply resolved both findings; re-collect shows pendingTargets empty. Residual probe verbatim: goal count=0, team count=0.

## Optimization Points
- 1. Finding summaries (which carry the prescribed fix command) exist only in findings.json; the collect digest lists counts and targets only. Include a one-line summary per pending finding in the collect digest so the Present stage needs no direct ledger read — this run read the machine-managed ledger in full to obtain summaries (token-efficiency).
- 2. The repair disposition hides a true deletion (legacy index unlink inside reindex) behind a reversible label; state the repair side-effect class (state-materialize + delete, git-recoverable) in the finding summary so the confirmation-gate classification needs no source inspection.
