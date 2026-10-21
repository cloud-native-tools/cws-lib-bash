# Git Workflow 状态文件定位与写入

本技能把项目声明的分支工作流信息写入独立状态文件 **`${SKILL_WORKDIR}/docs/git-workflow.md`** 的 Git Workflow 托管块，不写入 instructions 文件，也不生成其他工作流文档（`.specify/instructions.md` 的 `## Git Workflow` 章节只保留指向本文件的指针，由 `/speckit.instructions` 维护）。工作流模型是项目级选择（菜单见 SKILL.md 作用域 A）；块内首行 `Workflow model` 声明所选模型，其后的行随模型形态而异——下文示例为三层模型的填充形态。

## 目标文件

- 固定路径：`${SKILL_WORKDIR}/docs/git-workflow.md`；文件不存在时用 `${SKILL_HOME}/assets/git-workflow-block.md` 渲染整文件创建。
- 不要对 instructions 别名（`CLAUDE.md` / `AGENTS.md` / `QODER.md` 等）做任何写入。

## 写入规则

```bash
# 判断块是否已存在
grep -q '<!-- GIT_WORKFLOW_START -->' "${SKILL_WORKDIR:-.}/docs/git-workflow.md" && echo "block present" || echo "block missing"
```

- **文件已存在**：只替换 `<!-- GIT_WORKFLOW_START -->` 与 `<!-- GIT_WORKFLOW_END -->` **之间**的内容；标记本身与块外内容保持字节不变。
- **文件不存在**：读取 `${SKILL_HOME}/assets/git-workflow-block.md`，替换占位符后整文件写入。
- **占位状态**：未建立工作流时 `Workflow model` 声明行保留 `None yet.`——这一行即 Bootstrap 作用域的判定依据。
- **单一数据源**：分支信息只写入该文件。不要写进 instructions 文件，也不要另建 `.specify/git-workflow.md` 或 `.specify/memory/git-workflow.md`。

## 旧版块迁移（升级场景）

早期版本把托管块写在 `.specify/instructions.md` 的 `## Git Workflow` 章节内。检测：

```bash
grep -q '<!-- GIT_WORKFLOW_START -->' "${SKILL_WORKDIR:-.}/.specify/instructions.md" && echo "legacy block in instructions"
```

命中时：先把该块内容原样迁入 `docs/git-workflow.md`（文件缺失时先创建），再把 instructions 文件中的整个旧 `## Git Workflow` 章节替换为指针句（"分支角色唯一事实源在 `docs/git-workflow.md`，由 git-workflow 技能机器维护"），并在报告中说明已迁移。遗留 `.specify/git-workflow.md` / `.specify/memory/git-workflow.md` 仍按 Phase 0 规则处理。

## 块内容

模板见 `${SKILL_HOME}/assets/git-workflow-block.md`。填充后的形态（**三层模型示例**；其他模型以 `Workflow model` 声明行 + 该模型自己的约定行替代角色表）：

```markdown
<!-- GIT_WORKFLOW_START -->
<!-- Workflow model is a per-project choice (menu: single-branch / dual-branch / temp-branch / MAIN-PRE-DEV three-tier); the declaration below records THIS project's choice, followed by its operating rules. -->
- **Workflow model**: MAIN/PRE/DEV 三层
| Role | Branch | Tracking | Purpose |
|------|--------|----------|---------|
| MAIN | `master` | `origin/master` | 上游主干，只接收已通过版本验证的代码 |
| PRE | `xuanji/prepub` | `origin/xuanji/prepub` | 预发发布分支，用于版本集成与环境验证 |
| DEV | `xuanji/hanzhi` | `origin/xuanji/hanzhi` | 本地开发分支，所有新改动先在此开发与自测 |

- **Sync chain (rebase)**: `master -> xuanji/prepub -> xuanji/hanzhi`
- **Merge chain (PR)**: `master <- xuanji/prepub <- xuanji/hanzhi`
- **Last updated**: 2026-08-10
<!-- GIT_WORKFLOW_END -->
```

## 读取（体检与定向收敛的数据源）

```bash
# 提取三层模型的分支名（Branch 列反引号内的值；仅声明模型为三层时使用）
awk '/<!-- GIT_WORKFLOW_START -->/,/<!-- GIT_WORKFLOW_END -->/' "${SKILL_WORKDIR:-.}/docs/git-workflow.md" \
  | awk -F'|' '$2 ~ /MAIN|PRE|DEV/ {gsub(/[ `]/, "", $2); gsub(/[ `]/, "", $3); print $2"="$3}'
```

输出形如 `MAIN=master` / `PRE=xuanji/prepub` / `DEV=xuanji/hanzhi`，供后续 git 操作使用。若文件缺失、或某行的 Branch 为空 / 仍是 `None yet.`，视为块未填写 → 进入 Bootstrap。
