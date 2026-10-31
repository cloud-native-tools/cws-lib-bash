# Maintenance Recipes — H1–H5 执行细则

> 本文件是 `sdd-house-keeping` 的操作手册。Bootstrap（install/refresh/constitution/首次 goal/agents/team）归 `sdd-project-setup`；本文件只覆盖 bootstrap 之后的周期性维护。命令形态全部参数化：`<project-dir>` `<alias>` `<run-user>` `<tool>`。
>
> **三段循环对照**：setup = S0–S2 + HANDOFF；house-keeping = H0–H5；loop-driver = U0–U6。
> 目标解析唯一契约：`.specify/shared/workflow/target-resolution.md`。

## H1 ASSESS — 双盘点

```bash
# 本地（未给远程三元组）：目标=当前项目
python3 ${SKILL_HOME}/scripts/mechanism-inventory.py --project <project-dir> --json
python3 ${SKILL_HOME}/scripts/logical-framework.py --project <project-dir> [--json] [--strict]

# 远端（host+run-user+project-dir 给全）：在目标侧以 run-user 执行
ssh <alias> "su - <run-user> -c 'cd <project-dir> && python3 - --project <project-dir>'" < ${SKILL_HOME}/scripts/mechanism-inventory.py
ssh <alias> "su - <run-user> -c 'cd <project-dir> && python3 - --project <project-dir> --json'" < ${SKILL_HOME}/scripts/logical-framework.py
```

- 物理矩阵：const / feat / gloss / fb / reg / kb / session / tools / skills / tmpl / specs / src / compat；分级 `absent | degraded | partial | complete`。
- 逻辑矩阵：required（instructions / features / docs）、recommended（goals / glossary / register / knowledge）、conditional（agents / teams）。
- 退出码：logical `0` required 全 ok；`1` required 缺口；`2` 非 Spec Kit 项目。`--strict` 把 recommended 缺口也计为失败。
- 两层都跑完才算 H1 完成；缺口凭据是**本次**结果。

## H2 RECONCILE — 固定次序、按缺口

| 次序 | 命令 | 触发条件 | 效果 |
|---|---|---|---|
| 1 | `/speckit.sanitize` | 材料陈旧残留；`cleanup` 模式下还有已消费记录 | materials lane 卫生治理；retention lane 消费→回执→回收 |
| 2 | `/speckit.feature` | `feat` 缺或注册表与实况漂移 | 注册表 reconcile（增量，不重建） |
| 3 | `/speckit.instructions` | compat 断、过期、partial/degraded、`BUDGET ... over` | 指令与兼容链接重建；预算收敛 |
| 4 | `/speckit.docs` | docs 树与代码/特性/指令漂移 | 委托 create-docs 收敛 |

- 执行 **H1 缺口 OR owner 自检报告的漂移**；每项登记 `executed / existing / skipped + reason`；未处理项进 H5 清单。H1 只回答“资产在不在”，不替代 sanitize/feature/instructions/docs 的漂移检查。
- **Carrier**：本地 H2/H3 由编排者/原生子代理在当前项目执行；远端每个 `/speckit.*` 在 `<project-dir>` 下经 run-agent 驱动——`ssh <alias>` → `su - <run-user>` → `cd <project-dir>`；CLI 缺省 qodercli（execution-config defaults，可覆盖）。
- constitution 缺失 → 停止并 handoff `sdd-project-setup`。
- **sanitize 调用契约**：
  - `check` 模式：同时跑 `/speckit.sanitize check`（materials）与 `/speckit.sanitize --lane retention check`；两份摘要一起报告，不删除。
  - `cleanup` 模式：跑 `/speckit.sanitize --lane all`；一个调用内呈现 materials 与 retention 两个计划，破坏性确认仍由 sanitize 既有门处理，**不新增第二道门**。
  - MUST NOT 直接调用 `sanitize-utils.py apply` 或 `record-retention.py apply`。
  - **能力探测**：缺 `record-retention.py`（旧框架）→ 只跑 materials lane，报告 `retention=not_evaluated — 需升级 spec-kit`，不删除；缺 `sanitize-utils.py` → 回交 setup 做刷新。
  - **命令面**：不假设 `/speckit.*` 副本存在；缺失时按 `.specify/skills/internal/<name>/SKILL.md` 直接加载 owner 技能。

### Budget convergence (R3 fallback)

`/speckit.instructions` 的 `BUDGET: <size> <budget> over` 是收敛触发，不是装饰性告警：

0. **模板注入分支**：若模板全量注入本身就会过界，走 pointer-first——只写短指针节，未内联章节按名字登记 pending。
1. **先走 owner 的 R1/R2**：`/speckit.instructions` 内置的模板章节压缩与 project-owned 大章节外迁；回到 `within` 即结束。
2. **R3 回退**：仅当 R1/R2 无合法候选、仍 `over` 时，按 section table 的 `live B` 降序选择 `placeholder=yes` 且 `delta>0` 的 project-filled 章节，机械迁移到 owner 文档，断言每条内容只出现一次，再把 instructions 中该章节替换为摘要 + 指针，并在 `## Documentation Map` 增加 owner 文档行；每次迁移一个章节，迁移后复测。
3. **仍超预算 = pending**：列出剩余最大章节与原因，给用户三项选择（上调预算 / 拆分章节 / 接受超预算）；不得静默完成或删除项目内容。
4. **幂等**：`within` 稳定态重复执行零写动作。

