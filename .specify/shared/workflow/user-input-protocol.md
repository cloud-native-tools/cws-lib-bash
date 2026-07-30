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

## Empty Arguments Handling

- If `$ARGUMENTS` is empty, the command should use its default behavior (defined per-command).
- Commands that require arguments MUST report an error when `$ARGUMENTS` is empty.

## Shell Quoting

For single quotes in args like "I'm Groot", use escape syntax: e.g `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).
