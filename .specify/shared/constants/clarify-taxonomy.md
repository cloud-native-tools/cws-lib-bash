# Clarify Taxonomy

This document contains the detailed taxonomy coverage categories for the three clarification modes in `/speckit.clarify`.

## Mode A: Post-Requirements (Target: `requirements.md`)

### Taxonomy Coverage Scan

For each category below, mark status (Clear / Partial / Missing):

**Feature Linkage:**
- `Related Feature` section has concrete `Feature ID` and `Feature Name`
- The requirement-to-feature relationship is explicit and internally consistent
- When proposing bind-vs-create, list candidate Features with their Status and a one-line scope summary so overlap is judged on evidence, not recall

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

### Mode A Integration Rules

After each accepted answer:
- Ensure `## Clarifications` exists (create after highest-level overview section). Under it, `### Session YYYY-MM-DD`.
- Append: `- Q: <question> → A: <final answer>`
- Apply to most appropriate section:
  - Feature linkage → Update `Related Feature` with `Feature ID` and `Feature Name`
  - Functional ambiguity → Update/add bullet in Functional Requirements
  - User interaction → Update User Stories or Actors
  - Data shape → Update Data Model (fields, types, relationships)
  - Non-functional → Add/modify measurable criteria in Quality Attributes
  - Edge case → Add bullet under Edge Cases / Error Handling
  - Terminology → Normalize across spec; note `(formerly "X")` once if needed
- If invalidates earlier statement, replace it (no duplicates)
- **Append-only invariant (all modes)**: `## Clarifications` session entries are historical record — integrations MUST append new rows, never rewrite or replace existing ones. After each integration, re-count the entry rows (`- Q:` / `- 用户修订指示`) and verify the count strictly increased; a decreased or equal count means an Edit replaced history — restore the lost row before proceeding.
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
