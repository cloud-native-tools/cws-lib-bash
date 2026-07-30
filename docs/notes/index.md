# Notes

Temporary, lifecycle-constrained notes. Every note MUST carry the frontmatter
below. State machine: draft →(merged into target)→ archived; draft →(past
expires)→ expired; expired →(renewed)→ draft; expired →(human-confirmed)→
deleted. Notes is the only zone where confirmed deletion is allowed.

## Frontmatter template

```yaml
---
title: "<one-line title>"
created: YYYY-MM-DD
expires: YYYY-MM-DD    # required; default = created + 60 days
status: draft          # draft | expired | archived
target: ""             # intended formal destination, required when archived
tags: []
---
```

## Automation

```bash
python3 .specify/scripts/python/docs-utils.py --action scan --root .
python3 .specify/scripts/python/docs-utils.py --action expire --root .
python3 .specify/scripts/python/docs-utils.py --action clean --root .        # dry-run
python3 .specify/scripts/python/docs-utils.py --action clean --yes --root .  # after human confirmation
```
