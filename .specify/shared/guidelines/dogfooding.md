# Dogfooding Practice

Single source of truth for the two dogfooding loops. Referenced from the `## Dogfooding Practice` summary in `.specify/instructions.md` — keep that summary a pointer; the operational detail lives here. Concept definitions (what dogfooding is, two-hats, three-copies) live in `definitions/dogfooding-definitions.md`.

Dogfooding means the people who build a product also rely on it in their real daily work — developer and user tightly linked, often the same team — so a smooth **use → feedback → iterate** loop forms naturally. A project that provides development-assistance capabilities proves them the way a compiler proves itself by self-hosting: only a tool that performs well in its own engineering has earned the credibility to assist others. This document identifies two loops that already exist — it adds no new tools, steps, or storage.

## Loop A — Feed your framework usage back upstream

Real friction you hit while using the framework's commands and skills is valuable. The built-in feedback chain carries it upstream:

1. **Record** — commands/skills self-record optimization points at wrap-up; you can also record friction you personally hit: `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.<command>" --unit-type command --run-id "<id>" --review "<what happened>" --points "<suggestion>"` (unit-id must be `/speckit.<command>` or `skill:<name>`).
2. **Threshold prompt** — check accumulation with `--action status`; when the count crosses the threshold, a consolidated prompt invites (never forces) submission.
3. **Package** — `--action package` bundles pending entries into a local archive.
4. **Manual submission** — delivering the archive to the framework's install-source repository is a deliberate, manual step. There is **no automatic transmission** of any feedback data; nothing leaves your machine unless you send it.

## Loop B — Build the same loop for your own product

The framework's shipped capabilities are enough to run a Dogfooding loop for **your own product** — no extra tooling required:

| Capability | Role in your product's loop |
|------------|-----------------------------|
| Feedback engine (`feedback-utils.py`) | Record real-use findings about your product with `--unit-id "skill:<scenario-name>"` (unit-id accepts `/speckit.<command>` or `skill:<name>`); track accumulation with `--action status` / `--action list` |
| Memory (session/knowledge) | Persist working notes and distilled lessons from real usage |
| History | Distill past project conversations into reusable knowledge |
| Review | Periodic retrospective checkpoint where findings are revisited |
| Task records (tasks/verification) | Trace each finding to the iteration that addressed it |

## Adoption advice (advisory — never a gate)

- **Staged rollout**: start with the core team first, then widen; forcing 100% usage of an immature product hurts more than it helps (over-idealization).
- **Tailor to your product's shape**: if daily self-use is not suited to your product (embedded firmware, consumer hardware), substitute periodic real-environment drills or a designated proxy user group instead of forcing it.
- **Anti-patterns to avoid**: *formalism* (going through the motions without real reliance), *echo chamber* (only builders participate — bring in non-technical roles), *dead-letter feedback* (findings recorded but never acted on — close or resolve every entry deliberately), *over-idealization* (mandating full usage regardless of maturity).

The test of a healthy loop is simple: do team members rely on the product for real tasks, and does what they report visibly change the next iteration?
