# Constraint Placement & Compliance

Diagnose and fix runs where the target Skill **was invoked and its workflow was followed, but hard constraints were ignored** — format rules skipped, conditional musts not applied, forbidden wording used. This failure mode is usually a *placement* problem in the Skill document, not a wording problem.

## Evidence basis

A 150-run controlled experiment (2 temperatures × 5 injection strategies × 3 trigger cases, ~200-line production-shaped Skill with 8 hard constraints, rule-based auto-evaluation; internal article “一种很新的SKILL用法”, 2026-07) measured constraint-compliance rates:

| Strategy | What it does | Avg compliance |
|----------|--------------|----------------|
| Constraints re-stated at end of user message | Extract `## Constraints` text, append at the position closest to generation | **99.5%** |
| Double injection (system + user) | Same text in both places | 97.9% |
| Constraints appended to system prompt | Far from generation | 87.9% |
| Generic reminder (“strictly follow the Constraints”) | Pointer without content | 77.4% |
| Baseline | Constraints only mid-document inside the loaded Skill body | 75.8% |

Three transferable findings:

1. **Position dominates.** Constraints diluted mid-document (~5% of a long body) sit in the attention low-zone (“Lost in the Middle”, Liu et al. 2023). Moving the *concrete text* close to the generation point took the hardest constraint from 20% to 100% compliance.
2. **Generic reminders are a measured no-op.** “Strictly follow the Constraints above” scored ≈ baseline overall and **0%** on the hardest constraint — worse than doing nothing, because the model does not “look back” at a far-away block on cue. Never accept this as a fix.
3. **Repetition does not help and can hurt.** Duplicating the block in two places slightly *reduced* compliance (attention dilution), and negatively phrased rules injected early (“do not recommend X”) primed the model *toward* X in edge cases (the prohibited option’s compliance dropped below baseline).

A fourth, scoping finding: **gains concentrate on high-difficulty constraints** — conditional musts (“if user has no tests, step 1 MUST be adding tests”) and linked format bundles (three mandatory sections that pass or fail together). Simple lexical/formatting rules are position-immune (~100% everywhere), so measuring a placement fix against them yields no signal.

## When to suspect placement

- The Skill was invoked, steps were executed, output shape is roughly right — but one or more hard rules were violated.
- The same rule **is obeyed when the user restates it in chat** during the run. This is the strongest placement signal: the rule text works when close to generation, fails when buried.
- Violations cluster on conditional or multi-part format constraints while trivial rules pass.
- The Skill body is long and the constraints live mid-document, scattered, or embedded inside step prose.

## Fix ladder (apply in order, minimally)

1. **Consolidate hard constraints into one compact, clearly delimited block** (its own heading, table or short list, objective wording), positioned **late in `SKILL.md`** — after the workflow, where it lands closest to generation when the body is loaded. Do not scatter musts across step prose.
2. **Restate the concrete constraint text inline at the exact decision-point step.** When one step repeatedly violates one rule, put that rule’s full text in that step — not a pointer (“see Constraints”), which is the measured no-op.
3. **De-duplicate.** One constraint block is the source of truth; remove copies in other sections. More copies ≠ more compliance.
4. **Pair every prohibition with the required alternative.** “Do not use vague durations — give a specific week count” instead of a bare “no vague wording”, to avoid negation-priming toward the banned behavior.
5. **Make completion conditions objective.** Replace subjective adverbs (“carefully”, “thoroughly”) with checkable outputs: named sections present, a table used, a count given, a command exit code. Objective conditions are what a rule-based validation or the next improvement loop can actually verify.

## Verifying the fix

- Re-run (or trace) against the case that previously violated the rule; expect the **previously failing high-difficulty constraints** to pass. Do not claim success from position-immune easy rules.
- A correct fix typically also produces *more compact* output — in the experiment, higher compliance correlated with fewer completion tokens (the model stops padding when the required shape is unambiguous).
- Record the before/after in the intervention ledger as usual; “compliance improved on constraint R-n” is the expected signal.

## Relation to slimming (L0–L3 progressive disclosure)

Placement fixes and slimming reinforce each other. The Skill loading model is progressive: **L0** frontmatter `description` (always in context, ~100–300 chars), **L1** `SKILL.md` body (loaded on trigger; keep ≤ ~5K tokens), **L2** `references/` (read on demand), **L3** `scripts/` (executed, near-zero token cost). Every non-contract paragraph left in L1 dilutes the constraints that must survive there — moving manual content to L2/L3 is not just readability hygiene, it measurably protects hard-rule compliance. See [skill-slimming-principles.md](./skill-slimming-principles.md).
