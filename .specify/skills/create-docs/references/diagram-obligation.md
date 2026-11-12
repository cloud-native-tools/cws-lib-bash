# The Diagram Obligation — schema reference (distributed with this skill)

**What this file is**: the **client-facing projection** of the obligation — the part a project that installed
`create-docs` needs in order to *read* the `docs-utils.py --action obligation` output and to *write* the records
that make a diagram traceable. It travels with the skill, so no path here points outside this skill's own tree or
the project's `docs/`.

**What this file is NOT**: a design record. The obligation's design — the closed verdict and reason sets, the
per-document decision order, the two record schemas and their clause codes (`C-001`…`C-016`) — is owned by the
framework repository's `contracts/diagram-obligation.contract.md`, which does **not** ship and is therefore cited
here by name, never by a link. Where this page and that contract disagree about a **value**, the contract wins and
this page is the defect; where this page and **the engine** disagree, the engine wins
(`.specify/scripts/docs-utils.py --action obligation --help` and its JSON payload are authoritative for anything this page
summarises).

The obligation's **requirement** (which documents must carry a diagram, and how a named exemption replaces one) is
stated in `SKILL.md` § Desired-State Baseline, item 5. This page restates only which value each document lands and
why; it adds no rule of its own.

The **five** verdicts below (`satisfied` / `missing` / `stale` / `recorded-exemption` / `not-evaluated`) are the
checker's vocabulary. They are a different set from the **six** statuses the framework's verification log uses for
a success criterion (`pass` / `partial` / `fail` / `blocked` / `deferred` / `unknown`), owned by the framework's
`.specify/shared/workflow/acceptance-hardening.md` § Verification Vocabulary: five document verdicts here, six criterion
statuses there, and the two are not interchangeable.

---

## 1. Where the two records live

| Record | Path under the project root | Unit |
|--------|------------------------------|------|
| Traceability record | `docs/.speckit/runs/<UTC basic>-<8 hex>-diagram-trace.json` | one file per producing run |
| Exemption record | `docs/.speckit/exemptions/<relative document path>.md` | one file per exempted document |

`docs/.speckit/` is the machine area: never triaged as prose content, never archived, never counted as a carrier
document. `<UTC basic>` is `YYYYMMDDTHHMMSSZ`; `<8 hex>` is the first eight hex characters of the producing run's id.
The two are joined by a single `-`, and the extension is always `.json`. One record per run means two concurrent
writers write **different paths**, never one shared aggregate.

The checker reads **only** the one file `--record` names. It never globs `runs/` and never guesses "the newest one":
guessing would make a silently edited record undetectable, which is the failure the obligation exists to catch.

## 2. Traceability record schema

```json
{
  "run_id": "<UTC timestamp>-<8 hex>",
  "feature": "<feature key or null>",
  "diagrams": [
    {
      "document": "docs/concepts/foo.md",
      "engine": "mermaid",
      "engine_reason": "<the routing decision that selected this engine layer>",
      "ldm_summary": "<diagram_class=…; elements=…; relations=…; zones=…>",
      "delivery": { "accepted": true, "unmet": [] },
      "source": "docs/assets/foo.mmd",
      "rendered": [
        { "path": "docs/assets/foo.svg", "sha256": "<64 hex>" },
        { "path": "docs/assets/foo.png", "sha256": "<64 hex>" }
      ]
    }
  ]
}
```

Required fields — any one missing makes the entry untraceable (`trace-incomplete`): `document`, `engine`,
`engine_reason`, `ldm_summary`, `delivery.accepted`, `source`, and `rendered[].path`. `rendered[].sha256` is
optional; when it is absent the digest rule below is simply not judged.

- **Every path is relative to the project root**, the same base the document's own relative link resolves against, so
  a reference and a record entry can be compared directly.
- **One entry per produced diagram**, not per document that happens to show it: two documents citing the same
  diagram share one entry, and an update rewrites that entry rather than forking a copy per document.
