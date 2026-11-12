# Artifact and Implementation Review — per-dimension detail

Owner: `.specify/skills/internal/review-feature-quality/SKILL.md` § Segment A / § Segment B. This file carries the
**detail** of those two segments — the checklists a run walks, the coverage-line shape, the finding field
set and the smoke record's fields. It states no composition, no order and no boundary sentence: those are
owned by `.specify/shared/workflow/acceptance-hardening.md` § Review Composition, and no sentence here restates
them.

The severity tokens named below (`P0`, `P1`, `P2`) belong to `.specify/skills/internal/review-sdd-process/SKILL.md`
§ Severity Vocabulary. They are cited, never redefined, and they are never converted into the six-level
code family that `.specify/skills/internal/code-review/SKILL.md` owns.

## A. Artifact segment

### A.1 What the run reads

| Read | For |
|------|-----|
| the expected set's members under `REQUIREMENTS_DIR` | completeness and the coverage line |
| `tasks.md` row set, with each row's sigil | traceability and closed-row honesty |
| `verification.md` `SC-NNN_status=` rows | traceability and acceptance honesty |
| the feature detail's claimed status and `Latest Review` entry | acceptance honesty against the record |
| the plan/tasks tables' pointer targets | dependency and premise ownership |
| the contracts' clause ids the artifacts cite | internal consistency between clause and carrier |

### A.2 The coverage line

The line is written `checked / expected` and printed once per artifact segment run:

```
Artifacts: <checked> / <expected>   missing: <member>, <member> | none
```

- `expected` is the size of the **expected set** — never the count of files that happen to be present.
- `missing` names every expected member that is absent, one per comma. A missing member that is neither
  named here nor raised as a finding is a silent gap, and a silent gap is the failure the denominator
  exists to prevent.
- `missing: none` is only writable when the expected set and the present set are the same set.

A run whose line reads `N / N` while a required member is absent has read the directory instead of the
expected set. That reading is wrong by construction, not by judgement.

### A.3 Checklist per dimension

**Completeness**

- [ ] every expected member exists on disk;
- [ ] each member carries the sections its template requires (a `verification.md` without per-criterion
      status rows is incomplete, not merely thin);
- [ ] a member that exists but is a placeholder — a template with tokens unfilled — is a finding.

**Internal consistency**

- [ ] a threshold, count, enumeration or path literal appears once and is referenced elsewhere;
- [ ] a clause id cited by a carrier exists in the contract that owns it;
- [ ] the feature detail's status and the registry row agree;
- [ ] no artifact states a fact its owner does not state.

**Traceability**

- [ ] every `FR-…` reaches at least one task row;
- [ ] every task row reaches a success criterion or an evidence artifact;
- [ ] every `SC-…` reaches the evidence that moves it, and the evidence path exists;
- [ ] a criterion supported only by its own restatement is a broken link.

**Dependency and premise ownership**

- [ ] an inherited dependency names its owner, its carrier and its status;
- [ ] a premise a row rides on is stated where its owner lives, not copied into the row;
- [ ] a carrier that does not resolve is a finding, however well-formed the row looks.

**Acceptance honesty**

- [ ] every `pass` has the measurement that produced it;
- [ ] a red-first claim has a recorded red run with command, output and failing count;
- [ ] a `deferred` row carries its reason;
- [ ] a status claim the counts do not support is a `P0`.

### A.4 Severity assignment

The `P0`/`P1`/`P2` meanings are owned once, by the report template's severity table; this segment
applies them, it does not define them. The grading procedure is the only thing stated here:

1. read the owner's table;
2. grade the finding by its consequence — for an artifact finding, the consequence for a reader acting
   on the artifacts; for an implementation finding, the consequence for the slice's correctness, scope
   or regression;
3. when two levels could apply, take the higher one and write the reason in the finding.

No second table, no paraphrase of the owner's level meanings.

### A.5 Finding field set

Each finding is one row carrying exactly these fields:

| Field | Content | Rule |
|-------|---------|------|
| `severity` | one of `P0` / `P1` / `P2` | required |
| `artifact path` | repo-relative path of the expected member | required |
| `line` | line number inside that artifact | required whenever the artifact is line-addressable |
| `why the line is absent` | the reason, in the finding itself | required only when `line` is absent |
| `what is wrong` | one sentence, pointing at the defect | required |
| `what would fix it` | one sentence, naming the artifact section | required |

The `line` rule is a MUST with one escape: a **stated reason**. A markdown artifact is line-addressable,
and so is any row-shaped artifact whose row number can be computed. The escape exists for artifacts that
genuinely cannot be addressed by line — a binary, a generated file whose lines move on every run — and a
finding that uses it MUST say which case it is. No field of the set is conditional on anything else.

## B. Implementation segment

### B.1 What the run reads

| Read | For |
|------|-----|
| the resolved `base..head` range | the judgment object itself |
| `requirements.md` | correctness — what the delta was supposed to do |
| `tasks.md` | scope — what the delta was allowed to do |
| the feature's smoke record | the smoke triple |
| the closure checker's `final_path` record | a quotation only; never a bucket the segment re-counts |

`base` and `head` come from one place: `.specify/skills/internal/code-review/scripts/git-delta-review.sh`. Its
`base` step owns the ordered resolution tiers, the closed trunk order and the run-start-fixed head. The
segment records the pair it was given and resolves nothing a second time.

### B.2 The smoke triple

| Slot | Content | Rule |
|------|---------|------|
| command | the smoke command, verbatim | required; a paraphrase is not a command |
| exit code | the integer the command returned | required; `0` is `pass`, anything else is a finding |
| evidence path | the file holding the output | required; must exist and be non-empty |

A record carrying two of the three is not a verdict. A feature whose smoke cannot be made deterministic
on a local fixture is a finding, and the environment is not an exemption.

### B.3 Checklist per judgment

**Correctness**

- [ ] each requirement the slice claims is implemented has a delta hunk that implements it;
- [ ] the acceptance evidence the slice claims is the evidence this delta produced;
- [ ] a claimed behaviour that no test or fixture exercises is a finding, not a gap to note.

**Scope**

- [ ] no hunk implements work no requirement and no task row asks for;
- [ ] no task row is closed by a fragment of itself;
- [ ] a change to a surface outside the slice's declared paths is either declared or a finding.

**Regression**

- [ ] every behaviour an earlier criterion measured is re-measured;
- [ ] a changed public surface updates its callers in the same delta;
- [ ] a pre-existing failure the slice inherits is recorded as inherited, not as introduced.

### B.4 The `final_path` quotation

When the run has a `final_path` record, this segment may quote it — the seven keys, copied, on one line,
with the checker named as the source. It never recomputes a bucket, never narrows the record to a
summary and never treats the record as its own verdict. The record answers a different question (may the
feature be called `Implemented`?), and its hard condition is the implement gate's.
