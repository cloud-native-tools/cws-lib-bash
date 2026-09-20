# Self-Improvement Pattern（自我提升模式）

A reusable architecture for an Execution Subject that learns from its own completed runs
without becoming a self-authorizing or self-certifying mutation loop. Concept ownership:
`shared/definitions/self-improvement-definitions.md`. Normative gates:
`shared/guidelines/self-improvement.md`. Canonical execution order:
`shared/workflow/self-improvement-workflow.md`.

## When to Apply

Apply when all are true:

1. the target qualifies as an Execution Subject;
2. the same durable identity will execute again;
3. own-run evidence can be associated with that identity;
4. one canonical definition can be changed for future runs; and
5. current and later runs can produce a comparable signal.

Do not apply to a one-shot report, transient Agent Execution, static document, or artifact
with no future invocation. Improve those through an assisted edit or their owning mechanism.

## Roles, Not Necessarily Processes

The pattern separates responsibilities even when one agent runtime performs several of them:

| Role | Responsibility | Independence rule |
|------|----------------|-------------------|
| **Subject** | Owns the execution contract and initiating own-run signal | Stable identity across runs |
| **Observer** | Captures scoped facts after a completed run | Does not mutate while observing |
| **Improver** | Applies frozen, evidence-backed candidates to the canonical owner | Usually the matching `improve-*` skill |
| **Verifier** | Checks the intervention and later outcome | Separate execution when the guideline requires independence |
| **Authority** | Owns decisions outside the subject’s mutation boundary | User/governance source; never impersonated by the subject |

Self-Improvement is preserved when the Subject delegates to an Improver or Verifier. It turns
into Assisted Improvement when another actor originates the change direction.

## Two Coupled Loops

```text
FAST LOOP — one intervention cycle
own run → observe → qualify/freeze → diagnose → gate → edit owner → validate → ledger

SLOW LOOP — outcome closure
later comparable run → compare to ledger → outcome-supported | unchanged | regressed
```

The fast loop may prove that a change was applied and currently validates. Only the slow loop
may prove that the subject improved.

## Stable Artifact Reuse

The pattern introduces no new global store. Reuse existing artifacts:

| Need | Existing artifact/mechanism |
|------|-----------------------------|
| Reflection signal | Feedback entry when the subject is a qualifying Spec Kit unit |
| Normalized observations | evidence `findings.json` |
| Baseline and expected direction | evidence-run `intervention.json` |
| Run outcome | agent logs, team run report, tool invocation record, Skill execution evidence |
| Durable lesson | memory/history when reusable beyond the intervention |
| Global Harness finding | `/better-harness` or `/speckit.review` assisted review |

## Subject Adapters

### Agent Adapter

- Subject identity: Agent Template or Instance, never a live Execution.
- Own-run evidence: execution logs, result manifests, handoff failures, user corrections.
- Improver: `improve-agent`, with the target layer explicit.
- Mutation boundary: template/instance definition or execution config; runtime logs stay read-only.
- Verifier: a fresh agent execution for behavior changes.

### Skill Adapter

- Subject identity: canonical Skill directory.
- Own-run evidence: feedback entry, session trace, artifact/result mismatch, pressure-test result.
- Improver: `improve-skills`.
- Mutation boundary: `SKILL.md` and owned `references/`, `scripts/`, `assets/`; mirrors regenerate.
- Verifier: conformance tests plus RED-GREEN for behavior-changing instructions.

### Tool Adapter

- Subject identity: Tool record, not the external executable.
- Own-run evidence: invocation result, preflight failure, version/platform drift, user correction.
- Improver: `improve-tools`.
- Mutation boundary: record fields and behavioral rules; external binary is never rewritten.
- Verifier: source/preflight/schema validation; real invocation remains behind the Tool invoke gate.

### Team Adapter

- Subject identity: persisted `team.md`.
- Own-run evidence: run reports, post-run critique, convergence, conflicts, budget/circuit-breaker events.
- Improver: `improve-team`.
- Mutation boundary: team goal only when explicitly authorized, roster, pattern, config, territories.
- Verifier: independent team verifier for behavior or autonomy changes.

## Composition with Existing Patterns

- **Reconcile inside Self-Improvement**: the intervention may use a reconcile engine to update a
  durable space. Reconcile closes current-state drift; the later comparison closes learning.
- **Continuous team around Self-Improvement**: a continuous loop may schedule bounded cycles.
  Its maturity/budget/kill-switch rules remain authoritative; Self-Improvement does not create a
  second scheduler.
- **Feedback beside Self-Improvement**: feedback captures reflection; the evidence gate decides
  whether it becomes a candidate.
- **Better Harness above Self-Improvement**: the intervention names which Work Loop dimension it
  targets; cross-dimension findings escalate to system-level assisted review.

## Anti-Patterns

- **Reflection-equals-proof**: editing because a self-review sounds plausible.
- **Same-run contract mutation**: changing instructions mid-run and claiming that run validates them.
- **Self-authorization**: widening permissions, territory, or autonomy without the external authority.
- **Self-certification**: the authoring execution is the only verifier of a behavior-changing edit.
- **Perpetual tuning**: retrying until one favorable signal appears, without bounded attempts.
- **Mirror editing**: changing an installed/runtime copy instead of the canonical owner.
- **Candidate drift**: adding new fixes after the evidence candidate list was frozen.
- **Feedback as command queue**: treating every optional reflection entry as authorized work.

## Design Checklist

- [ ] Subject eligibility and canonical identity are explicit.
- [ ] Self vs assisted origin is disclosed.
- [ ] Observation sources are scoped to completed runs.
- [ ] Evidence Step A/B freezes candidates before edits.
- [ ] Mutation boundary and authority escalation are explicit.
- [ ] Matching `improve-*` executor is named.
- [ ] Current-run validation and later outcome comparison are separate.
- [ ] `intervention.json` records the expected signal.
- [ ] Attempt limit and failure/degrade path are defined.
- [ ] Feedback and mirrors retain their existing red lines.
