---
name: git-workflow
description: |
  Three-tier Git workflow management skill that dynamically discovers or defines branch names (trunk/pre-release/dev) and maintains `docs/git-workflow.md` as the single source of truth. Supports three modes: Setup (interactive branch naming + creation), Maintain (structure/sync health check), Execute (rebase sync, merge, and safe push). Covers pre-checks, rebase synchronization, conflict resolution, and force-with-lease push strategies. Use this when the user mentions ["git workflow", "branch sync", "rebase sync", "分支同步", "git rebase", "force-with-lease", "发布流程", "分支策略", "主干分支", "预发分支", "开发分支", "three-tier git", "git workflow setup", "创建git工作流", "工作流维护", "workflow health check", "工作流检查"]
skill_id: "<SKILL:.specify/skills/git-workflow/SKILL.md>"
---

# git-workflow

## Overview

三层 Git 开发工作流管理技能，根据项目状态和用户输入自动选择运行模式：

| 模式 | 触发条件 | 功能 |
|------|----------|------|
| **Setup** | `docs/git-workflow.md` 不存在 | 建立工作流：确认分支名、创建分支、生成配置文档 |
| **Maintain** | 文档存在 且 无操作参数 | 维护工作流：检查分支结构与文档一致性，输出健康报告 |
| **Execute** | 文档存在 且 有操作参数 | 执行工作流：按工作流规范执行具体 git 操作 |

### 分支角色

| 角色 | 含义 | 说明 |
|------|------|------|
| **`MAIN`** | 主干分支 | 上游主干，只接收已通过版本验证的代码 |
| **`PRE`** | 预发分支 | 预发发布分支，用于版本集成与环境验证 |
| **`DEV`** | 开发分支 | 本地开发分支，所有新改动先在此开发与自测 |

> **重要**：分支名称因项目而异（如 `master` / `xuanji/prepub` / `xuanji/hanzhi`，或 `main` / `staging` / `dev`）。本技能在执行时**动态确认**实际分支名，将其记录到 `${SKILL_WORKDIR}/docs/git-workflow.md`，后续操作以该文档为准。

核心链路（角色代号）：

```
代码同步：MAIN -> PRE -> DEV
代码合入：MAIN <- PRE <- DEV
```

固定 rebase 关系：`PRE` 基于 `MAIN` rebase；`DEV` 基于 `PRE` rebase。

---

## Workflow

### Phase 0: 模式判定

1. 检查 `${SKILL_WORKDIR}/docs/git-workflow.md` 是否存在。
2. 检查用户是否传入了操作参数（具体的 git 操作指令）。

| 文档存在 | 有操作参数 | 进入模式 |
|----------|------------|----------|
| 否 | — | Mode 1: Setup |
| 是 | 否 | Mode 2: Maintain |
| 是 | 是 | Mode 3: Execute |

---

### Mode 1: Setup — 建立工作流

当 `${SKILL_WORKDIR}/docs/git-workflow.md` 不存在时进入。

#### 1.1 检测现有分支

```bash
git branch -a --format='%(refname:short)'
```

#### 1.2 交互式确认分支名

逐一向用户确认（每次只问一个问题）：

1. **主干分支 `MAIN`**：
   - 从远端分支中推荐最常见的候选（`main`、`master`），询问用户选择或自定义。
   - 示例：「检测到远端有 `origin/main` 和 `origin/master`，哪个是您的主干分支？」
2. **预发分支 `PRE`**：
   - 询问是否存在预发分支，若存在请用户提供名称；若不存在，建议一个命名规范（如 `staging`、`release`、`prepub`）。
   - 示例：「项目的预发分支叫什么？如果还没有，建议命名为 `staging`。」
3. **开发分支 `DEV`**：
   - 同上逻辑，推荐命名（如 `dev`、`develop`）。

#### 1.3 创建缺失分支

若用户确认需要新建某个层级分支：

```bash
git checkout -b <PRE> origin/<MAIN>
git push -u origin <PRE>

git checkout -b <DEV> origin/<PRE>
git push -u origin <DEV>
```

