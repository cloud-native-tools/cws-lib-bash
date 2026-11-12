# Mechanism / policy check — how to locate a misplacement

The criteria are owned by `.specify/shared/definitions/mechanism-policy-definitions.md`: the boundary test
(§ Terminology), the two sides (§ Boundary Test), the symptoms (§ Misplacement Symptoms) and the
corrections. This file only says **where to look** and **how to read a hit**. It is not a second
owner and it adds no rule.

## Locate

1. Enumerate the lines you added or the body lines the user's draft touched — a check over the
   whole body is a survey, not this check; keep it to the lines this creation produced.
2. Policy side: search those lines for an absolute path, a user or machine directory name, a
   corpus path, or "default output to …" — any of these is the environment being frozen into the
   skill.
3. Mechanism side: read the run-environment notes the creation consumed (the user's brief, a
   dated execution notes doc, repository scratch notes) and look for a rule, a step order or a
   branch written there instead of in the skill's own files.
4. Read back each hit as a quotation (file + line, or the sentence verbatim). A hit you cannot
   quote is a suspicion, not a finding — do not report it.

## Correct

- Policy written into the mechanism: move the value to the run-environment side — take it as a
  parameter the caller or the environment supplies, and when it is absent ask (§ Consumption
  Contract of the owner), never inherit the value already in the text.
- Mechanism left in the run-environment side: move the rule, step order or branch into the skill
  assets — the body, `references/` or `.specify/scripts/` — and leave the run-environment note carrying
  only which input this run uses.
