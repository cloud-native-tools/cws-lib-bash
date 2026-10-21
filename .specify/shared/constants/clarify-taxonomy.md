# Clarify Taxonomy

This document contains the detailed taxonomy coverage categories for the three clarification modes in `/speckit.clarify`.

## Mode A: Post-Requirements (Target: `requirements.md`)

### Taxonomy Coverage Scan

For each category below, mark status (Clear / Partial / Missing):

**Feature Linkage:**
- `Related Feature` section has concrete `Feature ID` and `Feature Name`
- The requirement-to-feature relationship is explicit and internally consistent
- When proposing bind-vs-create, list candidate Features with their Status and a one-line scope summary so overlap is judged on evidence, not recall
- **Owner anchor**: the binding rules this category depends on — candidate scan → bind-or-create → integration responsibilities — are owned by `.specify/shared/workflow/feature-integration.md` § Feature Binding Rules. Read that section before proposing options; this taxonomy deliberately does not restate it.

**Functional Scope & Behavior:**
- Core user goals & success criteria
- Explicit out-of-scope declarations
- User roles / personas differentiation

**Domain & Data Model:**
- Entities, attributes, relationships
- Identity & uniqueness rules
- Lifecycle/state transitions
- Data volume / scale assumptions

**Interaction & UX Flow:**
- Critical user journeys / sequences
- Error/empty/loading states
- Accessibility or localization notes

**Non-Functional Quality Attributes:**
- Performance (latency, throughput targets)
- Scalability (horizontal/vertical, limits)
- Reliability & availability (uptime, recovery expectations)
- Observability (logging, metrics, tracing signals)
- Security & privacy (authN/Z, data protection, threat assumptions)
- Compliance / regulatory constraints (if any)

**Integration & External Dependencies:**
- External services/APIs and failure modes
- Data import/export formats
- Protocol/versioning assumptions

**Edge Cases & Failure Handling:**
- Negative scenarios
- Rate limiting / throttling
- Conflict resolution (e.g., concurrent edits)

**Constraints & Tradeoffs:**
- Technical constraints (language, storage, hosting)
- Explicit tradeoffs or rejected alternatives

**Terminology & Consistency:**
- Canonical glossary terms
- Avoided synonyms / deprecated terms

**Completion Signals:**
- Acceptance criteria testability
- Measurable Definition of Done style indicators

**Misc / Placeholders:**
- TODO markers / unresolved decisions
- Ambiguous adjectives ("robust", "intuitive") lacking quantification

**Deferred-by-assumption:**
- Reads the artifact's Assumptions (and any `Assumption:` rows recorded elsewhere in it) and asks of each entry whether it holds a **decision already taken** or a **choice still open**. Formal completeness is not semantic completeness: an entry carrying an ID and a well-written sentence defers a choice just as effectively as a TODO marker, and `Misc / Placeholders` does not catch it because that category scans markers and unquantified adjectives only.
- Hit conditions — any one makes the entry Partial or Missing, never Clear:
  - the entry sits between **named alternatives**: two or more candidate options are written down and the entry adopts one as tentative / provisional / for-now rather than as decided;
  - the entry **names a later phase or artifact as the decision-maker**: plan, tasks, implement, a `/speckit.*` command, "at design time", "when the implementation lands";
  - the entry carries a **conditional escalation clause**: "if X turns out to be Y, revisit / re-open / escalate".
- Stays Clear here: an entry that fixes a value with **no competing alternative named and no later phase nominated** — a recorded environment fact, a scope boundary, a technology constant. An entry whose alternative is written as **rejected** rather than **postponed** belongs to `Constraints & Tradeoffs`, not to this category.
- A hit becomes a candidate question only through the materiality filter `/speckit.clarify` already applies: worth asking when the answer changes a downstream artifact, not merely because the entry reads as unfinished.

### Mode A Integration Rules

After each accepted answer:
- Ensure `## Clarifications` exists (create after highest-level overview section). Under it, `### Session YYYY-MM-DD`.
- **Coexistence with pre-session-format rows**: specs may already carry legacy loose `- Q: …` bullets without a session heading. Those rows are historical record — leave them untouched and append the new `### Session YYYY-MM-DD` block after them. NEVER "normalize" legacy rows into a session heading (that rewrites history); the append-only invariant below applies to them as well.
- Append: `- Q: <question> → A: <final answer>`
- **Multi-answer ordering**: when one round returns several answers (a batched prompt, or one answer carrying sub-decisions), each answer still gets its own appended row, and the integration order is **target artifact first, Feature registry second** — land and save every spec-side change, then discharge the Feature obligations below. Never leave a saved spec naming a Feature whose registry duties are still pending; if the run stops between the two, the pending registry duties are the recovery point and the report says so.
- Apply to most appropriate section:
  - Feature linkage (both branches) → Update `Related Feature` with `Feature ID` and `Feature Name`. When the answer is a **new** Feature, the obligation continues: allocate the next ID from `.specify/memory/features.md`, add the index row (Draft) and `features/<ID>.md` detail, and add the reverse cross-reference in the neighbouring Feature — otherwise the spec points at an unregistered Feature that `/speckit.analyze` will flag. If the neighbouring Feature is a legacy entry with **only an index row and no detail file**, do NOT create a detail file for it — record the承接 relation in the **new** Feature's detail file (`Related Specifications`) instead.
  - Feature linkage (**existing**-Feature branch) → discharge the integration responsibilities owned by `.specify/shared/workflow/feature-integration.md` § Feature Binding Rules (that section is the owner — not restated here), plus what it leaves to this checkpoint: the new spec appears in the bound Feature's detail file (its related-specifications section, with a review/notes entry recording why this spec belongs to that Feature) and the index row's `Last Updated` cell carries the follow-up note. Binding to an existing Feature is NOT a no-op, and a status that is lawfully held (one that MUST NOT regress) never waives these duties — record the stage even when the status stays put.
  - Functional ambiguity → Update/add bullet in Functional Requirements
  - User interaction → Update User Stories or Actors
  - Data shape → Update Data Model (fields, types, relationships)
  - Non-functional → Add/modify measurable criteria in Quality Attributes
  - Edge case → Add bullet under Edge Cases / Error Handling
  - Terminology → Normalize across spec; note `(formerly "X")` once if needed