## H3 STRENGTHEN — 依赖次序、按需

| 次序 | 命令 | 触发条件 | 效果 |
|---|---|---|---|
| 1 | `/speckit.history` | `.specify/history/` 缺或落后于会话存量 | 增量蒸馏为主题知识库 |
| 2 | `/speckit.docs` | 有 history 新素材或文档待深化 | 吸收素材、深化文档 |
| 3 | `/speckit.research` | 调研结论缺失或过期 | 深度调研，结论落 spec 侧 |
| 4 | `/speckit.feature` | 注册表稀疏或调研揭示缺口 | 生成/补齐特性条目 |

- 依赖：history → docs；research → feature。不并行。
- `/speckit.goal`、`/speckit.agents`、`/speckit.team` 的首次定义归 setup；本 skill 只检查存在性。
- **Bootstrap-gap 回交**：若 H1 显示 goal/agents/team 缺失，MUST NOT 静默跳过——记录 `bootstrap-gap` 并回交 `sdd-project-setup`，除非用户明确要求本 skill 维护。首次定义仍归 setup。
- 强化产物进入 H5 候选清单；不推进任何 SDD 开发阶段。

## H4 VERIFY

1. 五族前置检查（本地拓扑只适用 ④ LLM 配置与 ⑤ framework 可用性；①–③ 记 `n/a`；远端五族全查）。权威表：`.specify/skills/internal/run-agent/references/dispatch-preflight.md`。
2. 物理矩阵复扫达 `complete`（或 partial 且缺口已声明）；逻辑矩阵 required 层无未声明缺口。
3. 兼容符号链接悬空扫描为空：
   ```bash
   find <project-dir> -maxdepth 2 -type l ! -exec test -e {} \; -print
   ```
4. Hook health：
   ```bash
   # 本地
   python3 ${SKILL_HOME}/scripts/hook-health.py --project <project-dir> [--fix] --json
   # 远端（目标侧以 run-user 执行）
   ssh <alias> "su - <run-user> -c 'cd <project-dir> && python3 - --project <project-dir> [--fix] --json'" < ${SKILL_HOME}/scripts/hook-health.py
   ```
   - `0` 干净/已修；`10` 未解决风险（进未处理清单）；`2` 参数错误。
   - `check` 模式只读，不带 `--fix`；`cleanup` 模式默认可带 `--fix`。
   - vendor-managed / 自愈 hook 只报告，不自动改。

## H5 REPORT

运行报告落宿主工作目录 `sdd-housekeeping-<project-slug>-<UTC-ts>.yaml`：

```yaml
target: {mode: local|remote, project_dir, alias, run_user}
mode: check|cleanup
inventory: {physical_before, logical_before, physical_after, logical_after}
actions:
  - {command: "/speckit.sanitize --lane retention", status: executed|existing|skipped, reason: ...}
sanitize_retention: {scanned, eligible, blocked, removed, remaining, ledger}
unprocessed: [...]
candidates: {features: [...], feedback: [...], todos: [...]}
suggestion: "候选工作；如需 SDD 全流程推进可调用 sdd-loop-driver（可选，非强制）"
```

- 候选来源：未完成 feature、大规模反馈改进、SPECKIT TODO。本 skill 是候选清单的唯一所有者；setup 不再产出 `sdd-candidates-*.yaml`。
- 候选清单是建议，不携带「必须调用 sdd-loop-driver」的语义。
- `check` 模式下 `removed` / `remaining` / `ledger` 允许为 null；`record-retention.py` 缺席时 `sanitize_retention.status = not_evaluated`，不得填 0 冒充。
- 不在目标项目创建 ad-hoc 目录；不借用 `.specify/state/`。

**就绪判据差异（有意）**：house-keeping H0 以 `.specify/` + constitution 为前置；`source.json` 缺失在 H1 记为 provenance warning，不阻断本 skill。loop-driver 的 preflight ⑤ 额外要求 `source.json`，因为它需要框架版本用于派发；两者差异在此声明，不在两处各自发挥。

## 幂等与重入

| 动作 | 稳定态重入行为 |
|---|---|
| 双盘点脚本 | 每次执行都跑；只读，输出不变 |
| `/speckit.sanitize` materials | 无残留则零动作 |
| `/speckit.sanitize --lane retention` | 无候选则零动作；有回执但未过宽限则只报告 |
| `/speckit.feature` | 增量 reconcile，不重建 |
| `/speckit.instructions` | 非破坏性 reconcile；预算 `within` 时零写 |
| `/speckit.docs` | 收敛核对，只处理新漂移 |
| `/speckit.history` | 增量，只处理新会话 |
| `/speckit.research` | 结论在位且未过期 → 跳过 |
| hook health | `check` 只读；`cleanup` 只修 fixable |

**稳定态快路径**：H1 全绿且 H3 触发条件全不命中 → H4 → H5，零结构写，仅刷新运行报告。

## Target resolution

唯一 owner：`.specify/shared/workflow/target-resolution.md`。**house-keeping 强依赖 `.specify/`**：显式目标优先；未给 → 从会话 cwd 向上搜索最近的合法 `.specify/` 根（显式本地路径则从其向上搜索）；找不到 → **拒绝执行**并提示 `sdd-project-setup` install / `specify init`，可 handoff setup。远端先跑 execution-side target-root probe。setup 的规则不同（它不依赖 `.specify/`，由 setup 自己创建基线），见 owner。本节不复写规则。
