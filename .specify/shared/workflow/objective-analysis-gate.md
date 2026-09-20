# Objective Analysis Gate (Same-Author Detection Delegation)

**Canonical convention.** When the artifacts a command analyzes were written by the agent now analyzing them, detection MUST be delegated to fresh-context read-only subagents. This file is the single source of truth for that gate; commands link here rather than restating it.

The evidence-state vocabulary this gate borrows (`Unobserved`, configured ≠ used) is owned by `shared/guidelines/better-harness.md` § 证据纪律. Read that for evidence discipline generally; this file is the staffing rule for one specific audit shape.

## Why the gate exists

An agent auditing its own output reproduces its own misreading: both passes read the text the same way, so the second pass confirms the first instead of testing it. The defect class that dominates self-authored artifact sets is precisely the one self-review cannot see — a correction landed in one place and not in the others, because the author knows the intended reading and supplies it silently at every copy.

Delegating only the *validation* of findings does not compensate. A validator may reject, downgrade, or confirm what detection produced; it cannot surface what detection never raised. A defect class invisible to detection stays invisible however many validators run. Detection is therefore the pass that needs an independent reader, and validation is a second, cheaper filter on top of it.

## When the gate fires

- **Fires**: the artifacts under analysis were produced by the agent now running the command, in the current session. The ordinary case is a `requirements → clarify → plan → tasks` chain run without a break, where every artifact is minutes old and shares one author.
- **Does not fire**: the artifacts predate this session, or have a different author (another agent, a human, an upstream release). Independent authorship already supplies the fresh context the gate exists to obtain.
- Mixed sets fire on the self-authored subset; say which subset was delegated.

## The gate

1. **Split by disjoint artifact scope** — one subagent per scope, so no two agents audit the same file pair and none needs the whole artifact set in context. Overlapping scopes produce duplicate findings and hide the gaps that fall between them.
2. **Name the same-author condition in the brief** — a subagent that does not know the artifacts are self-authored will not hunt the defect class that dominates them. State the condition and the multi-pass editing history, and instruct the agent to assume defects exist and locate them, not to report that the artifacts are sound.
3. **Require a propagation-surface answer before any severity** — for every finding the detector MUST list which downstream artifacts inherit it. When the answer is none, severity is capped at the command's own mid tier. This is the cheapest available correction: it moves work upstream and shrinks the validation wave. *(Dated measurement, never a threshold: in the 2026-09-18 run that established this rule, 12 findings reached validation at the top two tiers and 10 were downgraded — every downgrade reason was a propagation fact the detector had not checked.)*
4. **Treat every mapping table as an assertion, never as evidence** — an ID → ID table can be fully self-consistent, both identifiers resolving and the counts agreeing, while the referenced target says something else entirely. Checking that a target *exists* is not checking that it *expresses* the source. Quote the referenced body and judge whether it carries the mapped obligation; this defect class is invisible to any ID-level cross-check.
5. **Keep detection and validation disjoint** — no agent validates a finding it produced. Where a command runs both passes, they are separate agent sets.
6. **Report the condition and the downgrade rate** — state in the report that the same-author condition held, how detection was split, and how many findings validation downgraded. A downgrade rate near zero on a self-authored set is itself a signal worth reading: either the artifacts are unusually clean or detection asked for too little.
7. **Subagent-unavailable fallback** — if dispatch fails twice in a row (upstream error), degrade to a direct bounded read and mark every resulting row (for example `(detected: direct read, subagent unavailable)`) so the weaker evidence path stays visible to the reader. Never let the fallback pass silently as the delegated path.

## Severity vocabulary is owned locally

Rule 3 states the cap as "the command's own mid tier" and deliberately carries no per-command tier table. Commands do not share one severity vocabulary, and each vocabulary is owned by its command template; enumerating them here would create copies free to drift the moment a command retiers. Every binding command names its own literal cap in its own pointer, and a command with no tiers states the local analogue instead (what it must not raise, or what each emitted item must name).

## Binding set is owned by the test

The authoritative roster of commands carrying this gate is `tests/contract/test_objective_analysis_gate.py`, not a list restated here — per the owner-selection order in `shared/guidelines/one-source-of-truth.md`, code outranks an authored document for a fact a program can derive. Discover the live set with:

```bash
grep -rl 'objective-analysis-gate.md' templates/commands/
```

## Scope limits

Keep the gate cheap — it is a staffing decision, not a subsystem (Principle IX):

- **Applies to**: commands that produce findings, severities, or verdicts about artifacts.
- **Does NOT apply to**: deterministic program validators (`validate-tasks.py`, `scan-confirmation-gates.py`, mirror `--check`) — a program has no authorship bias, and this is why the house prefers program-first for fixed rules; measurement steps that RUN a command and READ its output (`/speckit.implement`'s gate function); explicit self-reflection (`/speckit.feedback` Mode 5 自省), where the same-author condition is the point rather than an obstacle; verification of external sources (`/speckit.research`, `/speckit.derive`), whose subject was not authored here.
- **A trivial or no-op run skips it.** Do not dispatch subagents to audit a run that produced nothing.
- **Reach of the ambient pointer**: the Documentation Map row for this file is added to `templates/instructions-template.md`, and `generate-instructions.sh` reconciles only at top-level `## ` section granularity — so that row reaches freshly-initialized projects and this repo's live instructions file, but is NOT injected into an already-initialized downstream project. The command pointers are the surface that actually reaches every project, because a command template is read in full at invocation.