#### 1.4 生成 `docs/git-workflow.md`

读取模板 `${SKILL_HOME}/assets/git-workflow-template.md`，替换 `<MAIN>` / `<PRE>` / `<DEV>` 为实际分支名，写入 `${SKILL_WORKDIR}/docs/git-workflow.md`。

#### 1.5 更新 instructions 文档

在归口 instructions 文档的 Documentation Map 中添加引用行：

```markdown
| **Git Workflow** | `docs/git-workflow.md` | 分支同步机制与操作文件 | 三层分支模型、rebase 同步流程、推送策略、安全底线 |
```

目标文档查找优先级：见 `${SKILL_HOME}/references/instructions-lookup.md`。

---

### Mode 2: Maintain — 维护工作流

当 `${SKILL_WORKDIR}/docs/git-workflow.md` 存在且用户未传入操作参数时进入。

#### 2.1 加载配置

从 `${SKILL_WORKDIR}/docs/git-workflow.md` frontmatter 读取分支映射：

```yaml
MAIN = main_branch 字段值
PRE  = pre_branch 字段值
DEV  = dev_branch 字段值
```

#### 2.2 分支结构检查

```bash
git fetch origin
git branch -a --format='%(refname:short)'
git for-each-ref --format='%(refname:short) -> %(upstream:short)' refs/heads/<MAIN> refs/heads/<PRE> refs/heads/<DEV>
```

检查项：

- `MAIN`、`PRE`、`DEV` 分支是否存在于本地和远端
- 分支 tracking 关系是否正确

#### 2.3 同步状态检查

```bash
git rev-list --left-right --count origin/<MAIN>...origin/<PRE>
git rev-list --left-right --count origin/<PRE>...origin/<DEV>
git rev-list --left-right --count origin/<MAIN>...origin/<DEV>
```

#### 2.4 文档一致性检查

- `docs/git-workflow.md` 中记录的分支名与实际分支是否一致
- frontmatter 格式完整（`main_branch`、`pre_branch`、`dev_branch`、`last_updated`）
- instructions 文档中是否包含 Git Workflow 引用行

#### 2.5 输出维护报告

```markdown
## 工作流维护报告

### 分支结构
- MAIN (<name>): ✅ 正常 / ❌ 问题描述
- PRE  (<name>): ✅ 正常 / ❌ 问题描述
- DEV  (<name>): ✅ 正常 / ❌ 问题描述

### 同步状态
- MAIN → PRE: ahead N / behind M （是否需要同步）
- PRE  → DEV: ahead N / behind M （是否需要同步）

### 文档一致性
- docs/git-workflow.md: ✅ / ❌ 问题描述
- instructions 引用: ✅ / ❌

### 建议操作
- （列出需要执行的操作，如有）
```

---

### Mode 3: Execute — 执行工作流

当 `${SKILL_WORKDIR}/docs/git-workflow.md` 存在且用户传入了具体操作参数时进入。

#### 3.1 加载配置

同 Mode 2 Step 2.1，从 frontmatter 读取 `MAIN` / `PRE` / `DEV` 分支名。

#### 3.2 前置校验

```bash
git fetch origin
git status --short --branch
```

若工作区不干净，向用户建议：

```bash
# 方式 1：推荐 — 提交本地改动
git add . && git commit -m "chore: save local work before sync"

# 方式 2：临时保存（含未跟踪文件）
git stash push -u -m "pre-sync-$(date +%Y%m%d)"
```

> **Gate**：`git status --short` 必须为空，才能继续执行。

#### 3.3 解析并执行操作

根据用户指令匹配预定义操作：

##### 操作 A: 代码同步（MAIN → PRE → DEV）

触发词：同步、sync、拉取上游更新

**A1. 同步 MAIN → PRE**

```bash
git checkout <PRE>
git pull --rebase origin <PRE>
git rebase origin/<MAIN>
git rev-list --left-right --count origin/<PRE>...<PRE>
```

