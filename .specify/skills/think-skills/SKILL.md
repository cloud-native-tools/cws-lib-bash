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
   - Identify whether the target Skill bundles executable scripts under its `scripts/` directory. If it does, those scripts are also part of the simulation target — trace their input/output contracts and execution effects, not just the natural-language flow.
   - Capture the user request, inputs, environment assumptions, allowed tools, forbidden actions, and desired output.
   - If critical target text or scenario data is missing, ask one targeted clarification question.

2. **Build the simulation contract**
   - List `Initial State`, `Rules`, `Known Constraints`, `Assumptions`, and `Unknowns`.
   - Define what counts as a side effect and explicitly mark it as forbidden for this run.
   - Choose the trace mode:
     - `Line-by-line` for code-like prompts or procedural Skills.
     - `State machine` for workflows, agents, tool orchestration, or multi-step user journeys.
     - `Devil's advocate` for robustness, adversarial edge cases, and prompt patching.
   - Perform a `Logic Implementation Audit` to separate the two kinds of logic in the target:
     - `Natural Language Logic`: judgmental instructions executed by LLM reasoning (trade-offs, quality review, intent understanding).
     - `Programmatic Logic`: deterministic logic executed by scripts in `${SKILL_HOME}/scripts/`.
     - For `Programmatic Logic`, assume each script runs per the contract described in its docs/comments (input → output mapping). Do not simulate script internals; instead verify the invocation timing, that inputs satisfy the script's preconditions, and that outputs are correctly consumed downstream.

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
   - When a step invokes a script from `${SKILL_HOME}/scripts/`, record it as `deterministic execution`: take the script's contract output directly as the `State Delta` without LLM-level reasoning about its internals. Focus the checks on whether the script's preconditions were satisfied by prior steps and whether its output is correctly used by later steps.

4. **Stress-test edge cases**
   - Simulate at least three scenarios when scope permits:
     - Happy path with clear inputs.
     - Missing, ambiguous, or contradictory input.
     - Tool failure, forbidden side effect, stale context, or policy/constraint conflict.
     - Script failure or abnormal script output — trace the degradation path when a `${SKILL_HOME}/scripts/` script errors, times out, or returns unexpected values.
   - For loops or repeated steps, trace the first few iterations in detail, then summarize the invariant or stopping condition. Do not hallucinate large traces.

5. **Audit the simulation**
   - Check whether any step falsely claimed real execution.
   - Check whether any state update skipped a rule or depended on a hidden assumption.
   - Check whether the target over-promises reliability where real execution, tests, or empirical data are required.
   - Check whether the boundary between deterministic logic (scripts) and judgmental logic (natural language) is drawn correctly — flag deterministic logic still expressed in natural language (a candidate for extraction into a script), and judgmental logic wrongly hard-coded into a script (should stay natural language).
   - Revise the trace if the audit finds inconsistencies.

6. **Report verdict and patches**
   - Provide a concise verdict: `Likely works`, `Works with caveats`, `Ambiguous`, or `Likely fails`.
   - Summarize expected behavior, failure modes, and validation gaps.
   - Recommend minimal prompt or Skill changes using precise instruction text.

## Output Template

Emit the full report skeleton from [`./references/prompt-templates.md`](./references/prompt-templates.md#simulation-report-output-template) — six mandatory sections: Simulation Scope, Initial State / Rules / Assumptions, Mental Trace (table), Edge Cases, Self-Audit, Verdict. Every heading is required; Self-Audit and Verdict are what make the simulation auditable rather than a guess.

## Resources

- Prompt fragments, reusable templates, and the report output template: `./references/prompt-templates.md`

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

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:think-skills" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
