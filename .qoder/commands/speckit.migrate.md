---
description: 一次性迁移收尾：干跑计划、同意后 apply 归档式收敛
---
<!-- AUTO-GENERATED from templates/commands/migrate.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> **Concurrency obligation（执行义务，按指针抵达）**: this command is an execution body — consider concurrency first, default to it when the class and capability allow, and, when serial, name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This template restates none of their rules.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions. 可选参数：`--workspace <path>`（目标工作区根，缺省当前目录；必须已含 `.specify/`）、`--format text|json`（干跑输出格式，缺省 `text`）。

## Glossary

Consult the project glossary (`.specify/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Delegation

`/speckit.migrate` 是薄投影：探测、计划与处置全部由已安装 CLI 的 `specify migrate` 子命令完成；模板不实现任何检查、残留清单、路径改写或处置判断，也不自带第二份计划。命令把新旧混杂的工作区收敛到当前安装版本的期望态，逐项给出「当前态 → 期望态 + 拟处置 + 依据路径」。

1. **Dry-run first.** 运行 `specify migrate`（人读计划）或 `specify migrate --format json`（机器可读包络；模板原样转述，不解析键集），并逐项向用户转述计划：

```bash
specify migrate --format json
```

2. **Apply automatically.** `--apply` 是本命令唯一的写入授权；每个破坏性步骤都是 archive-first，原件先复制进 `.specify/archive/migrate/<run-id>/`，回执逐项记录 `recover` 路径，因此这些动作按可逆处理并自动执行，不再要求第二次确认，也不新增确认旗标。干跑之后直接运行：

```bash
specify migrate --apply --format json
```

   非交互会话与交互终端行为一致：可逆项自动执行；只有真正无法合并的结构性冲突（如兼容链接位置被非空目录占用、宿主不支持符号链接）与执行期 I/O 失败会留在 `blocked`，其余项照常完成。

3. **Disclose merges.** anchor-layout 维度的旧新同位置文件由引擎合并：占位 stub 被真实内容替换；双方都是真实内容时，`features.md` 按特性 ID 做表行并集（目标侧同名行优先），其余锚点保留目标全文并以固定标记追加旧内容；两个原件都已归档。逐项报告被合并的锚点、归档位置，并建议用对应 owner 命令复核（`/speckit.constitution`、`/speckit.feature`）。合并结果本身可由回执恢复。

4. **Report the outcome verbatim.** 结局与退出码是稳定契约，原样转述：

| outcome | exit | 语义 |
|---------|------|------|
| `clean` | 0 | 计划为空（干跑或 apply 均可） |
| `planned` | 1 | 干跑且存在差异项 |
| `applied` | 0 | apply 完成，且无 refused / blocked / failed 项 |
| `blocked` | 3 | apply 后仍存在 refused / blocked / failed 项 |

   输入或前置条件错误以 stderr 报文 + 退出 2 收束（`error` 不是 outcome token）；工作区缺少 `.specify/` 时，修复入口是 `specify init`。

5. **Point at the records.** apply 后报告回执 `.specify/memory/migrate/receipts/<run-id>.json` 与归档根 `.specify/archive/migrate/<run-id>/`；恢复途径以回执的 `recover` 字段为准。

**Boundary**: neither install nor init — 本命令是 `specify install` + `specify init` 之后的一次性收尾；`/speckit.sanitize` 保留为周期复检 lane；goal/team 定义的档案迁移仍归 `/speckit.goal` 的 `migrate-archive`。

## Handoffs

**Before**: `specify install` + `specify init` 已完成，工作区已含 `.specify/`。

**After**: 回执中 blocked / failed 项逐项审阅后重跑 `/speckit.migrate`；合并过的 anchor 交对应 owner 命令复核；周期复检交 `/speckit.sanitize`；工作区刷新与兼容链接修复交 `specify init` / `/speckit.instructions`。