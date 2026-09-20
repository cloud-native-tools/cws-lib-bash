# Red-Line Framework (attribute-triggered mandatory constraints)

This file owns the **red-line framework**: a proactive conformance gate that runs while
improving a Skill. Unlike evidence-gated optimization (fix what a run observed breaking), a
red line is a **design invariant** — its violation is a defect by definition, whether or not
any execution crashed. The executable half is `${SKILL_HOME}/scripts/redline-check.py`; this
file owns the methodology, the registry catalogue, and the admission rigor.

## Why this exists

The improvement loop was purely reactive: it optimized from observed execution evidence and
user direction. That misses invariants whose breach produces no error — a browser-automation
Skill that steals system focus "works" (the run completes) while silently disrupting the
user's real work. Such invariants must be checked **proactively, keyed on what the Skill is**,
and remediated **mandatorily**, not recommended.

## The generic 4-step flow

```
1. attribute collection   classify the target Skill from its own text/scripts
                          (automation? sensitive-info? … — extensible)
2. red-line selection     map each present attribute to the red lines it fires
                          (attribute present ≠ red line fires; only bound red lines run)
3. trigger judgment       evaluate compliance -> PASS (not-applicable / compliant)
                          or TRIGGERED (gap / review)
4. remediation            TRIGGERED => MUST fix (or prove each signal a sanctioned,
                          announced exception). Red-line remediation is never optional.
```

Steps 1–3 are deterministic and run in `redline-check.py`. Step 4 is judgment + MUST-DO and
stays with the improver. Run it in **workflow step 4** (before acting) and re-run it in
**step 8** (must exit `0` before finishing).

```bash
python3 ${SKILL_HOME}/scripts/redline-check.py <target/SKILL.md>          # gate: exit 0 pass / 1 triggered
python3 ${SKILL_HOME}/scripts/redline-check.py <target/SKILL.md> --json    # machine verdict + evidence
python3 ${SKILL_HOME}/scripts/redline-check.py <target/SKILL.md> --scan-all # deeper audit incl. references/
```

## What the probe decides vs what stays judgment

| Deterministic (the probe) | Judgment (the improver) |
|---------------------------|-------------------------|
| which attributes are present | whether a flagged signal is a *sanctioned, announced exception* (e.g. a human-in-the-loop SSO login window) or a real violation |
| which red lines therefore apply | the concrete remediation edit that satisfies the invariant |
| where violation / compliance signals appear (file:line) | whether a `review` verdict's hard signals are all legitimately documented |

The probe never auto-convicts: a `review` verdict means "remediate **unless** you can point at
why each signal is sanctioned". This division follows the skill's own principle — deterministic
logic to code, judgment to the LLM.

### Verdict model (exit code driven by *mitigation presence*, not raw signal count)

| Verdict | Condition | Meaning |
|---------|-----------|---------|
| `not-applicable` | trigger attribute absent | red line does not fire → PASS |
| `gap` | attribute present, **zero** focus-safe vocabulary | drives automation with no mitigation → MANDATORY remediation |
| `review` | attribute present, mitigation present, un-negated **hard** signal remains | verify each is sanctioned, else fix → MANDATORY |
| `compliant` | attribute present, mitigation present, no un-negated hard signal | PASS |

Why mitigation-presence and not signal-count: a reference implementation documents the
*banned* mechanisms (in "rejected" tables, API listings, `never call X` prohibitions). Counting
raw greps would flag the most-compliant skills — the calibration trap `skill-shape.py` warns
about. So the probe (a) excludes `references/` from the default gate scope, (b) applies a ±2-line
**negation guard** (a wrapped `never call\n bringToFront()` is a prohibition, not a violation),
(c) splits **hard** signals (always worth judgment) from **soft** context signals (only matter
when no mitigation exists), and (d) skips its own framework files. `--scan-all` opts into the
deeper, knowingly-noisier reference audit.

## Red-line catalogue

The executable registry (detection patterns, compliance markers, remediation text) lives in
`redline-check.py` `RED_LINES` — that is the SSOT for *detection*. This table is the
human-facing index; keep ids in sync.

| id | trigger attribute | invariant (absolute) | mandatory remediation |
|----|-------------------|----------------------|-----------------------|
| `RL-FOCUS-01` | `automation` (drives a GUI/browser/desktop surface that maps real windows) | No automation method may steal the user's system focus or pop a window/tab in front of their work. | Route every launch/attach through a focus-safe path: background `open -g` (macOS) or headless / virtual display; attach to a running instance instead of relaunching; reuse background tabs; never `bringToFront()`; any genuinely-headed window is announced, small and fixed. Foreground/direct-binary launch only as an announced human-in-the-loop exception, gated + documented. See browser-utils `focus-safe-launch.md`, profiles-browsers SKILL.md § 焦点红线. |

Collected attributes with **no** red line bound yet (framework is extensible; binding one
requires passing admission below): `sensitive-info` (handles credentials/tokens/cookies/PII).

## Admission criteria — what qualifies as a red line (rigor gate)

The remediation for a red line is **MUST**, so the bar for calling something a red line is high.
A candidate qualifies **only if all** hold — otherwise it is a normal constraint (recommended,
evidence-gated), and MUST NOT be added to `RED_LINES`:

1. **Protects an irreversible or user-harming invariant** — data loss, security/credential
   breach, destructive/irreversible action, or disruption of the user's own work (focus theft).
   Not efficiency, structure, style, or a preference.
2. **Objectively detectable** — a static signal decides it (presence of a pattern / absence of
   required mitigation), not taste. If two competent reviewers would disagree on whether it was
   violated, it is not a red line.
3. **Has one required alternative** — remediation is a single unambiguous MUST-DO, not a menu of
   acceptable options. Pair the prohibition with the required alternative (avoids negation-priming).
4. **Universal within its trigger attribute** — it binds *every* Skill with the attribute, with
   at most narrow, nameable, announced exceptions (e.g. human-in-the-loop login). A rule with
   broad case-by-case discretion is a guideline, not a red line.
5. **Worth blocking a loop over** — breaching it must be severe enough that finishing the
   improvement without fixing it is unacceptable.

Anti-pattern: promoting a general best practice ("prefer headless", "announce long runs",
"keep scripts idempotent") to a red line. Those are constraints/recommendations; making them
`MUST` devalues the real red lines and trains people to ignore the gate.

## Reconciliation with "Evidence before defect" (Hard Constraint 5)

HC5 forbids labeling something a defect without an observed symptom. A red-line violation does
not contradict it: **the violating pattern's presence in the Skill's own instructions/scripts is
the observed symptom** (a static artifact), exactly like a runtime stack trace is evidence. The
probe surfaces that artifact; the improver still must not invent violations the probe did not
find. `not-applicable` and `compliant` verdicts are never defects.

## Extending the framework

To add a red line: (1) confirm the candidate passes **all** admission criteria above; (2) add its
trigger attribute signals to `ATTRIBUTES` (or reuse an existing attribute); (3) add a `RED_LINES`
entry — `id`, `attribute`, `invariant`, `violation` patterns tagged `hard`/`soft`, `compliance`
markers, `remediation` (the required alternative), `refs`; (4) add its row to the catalogue table
here; (5) validate per the reverse-case discipline — run the probe against a compliant Skill
(must NOT trigger) and a genuinely-violating sample (must trigger) before wiring it as a gate.
