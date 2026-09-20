---
description: 框架资料卫生治理：检测过期残留并按两级判据清理
---
<!-- AUTO-GENERATED from templates/commands/sanitize.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions. 可选参数:`--roots <csv>`(限定资料根子集,部分扫描不自动收敛)、`check`(仅检查,不进入清理提示)。

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

本命令是框架资料卫生能力的执行入口,引擎为 `.specify/scripts/python/sanitize-utils.py`(发现 schema/合并语义/门控判据以引擎输出与 `--help` 为准)。执行流七个阶段:

### Stage 1 — Preflight

探测 `python3` 与引擎脚本 `.specify/scripts/python/sanitize-utils.py` 是否可用;缺失则给出 actionable 提示(引擎三态探测惯例)后停止。非 git 环境照常运行——语义过期检测自动降级(引擎输出 note)。

### Stage 2 — Collect

```bash
python3 .specify/scripts/python/sanitize-utils.py --action collect --workspace-root . --format json
```

确定性检查(死引用/索引一致/符号链接/镜像漂移)由引擎直接判定并入账;同时输出语义候选(时间性声明材料 + 证据包)。向用户呈现台账摘要(计数与 pending 目标列表,摘要优先,不贴原始证据全文)。

### Stage 3 — Judge

对 collect 输出的 semanticCandidates 逐条作过期/冗余判定。**判定依据限于候选携带的 evidencePack**(gitLog 摘要行 + pathExistence 映射)与 claims 短语——不整读材料原文(升级阶梯例外才定向节选)。判定规则:

- 声明("未落地/待办")与 gitLog 证据矛盾(合入提交晚于声明日期且触碰所引路径)→ `stale-residue`;
- 声明内容已完整并入其他存活材料 → `redundant`;
- 证据不足以裁决 → **证据不足,不判定**(计入运行摘要即可,绝不臆造)。

把判定写入临时文件后经引擎入账:

```bash
python3 .specify/scripts/python/sanitize-utils.py --action record --file <verdicts.json> --workspace-root . --format json
```

verdicts 文件 schema:`{"findings": [...]}`,finding 字段与契约 sanitize-findings.md 一致(稳定 ID = sha1(category|target)[:12],evidenceRefs 必须引用具体 commit 哈希/路径)。

### Stage 4 — Present

呈现发现报告:逐条列出分类/严重度/证据引用/处置建议(含可逆性标注)。**移交分诊**(delegate 项不执行,只建议):

- docs 内容编纂与结构收敛 → `/speckit.docs`;
- 符号链接/说明文件再生成 → `/speckit.instructions`;
- 镜像漂移收敛 → `sync-mirrors.py --write` / `regen-command-copies.py`;
- SDD 过程质量 → `/speckit.review`。

台账摘要可随时复查:

```bash
python3 .specify/scripts/python/sanitize-utils.py --action status --workspace-root . --format json
```

### Stage 5 — Confirm(破坏性前置确认)

将 destructive 项(delete/archive)归并为一份清理计划写入 `.specify/memory/sanitize/cleanup-plan.json`(`confirmed: false`),**单次批量**向用户呈现。删除与移动/归档属破坏性桶,等待用户确认后才执行(引擎对 `confirmed != true` 的 apply 一律退出码 2 拒绝,零执行)。

> Gate probe: gate-sanitize-destructive-cleanup — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

### Stage 6 — Apply

用户放行后:先完成可逆修复(repair 项的内容修改,agent 直接编辑材料),将计划 `confirmed` 置 `true`,再执行:

```bash
python3 .specify/scripts/python/sanitize-utils.py --action apply --plan .specify/memory/sanitize/cleanup-plan.json --workspace-root . --format json
```

引擎机械执行 delete/archive(归档落 `.specify/archive/` 保留相对布局)与状态更新(pending→resolved)。执行后向用户呈现三要素执行报告:执行内容、变更工件(逐项可定位)、修改途径(git 历史可恢复删除项/归档新位置)。用户否决 → 仅保留 pending 发现并如实报告,零删除零移动。执行中途失败如实报告失败点、原因与已产生的中间产物,不静默跳过。

### Stage 7 — Wrap-up

标准 Feedback 与 Documentation 收尾步骤(见下)。门控触发且用户作出决定后,按门控观察协议记录观察事实(非阻塞):

```bash
python3 .specify/scripts/python/feedback-utils.py --action record \
  --unit-id "/speckit.sanitize" --unit-type command \
  --lifecycle-point "gate-sanitize-destructive-cleanup" --run-id "gate:gate-sanitize-destructive-cleanup:<UTC ts>" \
  --review "<观察事实,正文 MUST 含字面标记 confirm-gate>" --points-file "<要点文件>"
```

## Behavior Rules

- **范围红线**:不评估、不修改、不报告用户源代码、产品脚本与测试用例;发现目标限于框架自有资料(引用存在性检查只判定目标存在与否,不构成对用户代码的评估)。
- **检查零修改**:Collect/Judge 阶段不修改任何被检材料本体;写入仅落台账与计划文件。
- **确认红线**:任何删除与移动绝不发生在用户确认清理计划之前。
- **证据红线**:语义判定的 evidenceRefs 必须引用具体 commit 哈希/路径;证据不足候选不判定、不入账。
- 触发方式仅手动按需;`check` 参数止于 Present,不进入 Confirm。
- 台账累积语义:重复运行新发现并入、未处置发现保留状态、外部修复后未检出自动收敛(resolved)。

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether this run produced information needing entry into the documentation space, and conclude with exactly one of `需记录(目标文档 + 要点)` or `无需记录`. Never block wrap-up; incremental judgment only.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.sanitize" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Handoffs

**Before**: 无前置(手动按需运行)。

**After**: delegate 项按分诊建议移交 `/speckit.docs` / `/speckit.instructions` / sync-mirrors;台账 pending 项可留待下次运行收敛。