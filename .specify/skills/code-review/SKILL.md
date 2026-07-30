---
name: code-review
description: |
  Command-line code review workflow built around git-delta. Covers the full four-phase closed loop — pre-submission (author self-check, PR-size guard), review execution (structured P0–P6 dimension checks in a tests-first order, delta-rendered side-by-side diffs), feedback & iteration (six-level severity taxonomy: blocking/important/suggestion/nitpick/question/praise, convergence rules), and merge & knowledge precipitation (merge gate, metrics). Deterministic work (rendering diffs, recording notes, aggregating reports, merge-gate verdicts) is delegated to `${SKILL_HOME}/scripts/git-delta-review.sh`; judgment work (reading code, writing review comments) stays with the human/LLM reviewer. Use this when the user mentions ["code review", "review diff", "review PR", "review MR", "代码审查", "代码评审", "审查代码", "review 代码", "git-delta", "delta diff", "side-by-side diff", "PR review", "MR 审查", "合并前审查", "review 工作流", "code review workflow", "审查意见", "review comments", "合入门禁", "merge gate"]
skill_id: "<SKILL:.specify/skills/code-review/SKILL.md>"
---

# code-review

## Overview

以 **git-delta 为核心渲染工具** 的命令行 Code Review 工作流，覆盖 **提交前 → 审查中 → 反馈后 → 合入后** 四阶段闭环。核心理念：**git-delta 负责"看得舒服"，脚本负责"记得下来"，Markdown 负责"传得出去"；审查判断由人/LLM 完成**。

分工边界：

- **脚本（确定性）**：`diff` 渲染、`review` 逐文件流程、`note` 意见落盘、`report` 汇总与合入门禁判定 — 全部封装在 `${SKILL_HOME}/scripts/git-delta-review.sh`。
- **Reviewer（判断性）**：按 P0–P6 维度读代码、写意见、做合入决策 — 方法论见 [`${SKILL_HOME}/references/review-workflow.md`](./references/review-workflow.md)。

## Workflow

> 完整方法论（PR 模板、自检清单、表达原则、反模式、度量指标）见 [`references/review-workflow.md`](./references/review-workflow.md)；delta 安装与 git 配置见 [`references/delta-setup.md`](./references/delta-setup.md)。以下只保留执行骨架。

### Phase 0 — 路由与环境确认

1. 确认角色：**Author**（提交前自检，走 Phase 1）还是 **Reviewer**（审查执行，走 Phase 2–4）。两者都要时按顺序执行。
2. 确认对比基准：默认 `main..HEAD`，可用 `--since/--head` 或 `GIT_BASE/GIT_HEAD` 环境变量覆盖。
3. 确认 delta 可用：`command -v delta`。缺失时**报错并给出安装命令后停止**（见 `references/delta-setup.md`），不自动安装。仅 `note`/`report` 子命令可在无 delta 环境运行（CI/Agent 场景）。

### Phase 1 — 提交前准备（Author）

> 目标：让 Reviewer 不需要猜。

1. **粒度守门**：运行 `${SKILL_HOME}/scripts/git-delta-review.sh diff --stat`。脚本内置 size guard——变更 >400 行警告拆分，>800 行强烈警告。同时核对单一职责（一个 PR 只做一件事）。
2. **上下文准备**：按 `references/review-workflow.md` §2.2 的 PR 描述模板（What/Why/How/Testing/Risk）补全说明。
3. **自检清单**：按 `references/review-workflow.md` §2.3 逐项过（编译测试通过、无调试残留、无敏感信息、diff 已自审等）。"自审一遍自己的 diff"用 `${SKILL_HOME}/scripts/git-delta-review.sh diff --worktree`（未提交改动，HEAD vs 工作区）或 `diff --side-by-side --since <base>`（已提交改动）。

### Phase 2 — 审查执行（Reviewer）

> 目标：知道看什么、按什么顺序看。

