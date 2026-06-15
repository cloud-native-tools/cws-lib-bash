# Thought Experiment Prompt Templates

Use these templates only as prompt fragments. They are designed for mental simulation, not real execution.

## Mental Dry Run for a Prompt or Skill

```text
Act as a strict mental simulator for the following Skill or prompt. Do not execute tools, code, shell commands, network calls, file writes, or external actions unless I explicitly ask for real execution later.

Target:
[Paste the Skill, prompt, or workflow]

Scenario:
[Describe the user request, inputs, environment, and constraints]

Simulation contract:
1. List the initial state, known rules, assumptions, and unknowns.
2. Process the target step by step.
3. For every step, output: Step, Trigger/Instruction, Mental Action, State Delta, Consistency Check, Risk/Uncertainty.
4. If a step would require a real side effect, mark it as "would execute" and simulate only the expected logical consequence.
5. Stop if rules conflict or required information is missing.
6. End with verdict, likely output, failure modes, and patch recommendations.
```

## State Machine Simulation

```text
Treat the target workflow as a closed state machine.

Initial State:
[State object]

Rules:
[Allowed transitions and constraints]

Events:
[Sequence of user/tool/system events to simulate]

For each event, update and print the State Object, cite the rule applied, and run a consistency check. Do not use real tools or external knowledge beyond the provided rules.
```

## Devil's Advocate Verification

```text
Stress-test this Skill or prompt without executing it.

Target goal:
[Goal]

Target rules:
[Rules]

Create three edge-case scenarios:
1. Happy path with minimal ambiguity
2. Missing/conflicting input
3. Tool/action failure or forbidden side effect

For each scenario, mentally simulate the target step by step, track state changes, identify where it succeeds or fails, and propose minimal prompt/Skill patches.
```

## Self-Audit Footer

```text
Self-audit your simulation:
- Did any step claim real execution?
- Did any state change skip a rule?
- Did any conclusion rely on hidden assumptions?
- Which result still requires real execution, tests, or tool calls to confirm?
Revise the trace if needed.
```
