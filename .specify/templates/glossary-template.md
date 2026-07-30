# Project Glossary (项目词汇表)

> **Note**: This file is initialized by `/speckit.instructions` and lives beside `constitution.md` / `features.md`. It is the project's single, project-wide vocabulary anchor: it corrects voice/dictated input (homophones, easily-confused words) and doubles as a lightweight domain-knowledge dictionary. It is loaded as ambient context by every `/speckit.*` command via the Documentation Map. See `.specify/shared/workflow/glossary.md` for the correction / enrichment / conflict protocol.

## Authoring Rules

- **Common words are NOT recorded** — only project-specific / domain terms that carry special meaning here.
- **User edits are authoritative (以用户输入为准)** — manual entries win over automatic proposals and are preserved across regenerations; automatic proposals MUST NOT silently overwrite a `user` entry.
- **Conflicts require confirmation** — a new term that collides with an existing entry (same term/different meaning, or a homophone/near-duplicate) is written only after the user confirms the resolution.

## Column Definitions

| Column | Meaning |
|--------|---------|
| Canonical | The agreed project term (unique, case-insensitive). |
| Variants | Comma-separated homophones / easily-confused / dictation-error forms that anchor back to Canonical; `-` when none. |
| Meaning | Brief one-line domain definition. |
| Origin | `auto` (framework-proposed) or `user` (manually authored/confirmed). |
| Status | `proposed` (awaiting confirmation) or `confirmed`. |

## Glossary

| Canonical | Variants | Meaning | Origin | Status |
|-----------|----------|---------|--------|--------|
| None yet. | - | - | - | - |