1. **建立全局认知**：`diff --files` 看变更文件与增删行数；读 PR 描述理解意图。
2. **结构化审查**：`review --since <base>` 启动逐文件流程（未提交改动用 `review --worktree`）。脚本默认**测试文件优先**（测试即规格说明），逐文件渲染 delta side-by-side diff；`--focus <path>` 聚焦单模块，`--no-tests-first` 关闭排序。
3. **按 P0–P6 维度检查**（正确性 → 安全性 → 设计 → 可维护性 → 性能 → 风格 → 测试，检查项见 `references/review-workflow.md` §3.1），边看边定级。
4. **记录意见**：
   - 交互模式：每个文件后按提示 `c` 录入意见（选级别/行号/内容），可多条。
   - **Agent/CI 非交互模式**：`note -s <severity> -f <file> [-l <line>] -c <comment>` 逐条写入。LLM 审查时必须先完整阅读 diff 再写意见，禁止凭文件名臆测。
5. **时间管理**：单次 Review 不超过 60 分钟；>400 行分次聚焦审查（`--focus`）；规模参考见 `references/review-workflow.md` §3.3。

### Phase 3 — 反馈与迭代

> 目标：对事不对人、快速收敛。

1. **意见分级**（六级，脚本强制校验）：`blocking` 🔴 必须修改 / `important` 🟠 强烈建议 / `suggestion` 🟢 可选优化 / `nitpick` ⚪ 纯风格 / `question` ❓ 需要解释 / `praise` 👍 值得肯定。表达原则见 `references/review-workflow.md` §4.2。
2. **收敛判定**：`report --summary` 输出按级别汇总 + 合入门禁——存在 `blocking` 则不可合入；存在 `important` 需逐条回应。收敛条件与防无限循环规则见 `references/review-workflow.md` §4.3。
3. **迭代**：Author 修改后重跑 Phase 2（聚焦已改文件），Reviewer 仅针对未解决项复审。

### Phase 4 — 合入与沉淀

> 目标：Review 不是终点而是起点。

1. **合入前检查**：`report --summary` 门禁通过 + CI 全绿 + 无未决讨论线程（完整清单见 `references/review-workflow.md` §5.1）。
2. **归档报告**：`.specify/review/<branch>-<ts>.md` 为 Markdown，可直接粘贴到 PR 描述/评论区或随仓库提交。
3. **知识沉淀**：同一问题被提出超过 2 次 → 转化为 Linter 规则或 Checklist 条目，而非依赖人每次发现（沉淀形式见 `references/review-workflow.md` §5.2）。

## Strict Requirements

- **级别词汇表固定**：只允许 `blocking/important/suggestion/nitpick/question/praise`，脚本会拒绝其他值——不要发明新级别。
- **意见必须落到具体位置**：`-f <file> -l <line>`，全局性意见才允许省略 `-f`（记为 `(global)`）。
- **不绕过门禁**：`report --summary` 显示 blocking 未清零时，不得给出"可以合入"的结论。
- **大变更不硬审**：size guard 触发 >800 行警告时，先建议拆分，再逐模块 `--focus` 审查。
- **环境缺失即停**：delta 缺失时报错 + 安装指引，停止执行；不自动安装、不降级为 `git diff` 裸输出冒充已审查。

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/code-review/SKILL.md>`
- Canonical Path: `.specify/skills/code-review/SKILL.md`

## Path Conventions

This Skill follows the canonical path conventions defined in `templates/commands/skills.md` (`## Path Conventions`):

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets, sub-directory files).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path this Skill reads from or writes to (inputs in the user's project, outputs delivered to the user). Review 记录统一写入 `${SKILL_WORKDIR}/.specify/review/`（可用 `REVIEW_DIR` 覆盖）。
- Never conflate the two; never embed agent-specific install paths.

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)
- `git-delta-review.sh` — 四子命令闭环工具：`diff`（delta 渲染 + size guard；`--worktree` 支持未提交改动）、`review`（交互式逐文件，测试优先，同支持 `--worktree`）、`note`（非交互意见落盘，无需 delta）、`report`（列表/最新/按级汇总 + 合入门禁）。

### References (`${SKILL_HOME}/references/`)
- `review-workflow.md` — 四阶段方法论全本：提交粒度规则、PR 描述模板、自检清单、P0–P6 审查维度、审查顺序、反馈分级与表达原则、迭代收敛规则、合入策略、知识沉淀、度量指标、角色矩阵、反模式对策。
- `delta-setup.md` — git-delta 安装（brew/apt/cargo/预编译包）、git 全局配置（pager/side-by-side/line-numbers/navigate/diff3）、容器集成与故障排查。

### Assets (`${SKILL_HOME}/assets/`)
- No assets currently.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:code-review" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
