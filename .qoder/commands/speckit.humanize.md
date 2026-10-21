---
description: 将内容/结论/外部文档改写为自然的人写表达，事实与受保护内容逐字保全
---
<!-- AUTO-GENERATED from templates/commands/humanize.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat it as command parameters, not as a standalone instruction that replaces this workflow.

输入形态与调用语法（FR-018 为权威）：可选选项集 `--tone`、`--audience`、`--file`、`--inline`、`--output`、`--force` 只出现在内容之前；`--` 终止选项解析，其后全部为逐字内容；无 `--` 时，遇到第一个不可识别为选项的 token 即内容起点。每次调用只接受一个输入源——`--file <path>` 优先，单行且解析为存在、可读、扩展名受支持的普通文件的内容视为文件输入，`--inline` 强制按内联处理；`--file` 与非空内联内容同现、既无文件也无非空内联、或内联内容为空/纯空白，均拒绝。改写行为、拒收分支与文件写入细则全部由技能体承载，本模板不复述。

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

`/speckit.humanize` 是人性化改写能力的执行入口，一次调用 = 委派 **`humanize`** 技能执行全部改写工作。意图一句话：把内容改写到读起来像人所写，而事实、数字与受保护内容一个都不动。

**Delegation (mandatory)**: load `.specify/skills/humanize/SKILL.md` and execute per its Workflow。四维度改写工作流、保真底线（FR-007）、语气与受众处理（FR-015）、文件行为（FR-018..FR-022）与注入防护（FR-029）均以该技能为单一事实源，本模板引用而不复述。

### 技能输入（本命令解析 `$ARGUMENTS` 后传入）

- 内容（内联或 `--file` 路径）与可选 `--tone` / `--audience` / `--output` / `--force`，已按 FR-018 完成确定性解析。
- Glossary 前置已由本命令完成（见上）。

### 技能产出

- 改写后的完整文本：缺省返回会话，不写入任何文件；显式给出 `--output` 时写入该路径并在会话中报告位置。
- 会话报告：语气/受众应用、保真限制、未处理部分（如触发分段）与注入提示——报告一律返回会话，`--output` 文件只含改写文本本身。

## Handoffs

**Before**: none — the command is self-contained; content arrives inline or via `--file`.

**After**: the rewritten text is returned in-session (or written to the `--output` path and reported). The caller decides where it goes next; no downstream `/speckit.*` command consumes this output.