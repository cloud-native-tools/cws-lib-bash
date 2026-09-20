# User Input Protocol

This document defines the standard processing rules for `$ARGUMENTS` across all `/speckit.*` commands.

## Standard Rules

Every command receives user input via the `$ARGUMENTS` placeholder. When processing this input:

1. You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement missing context and guide the command workflow.

2. The user input may include:
   - Special requests that require extra care or custom handling during the workflow.
   - Supplemental information that provides additional context or reference material.
   - Additional tasks or focus areas that go beyond the default scope described in the command.

3. When processing the user input:
   - You **MUST** treat `$ARGUMENTS` as parameters for the current command.
   - Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
   - If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

## Mid-Run Addendum Input

Input that arrives **after** the command has already started — a new directive, a correction, or added scope supplied between steps — is an **addendum** to the running command, not a new invocation:

1. Process it under the Standard Rules above: parameters for the current command, never a standalone instruction that replaces the workflow.
2. **Batch, do not interleave**: when several addenda arrive across one run, integrate them together at the next artifact-write point. Never alternate partial artifact edits with new-input intake — the batch is integrated once, and any validation gate it triggers is re-run once.
3. **Upstream artifact first**: an addendum that changes requirement scope MUST land in the upstream artifact it belongs to, and that artifact's validation gate MUST be re-run, before downstream work continues. Downstream artifacts built against a stale upstream are untrustworthy by construction.
4. **Record verbatim**: each addendum is recorded append-only under the artifact's `## Clarifications` > `### Session YYYY-MM-DD` heading, so the run stays auditable.

Per-command steps name *which* artifact an addendum lands in and what restructuring it needs; the batching, ordering, and recording rules are owned here.

## Empty Arguments Handling

- If `$ARGUMENTS` is empty, the command should use its default behavior (defined per-command).
- Commands that require arguments MUST report an error when `$ARGUMENTS` is empty.

## Shell Quoting

For single quotes in args like "I'm Groot", use escape syntax: e.g `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).