- What the three content fields *mean* is owned by the drawing capability (`draw-diagram`): `engine` is one of its
  engine-layer names, `ldm_summary` is its semantic-model summary, `delivery` is the outcome of its own delivery
  self-check. This page records only the field names and which are required.
- A **producing run** writes the record, in the same run that writes the faces. The checker never writes it.

## 3. Exemption record schema

```markdown
---
document: docs/concepts/changelog-shaped.md
reason: exempt-chronological
recorded_at: 2026-11-06
justification: "Release flow ordered in time; no structure to draw"
---
```

- `reason` is a closed three-value set, and every value says *this file has no structure to depict* — never "this
  diagram would be hard to draw": `exempt-chronological` (a timeline or release stream), `exempt-flat-reference` (a
  flat reference table), `exempt-licence` (licence or legal text).
- **Validity**: `document` equals the exempted document's root-relative path, `justification` is non-empty and at
  least 8 characters, and `recorded_at` reads `YYYY-MM-DD`. Anything else is `not-evaluated` / `exemption-invalid` —
  visible, never a silent pass.
- **An exemption is not a pass.** `summary.exempted > 0` forces `summary.clean` to `false`. It does **not** stop
  `summary.converged`: an exemption is a legal terminal state, and `converged` asks only whether any
  `missing` / `stale` / `not-evaluated` remains. Use `converged` for "is there work left", `clean` for "is this space
  wholly compliant".
- **An exemption that no longer holds is reported.** When the exempted document in the same run already carries a
  reference that resolves to a **rendered** face, the exemption has been overturned by fact → `not-evaluated` /
  `exemption-invalid`, counted once in `summary.exemption_superseded`. That is the only mechanical signal for "the
  justification no longer applies"; a change in the justification's meaning is never inferred.

## 4. The five verdicts and their reasons

Each carrier document lands exactly one verdict, with a reason from the closed table below. A value outside either
set is a contract violation of the checker, not a finding about a project.

| Verdict | Reason | One-line meaning |
|---------|--------|------------------|
| `satisfied` | `reference-resolves` | The document references a rendered face and the record accounts for it |
| `missing` | `no-diagram-reference` | No relative reference to a diagram face at all |
| `missing` | `reference-unresolved` | A reference exists but its target is not on disk |
| `missing` | `orphan-source` | A rendered face is on disk and the editable source is gone |
| `missing` | `orphan-rendered` | The editable source is on disk and the rendered face is gone |
| `stale` | `source-newer-than-render` | The source was edited after its rendered face was produced |
| `stale` | `render-digest-mismatch` | A face's bytes no longer match the record's `sha256` |
| `not-evaluated` | `no-trace-record` | Faces and reference are in place; no producing run left a record |
| `not-evaluated` | `trace-incomplete` | A record exists but cannot point at this diagram |
| `not-evaluated` | `exemption-invalid` | An exemption record is invalid or has been overturned |
| `not-evaluated` | `render-unreadable` | A face exists but cannot be read |
| `recorded-exemption` | `exempt-chronological` | A valid exemption record stands and no render is referenced |

`recorded-exemption` is not a pass, and `not-evaluated` is not "ignore for now": it makes both `converged` and
`clean` false exactly as `missing` does.

## 5. When a document is `satisfied`

All five conditions hold at once. Any one failing means the document lands one of the other tiers — never
`satisfied`:

1. The document carries at least one **relative** link (`[text](path)`, not `http(s)://`, not absolute) that resolves
   to a file on disk.
2. That file is a same-named `rendered[].path` in the record `--record` names. **A link to the editable source is not
   this condition**: it names the file the reader cannot view, and it is reported as the missing rendered face.
3. Both faces of that diagram — `source` and `rendered[]` — are on disk.
4. The record's entry for that diagram is complete (every required field above).
5. Neither staleness rule below holds.

**No record means `not-evaluated`.** "Both faces are on disk and the link resolves" is not acceptance: an unrecorded
diagram is one nothing can vouch for.