推送策略：
- 仅 ahead（`0 N`）：`git push origin <PRE>`
- ahead + behind（`M N`，M>0）：确认团队同步窗口 → `git push --force-with-lease origin <PRE>`

**A2. 同步 PRE → DEV**

```bash
git checkout <DEV>
git pull --rebase origin <DEV>
git rebase origin/<PRE>
git rev-list --left-right --count origin/<DEV>...<DEV>
```

推送策略同 A1。若出现 `skipped previously applied commit`，记录 commit id，继续 rebase，执行差异核对：

```bash
git log --left-right --cherry-pick --oneline origin/<DEV>...<DEV>
```

**A3. 恢复临时保存**（若使用过 stash）

```bash
git stash list && git stash pop
```

##### 操作 B: 提交到预发（DEV → PRE）

触发词：提交到预发、合入预发、merge to pre、提测

建议通过 PR 流程：`<DEV> → <PRE>`。

或直接合入（需用户确认）：

```bash
git checkout <PRE>
git pull --rebase origin <PRE>
git merge <DEV> --no-ff -m "merge: <DEV> into <PRE>"
```

##### 操作 C: 提交到主干（PRE → MAIN）

触发词：提交到主干、合入主干、merge to main、发布

> **安全检查**：禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。

建议通过 PR 流程：`<PRE> → <MAIN>`。

或直接合入（需用户确认）：

```bash
git checkout <MAIN>
git pull --rebase origin <MAIN>
git merge <PRE> --no-ff -m "merge: <PRE> into <MAIN>"
```

##### 操作 D: 基于指定分支 rebase

触发词：rebase、变基

```bash
git checkout <target-branch>
git pull --rebase origin <target-branch>
git rebase origin/<base-branch>
```

##### 操作 E: 自定义操作

对于无法匹配预定义操作的用户指令，根据 `docs/git-workflow.md` 中的规范理解用户意图，拆解为安全的 git 操作序列。遵守 Security 章节的安全底线。

---

## Security / 安全底线

1. `<MAIN>` 禁止直接 push 未审查代码。
2. 禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。
3. 禁止 `git push -f`，仅允许 `git push --force-with-lease`。
4. 对共享分支执行强推前，必须完成"通知 + 同步窗口 + 回滚预案"。

## Known Issues & Mitigations

| 异常现象 | 根因 | 应对策略 |
|----------|------|----------|
| `git checkout` 报错，本地改动会被覆盖 | 工作区不干净 | 先完成前置校验再切换分支 |
| rebase 后变为 `M N`（双向分叉） | 共享分支 rebase 重写历史 | `--force-with-lease` 受控推送，走团队同步窗口 |
| `skipped previously applied commit` | 分支存在重复补丁或历史漂移 | 记录 commit id，继续 rebase，`git log --left-right --cherry-pick` 差异核对 |

---

## docs/git-workflow.md 文档维护

- **创建**：Mode 1 Setup 完成后，使用 `${SKILL_HOME}/assets/git-workflow-template.md` 生成。
- **更新**：分支改名时更新 frontmatter 映射；新增异常经验追加到 Known Issues 章节；更新 `last_updated` 日期。
- **数据源**：`docs/git-workflow.md` frontmatter 是后续所有操作的唯一分支名数据源。

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/git-workflow/SKILL.md>`
- Canonical Path: `.specify/skills/git-workflow/SKILL.md`

## Path Conventions

- `${SKILL_HOME}/<relative-path>` — Skill-owned resources (scripts, references, assets).
- `${SKILL_WORKDIR}/<relative-path>` — runtime/user-facing paths.

## Resources

### References (`${SKILL_HOME}/references/`)
- `instructions-lookup.md` — instructions 文档查找优先级表。

### Assets (`${SKILL_HOME}/assets/`)
- `git-workflow-template.md` — `docs/git-workflow.md` 生成模板，含 `<MAIN>` / `<PRE>` / `<DEV>` 占位符。
