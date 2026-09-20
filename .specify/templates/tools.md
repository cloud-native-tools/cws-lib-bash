# Tools System Guide

> **Note**: This file is shipped by Spec Kit and created by `/speckit.instructions` only when absent — your local edits are preserved. It is an explanation document, **not** a registry: nothing here needs to be updated when tools are added or removed.

## What a Tool is

A **Tool** (unqualified, in the tools domain) is a pre-verified reusable capability record at `.specify/memory/tools/<name>.md`, ID form `<TOOL:...>`, owned by `/speckit.tools`. Its authoritative RFC 2119 behavioral rules outrank the agent's built-in knowledge, and its environment applicability (verified version / version differences / platform / architecture / fallback / preflight) tells you the form that actually holds in this environment.

Do not confuse it with an **AI agent CLI** (Claude Code, Codex CLI, Qoder CLI, …) or with the `tools:` frontmatter key of an agent (the LLM's callable surface).

## Source of truth — no registration table

- **Definition records**: `.specify/memory/tools/<name>.md` — one file per tool; the single authoritative source. A tool exists iff its record file exists.
- **Discovery inventories**: `.specify/tools/{system,shell,project}.json` — machine-generated (system binaries, shell functions, project scripts); never hand-edit them. Regeneration path and the unrelated `.specify/memory/tools.md` MCP index: `.specify/shared/definitions/tool-definitions.md`.
- Spec Kit maintains **no tool registry** in `instructions.md`; completeness is guaranteed by the filesystem (records + regenerated inventory), not by table rows.

## Lifecycle

- **Define / create**: the `create-tools` skill (definition-first: mandatory fields come from the user; discovery only bootstraps a Draft).
- **Improve / promote**: the `improve-tools` skill (source/contract correction, rule hardening, alias/rename, Draft → Verified).
- **Reuse gate**: before writing script code for a complex or repeatable action, look for an existing Tool under `.specify/memory/tools/` and reuse it — see `.specify/shared/workflow/tool-reuse-gate.md` (Constitution Principle XII). No Tool for the capability? Writing the code is the expected outcome.