- **A surfaced tension is integrated, never dropped**: when the chosen option carries an identified cost or semantic tension (including the one named in its consequence preview — that preview is required by `/speckit.clarify`'s questioning format, not defined here), the same integration pass MUST also write the corresponding binding clause into the artifact — a constraint or requirement clause, or an Edge Case stating the boundary the choice creates. Recording the `- Q: → A:` row alone leaves the cost unowned and it resurfaces downstream as a finding. Dropping a tension by not writing it down is not a resolution; if the user accepts the cost knowingly, the clause records that it is accepted and under what condition.
- If invalidates earlier statement, replace it (no duplicates) — but first test whether the two actually conflict: when both hold in different contexts (repo source vs installed copy, different runtime modes, different tool tiers), do NOT replace; keep both in the same requirement with their applicability conditions stated. Replace only when one side is genuinely falsified.
- **Removal & renumbering**: when an accepted answer removes FRs/user stories, renumber the LIVE IDs to stay contiguous, but NEVER touch prior `## Clarifications` entries (append-only) — instead emit an explicit `旧→新` numbering map in the new session entry, and mechanically rewrite every live `FR-\d+`/`SC-\d+` reference outside `## Clarifications` per that map (a prose map documents the change; it does not perform it — verify zero stale references by grep afterwards)
- **Derived-count revisit**: renumbering does not stop at the spec. `checklists/requirements.md` carries derived counts (how many FR / SC / STR / Entity / Story rows the spec has) that the renumbering just falsified, and nothing else in this checkpoint revisits them — `/speckit.checklist` only ever creates a new file, so a stale count survives until a downstream phase trips over it. After any FR/SC addition, removal, or renumbering, re-check that checklist:
  - file exists → re-measure the live counts from the spec with the extraction in the document-order invariant below (same two anchors, same command prefix) and refresh the checklist's numbers in place;
  - file absent → record it as **pending generation** in the session entry rather than silently skipping it;
  - then assert zero residual stale counts by grep: for each count whose value changed, the superseded literal MUST return no hit (the literals below are the values this run superseded, not fixed text).

    ```bash
    grep -nE 'FR 36|SC 16' <spec-dir>/checklists/requirements.md   # MUST print nothing once refreshed
    ```

  The checklist's own structure and the full count set are owned by `.specify/shared/guidelines/requirements-guidelines.md` § Create Spec Quality Checklist — measure from the spec, never carry the checklist's previous numbers forward.
- **Append-only invariant (all modes)**: `## Clarifications` session entries are historical record — integrations MUST append new rows, never rewrite or replace existing ones. After each integration, re-count the entry rows (`- Q:` / `- 用户修订指示`) and verify the count strictly increased; a decreased or equal count means an Edit replaced history — restore the lost row before proceeding.
- **Document-order invariant (Mode A)**: a contiguous ID *set* is not an ordered *document* — the two come apart the moment an answer inserts a requirement mid-list, and the ID-set check above stays green through it. After any integration that adds, removes, or rewrites a Functional Requirement or Success Criterion, compare the live definition sequence **in order of appearance** against ascending order and report one `ORDER BREAK: <ID> after <ID>` line per inversion. The verdict comes from the comparison's output, never from re-reading the artifact: **empty output means ordered**. This assertion shares one implementation with `/speckit.requirements`' deterministic spec validator — it *is* that validator, `.specify/scripts/python/validate-requirements.py`, so the two commands cannot drift about what "in order" means. Discharge it by running the checker and reading its `doc-order` verdict:

  ```bash
  python3 .specify/scripts/python/validate-requirements.py <spec-dir>/requirements.md
  ```

  Both anchors are load-bearing, not decoration: comparing every `FR-\d+` *occurrence* instead of every *definition* flags cross-references, which are legitimately out of order — measured on a clean spec, the occurrence form reports five false breaks where the definition form reports none; and including `## Clarifications` turns append-only history that quotes pre-renumbering definition lines into a false break. Repair an `ORDER BREAK` before the run reports completion — reorder the requirement, or renumber to document order under the numbering-map rule above.
- Save `requirements.md` after EACH integration

---

## Mode B: Post-Plan (Target: `plan.md`)

### Taxonomy Coverage Scan

**Technical Context Completeness:**
- Language/Version, Primary Dependencies, Storage, Testing, Target Platform are all resolved
- Project Type is specified
- Performance Goals, Constraints, Scale/Scope have concrete values

**Constitution Check:**
- All Core Principles have explicit compliance status
- Gates Status is determined (all pass, or specific violations with justification)
- Any complexity tracking violations have full justifications

**Project Structure:**
- Documentation tree and Source Code tree are both filled in
- Structure Decision explicitly states the chosen layout
- Paths reflect real directories

**Requirements Coverage:**
- Each user story maps to at least one design artifact (data-model entity, contract endpoint, or quickstart scenario)
- No orphan user stories with zero design coverage
- No unjustified scope creep (design artifacts with no user story)

**Data Model Alignment:**
- Every entity in `data-model.md` has corresponding requirements grounding
- Entity relationships match requirement narratives
- Validation rules reflect functional requirements

**API Contract Alignment:**
- Each endpoint in `contracts/` maps to at least one user story or functional requirement
- HTTP methods, paths, request/response schemas are fully specified
- Error response codes correspond to edge cases in requirements

**Consistency & Cross-Artifact Gaps:**
- Terminology matches between `plan.md` and `requirements.md`
- `research.md` decisions are reflected in Technical Context
- `quickstart.md` scenarios align with user stories
- No `NEEDS CLARIFICATION` markers remain

**Feasibility & Risk:**
- Selected tech stack compatible with constitution constraints
- Scale/Scope assumptions realistic given Performance Goals
- External dependency failure modes acknowledged

### Mode B Integration Rules

After each accepted answer:
- Ensure `## Clarifications` in `plan.md` (after Summary section). Under it, `### Session YYYY-MM-DD`.
- Append: `- Q: <question> → A: <final answer>`
- Apply to most appropriate location:
  - Technical Context unknowns → Resolve "NEEDS CLARIFICATION" fields
  - Constitution Gate → Update Gates Status with resolution
  - Structure gaps → Fill missing paths or update Structure Decision
  - Data model gap → Record decision; recommend re-running `/speckit.plan` if regeneration needed
  - Contract gap → Record endpoint/API decision; recommend re-running if needed
  - Terminology drift → Normalize in `plan.md`
  - Feasibility risk → Add mitigation note in Constraints or Complexity Tracking
- Save `plan.md` after EACH integration
- Do NOT modify `requirements.md` in this mode

---

## Mode C: Post-Tasks (Target: `tasks.md`)

### Taxonomy Coverage Scan

**Story Coverage & Prioritization:**
- Every user story from `requirements.md` has a corresponding Phase
- Story priorities (P1, P2, P3) preserved in task ordering
- MVP scope clearly identifiable and independently testable

**Task Completeness Per Story:**
- Each phase includes: goal, independent test criteria, tests, implementation tasks
- Test tasks precede implementation tasks (TDD order)
- Implementation tasks cover models, services, endpoints, error handling
- Verification/manual QA tasks present where automated tests insufficient

**Dependency Correctness:**
- Setup (Phase 1) tasks have no story dependencies
- Foundational (Phase 2) tasks correctly marked as blocking
- All story implementation tasks depend on Foundational completion
- Intra-story ordering respects code dependencies
- Parallel markers [P] correctly applied (different files, no shared state)

**File Path Validity:**
- All task file paths resolve within project structure defined in `plan.md`
- No paths reference non-existent directories without creation instructions
- Test file paths mirror implementation paths

**Definition of Done:**
- DoD checklist filled (not template placeholder text)
- DoD items measurable and verifiable
- DoD aligns with Constitution quality gates

**Format Compliance:**
- All tasks follow `[ID] [P?] [Story] Description` format
- Task IDs sequential and unique
- No template sample tasks remain

**Phase Dependencies & Parallelization:**
- Phase Dependencies section reflects actual blocking relationships
- Parallel execution examples realistic
- Implementation strategy provides clear MVP-first guidance

### Mode C Integration Rules

After each accepted answer:
- Ensure `## Clarifications` in `tasks.md` (after Prerequisites/Input section). Under it, `### Session YYYY-MM-DD`.
- Append: `- Q: <question> → A: <final answer>`
- Apply to most appropriate location:
  - Missing story → Add new Phase with goal, test criteria, placeholder tasks
  - Task completeness → Add missing tasks within relevant Phase
  - Dependency ordering → Reorder tasks or update [P] markers
  - Incorrect file paths → Correct the path
  - DoD gaps → Fill missing checklist items
  - Format violation → Normalize task format
  - Parallelization → Update parallel execution examples or add [P] markers
- Save `tasks.md` after EACH integration
- Do NOT modify `requirements.md` or `plan.md` in this mode