## 6. The two staleness rules

- **Source newer than render**: the source's modification time is strictly later than the earliest rendered face's.
  The pair is out of step; re-render, do not touch the source.
- **Render digest mismatch**: a face's bytes no longer hash to the `sha256` the record carries. The picture was
  edited by hand; re-render from the source rather than editing the render.

Both rules need **two faces on disk** to be judged at all. A document missing one face is a face-loss finding with a
name, not a staleness finding: `orphan-rendered` and `orphan-source` are mirror images and are never swapped.

## 7. Precedence — the first hit wins

The checker makes one pass in this order and stops at the first hit; it never backtracks and never overwrites a
verdict with a later tier's:

| # | Condition | Verdict / reason |
|---|-----------|------------------|
| 1 | A valid exemption record, no diagram face referenced | `recorded-exemption` / `exempt-chronological` |
| 2 | An exemption record that is invalid or overturned | `not-evaluated` / `exemption-invalid` |
| 3 | No relative reference to a diagram face | `missing` / `no-diagram-reference` |
| 4 | A reference whose target is not on disk | `missing` / `reference-unresolved` |
| 5 | One face of the pair on disk while the other is absent | `missing` / `orphan-rendered` · `orphan-source` |
| 6 | Faces and reference in place, but no record points at this diagram (a record exists and its entry is missing a required field) | `not-evaluated` / `trace-incomplete` |
| 7 | Faces and reference in place, and there is no `--record` at all (or nothing in it points here) | `not-evaluated` / `no-trace-record` |
| 8 | Faces, reference and complete record in place; a staleness rule holds | `stale` / `source-newer-than-render` · `render-digest-mismatch` |
| 9 | Everything above is clear and the reference names a rendered face | `satisfied` / `reference-resolves` |

The row count is the design record's (`contracts/diagram-obligation.contract.md` `C-016`, nine orders) projected
one for one: orders 6 and 7 are two different facts — a record that exists but cannot point at this diagram, and no
record to point with — so they are never merged into one row here.

Face loss precedes staleness, because a rule that compares two faces cannot be judged when one of them does not
exist; attributing the loss to staleness sends the reader to re-render something that is missing.

## 8. The payload

`--action obligation` writes one JSON object and always exits `0` when it judged something: red and green live in the
payload, never in the exit code. Exit `2` means an input could not be read (a `--root` that does not exist, a
`--record` that is not readable JSON) — never a finding about the documentation.

```json
{
  "action": "obligation",
  "root": "<resolved root>",
  "record": "<resolved record path or null>",
  "carriers": 85,
  "documents": [ { "path": "docs/concepts/foo.md", "line": 12, "verdict": "missing", "reason": "no-diagram-reference" } ],
  "summary": {
    "satisfied": 0, "missing": 84, "stale": 0, "exempted": 0, "not_evaluated": 1,
    "converged": false, "clean": false, "exemption_superseded": 0
  }
}
```

- `documents[]` is sorted by `path`, and every entry carries `path` and `line` (the reference's own line; `0` when
  there is no reference). Naming each document by path is a hard requirement: a count alone is not actionable.
- `converged` = at least one carrier was judged **and** `missing`, `stale` and `not-evaluated` are all zero.
  `clean` = `converged` **and** `exempted` is zero. Use `converged` to decide whether work remains and `clean` to
  decide whether the space is wholly compliant; do not substitute one for the other.

## 9. What the checker does not judge

- **Whether the diagram is semantically right.** Whether a picture's labels and relations agree with the prose is a
  review judgement, not a machine one. The obligation proves the artifact set and its traceability.
- **Whether an engine is available.** The checker calls no engine and needs no network; an engine's refusal belongs
  to the producing run, which must report it verbatim rather than as "the diagram was skipped".
- **Documents outside the carrier set.** `docs/notes/`, `docs/archive/`, `docs/.speckit/`, `docs/assets/` and every
  non-document directory are invisible to the judgement: not judged is not the same as judged and passed.
