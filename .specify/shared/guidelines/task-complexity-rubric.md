# Task Complexity Rubric

Single source of truth for the task-complexity thinking tiers. Referenced from the `## Task Complexity Rubric` summary in `.specify/instructions.md` — keep that summary a pointer; the full rubric lives here.

Right-size your thinking to the task. Under-thinking complex or high-stakes tasks causes defects and rework (a **quality** cost); over-thinking trivial tasks wastes time and adds noise (an **efficiency** cost). Aim for the lowest thinking depth that safely fits the task — escalate when in doubt, and do not default to maximal effort.

Classify each task by these signals: scope/size, uncertainty/novelty, blast radius/reversibility, cross-cutting impact, and requirements clarity. Then adopt the matching tier's thinking depth:

| Tier | Typical signals | Thinking depth (what to actually do) |
|------|-----------------|--------------------------------------|
| **Trivial** | Tiny, well-scoped edit; no uncertainty; easily reversible; no cross-cutting impact; requirements crystal-clear | **Minimal** — act directly; little to no exploration; no written plan; a light sanity check (build/lint or the one relevant test) |
| **Standard** | One area or a few files; low uncertainty; moderate, reversible risk; little cross-cutting; requirements clear | **Moderate** — read the directly relevant files; form a brief internal plan; run the related tests |
| **Complex** | Multiple files/modules; real uncertainty or design choices; harder to reverse; cross-cutting; requirements mostly clear | **Deep** — explore broadly before editing; write an explicit plan (consider plan mode); weigh alternatives; add/adjust tests and verify behavior |
| **High-stakes / Ambiguous** | High blast radius (shared infra, data migration, security, public API); hard or irreversible; or requirements unclear/conflicting | **Exhaustive** — thorough exploration; explicit plan with user checkpoints; edge-case and adversarial analysis; strong verification; confirm before irreversible actions; resolve unclear requirements first |

> Gate probe: gate-rubric-high-stakes — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

- **Tie-break**: when a task's signals span more than one tier, choose the **higher tier**. Blast-radius/reversibility and requirements clarity dominate — a tiny edit to a shared, irreversible, or security-sensitive surface is High-stakes, not Trivial.
- **Default**: if a task cannot yet be classified, treat it as **Standard**; but when the reason is unclear or under-specified requirements, that is itself a High-stakes / Ambiguous signal — clarify before proceeding rather than guessing.
