# Documentation Target Structure

This file records the project-specific layer above the static documentation baseline. The baseline remains authoritative at `.specify/skills/create-docs/SKILL.md` § Desired-State Baseline.

Content outside the managed block is reserved for human notes and must remain byte-for-byte unchanged when the managed block is refreshed.

<!-- DOCS_TARGET_STRUCTURE_START -->

## 项目形态

[PROJECT_SHAPE]

## 目标读者

[TARGET_READERS]

## 静态基线引用

`.specify/skills/create-docs/SKILL.md` § Desired-State Baseline

## 项目专属扩展

| Path | Purpose | Evidence |
|------|---------|----------|
| [PROJECT_PATH_OR_NONE] | [PROJECT_SPECIFIC_PURPOSE] | [REPOSITORY_EVIDENCE] |

## 内容盘点摘要

| Topic cluster | Intended home | Evidence |
|---------------|---------------|----------|
| [TOPIC_CLUSTER] | [TARGET_LOCATION] | [SOURCE_PATHS] |

## 固定检索入口

| Consumer | Entry point | Refresh method |
|----------|-------------|----------------|
| Human | [HUMAN_INDEX_ENTRY] | Update the canonical index in the same reconcile run |
| Agent | `.specify/instructions.md` § Documentation Map | Run `/speckit.instructions` when canonical documentation locations change |

## 最后确认

- Date: [CONFIRMED_DATE]
- Basis: [CONFIRMATION_BASIS]

<!-- DOCS_TARGET_STRUCTURE_END -->
