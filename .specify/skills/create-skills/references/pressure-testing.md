# Pressure Testing Skills (RED-GREEN)

Method adapted from superpowers' `writing-skills` TDD discipline (skill creation treated as RED-GREEN-REFACTOR) to Spec Kit's subagent dispatch model. Applies to `create-skills` (before Register) and to `improve-skills` (for behavior-changing edits).

## Why

A skill that reads well can still fail under pressure: agents rationalize around rules ("just this once", "the user is in a hurry", "this case is different"). Static validation (frontmatter, size, paths) cannot catch this — only observing an agent attempt the task can.

## Method

### 0. Pre-dispatch — name the discriminating observation

Before either arm runs, state the **single observation that would distinguish RED from
GREEN**: the concrete behavior, refusal, phrasing, or artifact the skill causes that this
scenario would not produce on its own. If the host environment cannot produce such an
observation — both arms would reach the same outcome for unrelated environmental reasons
(tooling defaults, host guardrails, affordances baked into the scenario) — the test cannot
prove anything: declare it **inconclusive**, and redesign the scenario or the stressor until
the arms diverge observably. An inconclusive result is never recorded as a pass.

### 1. RED — run the scenario WITHOUT the skill

- Construct one realistic **pressure scenario**: a task the skill should govern, plus a stressor (time pressure, a plausible shortcut, an instruction that tempts rule-bending).
- Dispatch a fresh subagent (no access to the skill body) with the scenario.
- **Record verbatim** what it does wrong and every rationalization it produces. These are the failure modes the skill must close.
- If the subagent already behaves correctly without the skill, the skill may be unnecessary — surface this to the user before continuing.

### 2. GREEN — run the same scenario WITH the skill

- Dispatch a fresh subagent whose prompt includes the skill body (or instructs it to load the skill).
- **Load proof — required.** The GREEN report must cite something only a reader of the skill could know: a verbatim quote (heading + text) of the section that governs the scenario, reproduced by the subagent from the loaded skill. Without that citation, a GREEN "pass" cannot distinguish "the skill governed the behavior" from "the subagent never opened the file" — record it as inconclusive and re-dispatch, never as compliance.
- Verify it now complies: the RED failure modes do not recur, **and** the §0 discriminating observation actually differs between the two arms.
- A pass requires observed compliance, not a plausibility argument.

### 3. REFACTOR — close loopholes

- For each RED rationalization the GREEN run did not fully suppress, add an explicit counter to the skill (a MUST/MUST NOT line, a red-flag phrase list, or a rationalization table entry).
- Re-run GREEN until clean or the remaining gap is explicitly accepted by the user.

## Dispatch template

```
Subagent prompt (RED):  <scenario task + stressor>. Do NOT load any skill.
Subagent prompt (GREEN): <same scenario>. Load the skill at <path>. Before answering, quote
  verbatim the section that governs this scenario (heading + text), then answer strictly
  under that section. Your reply MUST contain the quote — a reply without it is a failed
  load, not a compliant run.
```

Use a read-only/worktree-isolated subagent when the scenario would otherwise write files.

## Scope & waiver

- MANDATORY for new discipline/workflow skills (skills that constrain agent behavior).
- OPTIONAL for pure utility skills (wrappers around deterministic scripts) — static validation plus a smoke invocation suffices; state which case applies in the report.
- The user may waive the pressure test explicitly; record the waiver in the creation report.

## Record

Append to the skill creation/improvement report: scenario used, the §0 discriminating observation, RED failures (verbatim), GREEN outcome with its load-proof quote — or the inconclusive verdict and why — and loopholes closed. One scenario well-observed beats five imagined.
