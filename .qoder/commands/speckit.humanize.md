---
description: 跑一条指令并给人读五节报告；或按 --file/--inline 改写内容，事实逐字保全
---
<!-- AUTO-GENERATED from templates/commands/humanize.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> **Concurrency obligation（执行义务，按指针抵达）**: this command is an execution body — consider concurrency first, default to it when the class and capability allow, and, when serial, name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This template restates none of their rules.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat it as call parameters plus the text to run — not as a workflow that replaces this entry.

## Breaking Change（破坏性变更，入口必读）

- **裸文本 = 待执行指令**。`/speckit.humanize 把这段纪要整理成三条要点` 会**执行**这段文本，不会改写它。
- **改写既有文本 MUST 使用 `--file` 或 `--inline`**。内容源与非空指令同时出现会被拒绝，并在消息里点名两者。
- **迁移示例**（可直接复制；旧写法不再表示改写）：

  ```text
  旧： /speckit.humanize 把这段纪要整理成三条要点
  新： /speckit.humanize --inline 把这段纪要整理成三条要点
  文件：/speckit.humanize --file notes/meeting.md
  ```

调用语法与拒收分支的权威是 062 FR-018 与技能 `references/run-mode.md` § Parse：选项集只有 `--tone`、`--audience`、`--file`、`--inline`、`--output`、`--force`，只出现在指令之前；`--` 终止选项解析，其后全部逐字进入指令。本模板不复述判定表。

## Glossary

Consult the project glossary (`.specify/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

`/speckit.humanize` 有两个分支：**运行模式（缺省）**把选项之后的文本当作待执行指令，派发恰好一个会话级临时执行体跑完，再由主会话写出一份五节人读报告；**内容模式（显式 `--file` / `--inline`）**保留既有改写入口。分支边界、运行模式细则与报告形态以技能为单一事实源，本模板引用而不复述。

### 门禁归口（本模板只声明，不执行）

- 类别（判据、两个取值与逐流程台账）的唯一所有者：`.specify/shared/definitions/flow-class-definitions.md`；本命令不读取类别，也不调用任何脚本。
- 文档型门禁算子集的唯一所有者：`.specify/shared/workflow/expression-gates.md`；本命令不执行算子。
- 类别读取与最小算子集的执行，由委派技能在其 Stage 6「交付前保真自检」内承担（同一次运行只读一次）；本模板不复述判据、算子表或调用点表。

### 委派（强制）

**Delegation (mandatory)**: load `.specify/skills/humanize-conclusion/SKILL.md` and execute the branch its mode routing selects. 两模式的行为细则、派发载荷与回传信封、报告五节、语言与保真、注入防护，全部以该技能（含 `references/`）为单一事实源；本模板不复述其 Stage 表、字段表或小节标题。

### 本命令只做三件事

- 转发 `$ARGUMENTS` 原文与显式选项，不猜测意图、不预解析内容。
- 前置 Glossary 读取（见上）。
- 把技能的结果交给调用方：运行模式是会话内报告（显式 `--output` 时另给写入位置回执）；内容模式是改写文本（缺省会话内返回）。

## Handoffs

**Before**: none — the command is self-contained; the instruction arrives in `$ARGUMENTS`, content via `--file` / `--inline`.

**After**: the report or rewritten text is returned in-session (or written to the `--output` path and reported). The caller decides where it goes next; no downstream `/speckit.*` command consumes this output.