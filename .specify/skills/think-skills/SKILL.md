---
name: think-skills
description: |
  This skill can mentally simulate a Skill or prompt to verify likely execution behavior without real side effects. Use this when the user mentions ["thought experiment", "mental dry run", "simulate a skill", "simulate a prompt", "pretend to run", "dry-run prompt", "verify prompt logic", "验证技能执行效果", "思想实验", "不要真的执行"].
skill_id: "<SKILL:.specify/skills/think-skills/SKILL.md>"
---

# think-skills

## Goal

Verify the likely behavior of another Skill, prompt, workflow, or instruction set by running a structured mental simulation only. The result should expose hidden assumptions, skipped logic, conflicts, side effects, and edge-case failures before any real execution occurs.

## Operating Rules

- Do not actually execute the target Skill, prompt, code, commands, network calls, file writes, tool calls, or external actions during the simulation.
- Reading the target text is allowed when needed; triggering its side effects is not.
- Use an auditable trace table or state object instead of claiming that anything really ran.
- Mark uncertainty explicitly. Do not invent facts, tool outputs, files, timing behavior, or empirical results.
- If the target requires real execution for confirmation, label that as a validation gap rather than simulating certainty.

## Workflow

1. **Identify target and scenario**
   - Determine the target Skill, prompt, or workflow to simulate.
   - Capture the user request, inputs, environment assumptions, allowed tools, forbidden actions, and desired output.
   - If critical target text or scenario data is missing, ask one targeted clarification question.

2. **Build the simulation contract**
   - List `Initial State`, `Rules`, `Known Constraints`, `Assumptions`, and `Unknowns`.
   - Define what counts as a side effect and explicitly mark it as forbidden for this run.
   - Choose the trace mode:
     - `Line-by-line` for code-like prompts or procedural Skills.
     - `State machine` for workflows, agents, tool orchestration, or multi-step user journeys.
     - `Devil's advocate` for robustness, adversarial edge cases, and prompt patching.

3. **Run the mental trace**
   - Process the target step by step.
   - For each step, record:
     - `Step`
     - `Trigger / Instruction`
     - `Mental Action`
     - `State Delta`
     - `Consistency Check`
     - `Risk / Uncertainty`
   - When a step would use a real tool or cause a side effect, write `would execute`, infer only the logical intent, and continue with a clearly marked hypothetical state.

4. **Stress-test edge cases**
   - Simulate at least three scenarios when scope permits:
     - Happy path with clear inputs.
     - Missing, ambiguous, or contradictory input.
     - Tool failure, forbidden side effect, stale context, or policy/constraint conflict.
   - For loops or repeated steps, trace the first few iterations in detail, then summarize the invariant or stopping condition. Do not hallucinate large traces.

5. **Audit the simulation**
   - Check whether any step falsely claimed real execution.
   - Check whether any state update skipped a rule or depended on a hidden assumption.
   - Check whether the target over-promises reliability where real execution, tests, or empirical data are required.
   - Revise the trace if the audit finds inconsistencies.

6. **Report verdict and patches**
   - Provide a concise verdict: `Likely works`, `Works with caveats`, `Ambiguous`, or `Likely fails`.
   - Summarize expected behavior, failure modes, and validation gaps.
   - Recommend minimal prompt or Skill changes using precise instruction text.

## Output Template

```markdown
## Simulation Scope
- Target:
- Scenario:
- Forbidden real actions:

## Initial State / Rules / Assumptions
- Initial State:
- Rules:
- Assumptions:
- Unknowns:

## Mental Trace
| Step | Trigger / Instruction | Mental Action | State Delta | Consistency Check | Risk / Uncertainty |
|---|---|---|---|---|---|

## Edge Cases
1. Happy path:
2. Missing or conflicting input:
3. Tool/action failure or forbidden side effect:

## Self-Audit
- Real execution claims:
- Skipped logic:
- Hidden assumptions:
- Needs real validation:

## Verdict
- Result:
- Likely behavior:
- Failure modes:
- Minimal patches:
```

## Resources

- Prompt fragments and reusable templates: `./references/prompt-templates.md`

## Resource ID
- Canonical ID: `<SKILL:.specify/skills/think-skills/SKILL.md>`
- Canonical Path: `.specify/skills/think-skills/SKILL.md`

## Available Tools & Resources

### Scripts (`./scripts/`)
- No scripts required.

### References (`./references/`)
- `./references/prompt-templates.md` — mental dry-run, state-machine, devil's advocate, and self-audit prompt fragments.

### Assets (`./assets/`)
- No assets required.
