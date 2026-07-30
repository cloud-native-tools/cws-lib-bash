---
name: git-workflow
description: |
  Three-tier Git workflow management skill that dynamically discovers or defines branch names (trunk/pre-release/dev) and maintains `.specify/memory/git-workflow.md` as the single source of truth. Runs as a single **reconcile engine** (see `.specify/shared/patterns/reconcile-pattern.md`): the desired state is the declared three-tier branch structure + sync relations + per-branch `.gitexcludes` rules; every invocation observes the current repo state, diffs, and converges — bootstrap (interactive branch naming + creation + .gitexcludes init when the config doc is absent), health-check (structure/sync/.gitexcludes observation + residual report), and directed convergence (rebase sync, merge, and safe push with automatic .gitexcludes enforcement) are the same engine under different inputs. Covers pre-checks, rebase synchronization, conflict resolution, force-with-lease push strategies, and per-branch file exclusion via `.gitexcludes`. Use this when the user mentions ["git workflow", "branch sync", "rebase sync", "分支同步", "git rebase", "force-with-lease", "发布流程", "分支策略", "主干分支", "预发分支", "开发分支", "three-tier git", "git workflow setup", "创建git工作流", "工作流维护", "workflow health check", "工作流检查", "selective merge", "选择性合并", "排除文件", "忽略配置文件", "分支排除", "branch-exclusive", ".gitexcludes", "开发专属文件", "merge filter", "调谐工作流", "git 调谐"]
skill_id: "<SKILL:.specify/skills/git-workflow/SKILL.md>"
---

# git-workflow

## Overview

三层 Git 开发工作流管理技能。**只有一个运行模式——调谐（Reconcile）**，遵循 [`.specify/shared/patterns/reconcile-pattern.md`](../../shared/patterns/reconcile-pattern.md)：

- **期望态（spec）** = `.specify/memory/git-workflow.md` 声明的三层分支结构（MAIN/PRE/DEV 存在且 tracking 正确）+ 固定 rebase 同步关系（无积压分叉）+ 各分支 `.gitexcludes` 规则就位且被排除路径未被跟踪 + 本次用户操作指令。
- **当前态（status）** = 仓库实际分支结构、同步状态、`.gitexcludes` 分布。
- **调谐** = 观测 → diff（过容忍带）→ 收敛（分级确认）→ 校验。

原「Setup / Maintain / Execute 三模式」是**同一调谐引擎在不同输入下的表现**：

| 输入 | 作用域 | 行为（旧模式名） |
|------|--------|------------------|
| 配置文档 `.specify/memory/git-workflow.md` 不存在 | **Bootstrap** | 对空配置的调谐：交互确认分支名、创建分支、初始化 `.gitexcludes`、生成配置文档（Setup） |
| 文档存在 且 无操作参数 | **全维度体检** | R1 观测 + R3 diff + 残差汇报，不自动收敛（Maintain） |
| 文档存在 且 有操作参数 | **定向收敛** | 用户指令并入期望态，执行具体 git 操作（自动尊重 `.gitexcludes`）（Execute） |

**容忍带**：同步状态 `0 0`、`.gitexcludes` 内容语义等价、文档与实际分支名一致——均标记「已一致（容忍）」不触发收敛；仅 ahead/behind 分叉、分支缺失、排除路径仍被跟踪等实质偏离进入收敛建议。

**分级确认门禁**（与模式文档对齐）：

| 动作类 | 门禁 |
|--------|------|
| 只读观测、体检报告、本地分支创建 | 自动执行 |
| 写远端（push / 建远端分支）、直接 merge 入 PRE/MAIN | **停下确认**（外部权威源） |
| 共享分支 force-with-lease 强推 | **停下确认** + 团队同步窗口 + 回滚预案 |

**强制产物**：体检的「工作流维护报告」同时充当观测快照与残差汇报；定向收敛的审计由 git 提交历史天然承担（每次同步/恢复操作都有显式 commit 与打印清单）。

### 分支角色

| 角色 | 含义 | 说明 |
|------|------|------|
| **`MAIN`** | 主干分支 | 上游主干，只接收已通过版本验证的代码 |
| **`PRE`** | 预发分支 | 预发发布分支，用于版本集成与环境验证 |
| **`DEV`** | 开发分支 | 本地开发分支，所有新改动先在此开发与自测 |

> **重要**：分支名称因项目而异（如 `master` / `xuanji/prepub` / `xuanji/hanzhi`，或 `main` / `staging` / `dev`）。本技能在执行时**动态确认**实际分支名，将其记录到 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md`，后续操作以该文档为准。

核心链路（角色代号）：

```
代码同步：MAIN -> PRE -> DEV
代码合入：MAIN <- PRE <- DEV
```

固定 rebase 关系：`PRE` 基于 `MAIN` rebase；`DEV` 基于 `PRE` rebase。

---

## Workflow

### Phase 0: 调谐作用域判定

0. **迁移旧位置文档（一次性）**：本技能的输出文档已从旧位置 `docs/git-workflow.md` 迁移到 `.specify/memory/git-workflow.md`。执行任何模式前，若检测到旧位置仍有文件而新位置尚不存在，先迁移：

   ```bash
   if [ -f "${SKILL_WORKDIR}/docs/git-workflow.md" ] && [ ! -f "${SKILL_WORKDIR}/.specify/memory/git-workflow.md" ]; then
     mkdir -p "${SKILL_WORKDIR}/.specify/memory"
     git mv "${SKILL_WORKDIR}/docs/git-workflow.md" "${SKILL_WORKDIR}/.specify/memory/git-workflow.md" 2>/dev/null \
       || mv "${SKILL_WORKDIR}/docs/git-workflow.md" "${SKILL_WORKDIR}/.specify/memory/git-workflow.md"
     echo "migrated git-workflow.md -> .specify/memory/"
   fi
   ```

   若归口 instructions 文档的 Documentation Map 仍引用旧路径 `docs/git-workflow.md`，同时将其更新为 `.specify/memory/git-workflow.md`。

1. 检查 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md` 是否存在。
2. 检查用户是否传入了操作参数（具体的 git 操作指令）。

| 文档存在 | 有操作参数 | 进入作用域 |
|----------|------------|------------|
| 否 | — | Bootstrap 调谐（Setup） |
| 是 | 否 | 全维度体检（Maintain） |
| 是 | 是 | 定向收敛（Execute） |

---

### Bootstrap 调谐（Setup）— 建立工作流

当 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md` 不存在时进入：期望态 = 完整三层工作流骨架，通过最少必要问题（逐一确认，不臆造分支名）+ 自动探测补齐信息。

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

#### 1.4 生成 `.specify/memory/git-workflow.md`

读取模板 `${SKILL_HOME}/assets/git-workflow-template.md`，替换 `<MAIN>` / `<PRE>` / `<DEV>` 为实际分支名，写入 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md`。

#### 1.5 初始化 `.gitexcludes`（分支排除规则）

询问用户：每个分支是否有「仅属于本分支、不应同步到其他分支」的目录或文件。

示例提问：「是否有某些目录/文件只属于特定分支？例如 `.github/`、`.claude/`、`.vscode/` 只保留在开发分支，不同步到主干？」

**`.gitexcludes` 机制说明**：

- 项目根目录的 `.gitexcludes` 文件定义**本分支专属文件**，语法与 `.gitignore` 完全一致。
- 每个分支各自维护自己的 `.gitexcludes`，内容可以不同。
- 无论向哪个分支同步代码（rebase 或 merge），目标分支的 `.gitexcludes` 匹配的文件/目录都会被保护，不被源分支覆盖。
- `.gitexcludes` 文件本身也隐含被排除（不会被其他分支的版本覆盖）。

若用户提供排除列表，为各分支创建对应的 `.gitexcludes`：

```bash
# 示例：在开发分支创建 .gitexcludes（DEV 分支通常不需要排除，因为它接收所有代码）
git checkout <DEV>
echo '# DEV branch: no exclusions (receives all code)' > .gitexcludes
git add .gitexcludes && git commit -m "chore: init .gitexcludes for DEV"

# 在 MAIN 分支创建 .gitexcludes
git checkout <MAIN>
cat > .gitexcludes << 'EOF'
# Files exclusive to dev branches, not synced to main
.github/
.claude/
.vscode/
.qoder/
EOF
git add .gitexcludes && git commit -m "chore: init .gitexcludes for MAIN"

# 在 PRE 分支创建 .gitexcludes（根据需要配置）
git checkout <PRE>
cat > .gitexcludes << 'EOF'
# Files exclusive to dev branches, not synced to pre-release
.vscode/
EOF
git add .gitexcludes && git commit -m "chore: init .gitexcludes for PRE"
```

若用户不需要排除规则，创建空 `.gitexcludes` 文件（留备后续使用）。

#### 1.6 更新 instructions 文档

在归口 instructions 文档的 Documentation Map 中添加引用行：

```markdown
| **Git Workflow** | `.specify/memory/git-workflow.md` | 分支同步机制与操作文件 | 三层分支模型、rebase 同步流程、推送策略、安全底线、.gitexcludes 机制 |
```

目标文档查找优先级：见 `${SKILL_HOME}/references/instructions-lookup.md`。

---

### 全维度体检（Maintain）— 观测 + diff + 残差汇报

当 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md` 存在且用户未传入操作参数时进入。只观测与 diff，不自动收敛；收敛建议列入报告尾部待用户确认。

#### 2.1 加载配置

从 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md` frontmatter 读取分支映射：

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

#### 2.4 `.gitexcludes` 一致性检查

检查各分支的 `.gitexcludes` 状态：

```bash
# 检查各分支是否存在 .gitexcludes
git show origin/<MAIN>:.gitexcludes 2>/dev/null && echo "MAIN: exists" || echo "MAIN: missing"
git show origin/<PRE>:.gitexcludes 2>/dev/null && echo "PRE: exists" || echo "PRE: missing"
git show origin/<DEV>:.gitexcludes 2>/dev/null && echo "DEV: exists" || echo "DEV: missing"
```

检查项：

- 各分支是否都有 `.gitexcludes` 文件（即使为空）
- `.gitexcludes` 中列出的路径是否在其他分支中仍被跟踪（若被排除且仍被跟踪，建议执行清理）
- 各分支 `.gitexcludes` 规则是否符合预期（如 MAIN 应排除开发配置文件）

#### 2.5 文档一致性检查

- `.specify/memory/git-workflow.md` 中记录的分支名与实际分支是否一致
- frontmatter 格式完整（`main_branch`、`pre_branch`、`dev_branch`、`last_updated`）
- instructions 文档中是否包含 Git Workflow 引用行

#### 2.6 输出维护报告（观测快照 + 残差汇报，强制产物）

容忍带内的项（同步 `0 0`、文档与实际一致）标记「✅ 已一致」；仅实质偏离进入「建议操作」：

```markdown
## 工作流维护报告

### 分支结构
- MAIN (<name>): ✅ 正常 / ❌ 问题描述
- PRE  (<name>): ✅ 正常 / ❌ 问题描述
- DEV  (<name>): ✅ 正常 / ❌ 问题描述

### 同步状态
- MAIN → PRE: ahead N / behind M （是否需要同步）
- PRE  → DEV: ahead N / behind M （是否需要同步）

### 排除规则状态
- MAIN .gitexcludes: ✅ 存在 / ❌ 缺失
- PRE  .gitexcludes: ✅ 存在 / ❌ 缺失
- DEV  .gitexcludes: ✅ 存在 / ❌ 缺失
- 被排除路径跟踪状态: ✅ 已清理 / ⚠️ 仍被跟踪（列表）

### 文档一致性
- .specify/memory/git-workflow.md: ✅ / ❌ 问题描述
- instructions 引用: ✅ / ❌

### 建议操作
- （列出需要执行的操作，如有）
```

---

### 定向收敛（Execute）— 执行工作流

当 `${SKILL_WORKDIR}/.specify/memory/git-workflow.md` 存在且用户传入了具体操作参数时进入：用户指令并入期望态，按下列预定义操作收敛，写远端/直接合入类动作遵循 Overview 的分级确认门禁。

#### 3.1 加载配置

同全维度体检 Step 2.1，从 frontmatter 读取 `MAIN` / `PRE` / `DEV` 分支名。

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

#### 3.3 通用排除处理子程序（.gitexcludes Subroutine）

所有同步/合并操作均自动调用此子程序。详细实现见 [`${SKILL_HOME}/references/gitexcludes-subroutine.md`](./references/gitexcludes-subroutine.md)。

**核心逻辑**：

1. **前置**：切换到目标分支后，先清理可能残留的旧标签（`git tag -d _gitexcludes_pre_sync`），再读取 `.gitexcludes` 并 `git tag _gitexcludes_pre_sync HEAD` 保存当前状态。**打印被保护文件清单供用户确认。**
2. **执行**：正常执行 rebase 或 merge。
3. **后置**：从保存点恢复 `.gitexcludes` 匹配的所有文件（含 `.gitexcludes` 本身），移除 tag 中不存在但被 sync 新引入的文件，**逐项打印恢复/移除结果**，若有变更则提交，清理临时标签。

> **设计原则**：
> - 谁接收代码（目标分支），谁的 `.gitexcludes` 说了算。方向无关。
> - `.gitexcludes` 本身是固定排除项，各分支内容可不同，永不被其他分支覆盖。

#### 3.4 解析并执行操作

根据用户指令匹配预定义操作：

##### 操作 A: 代码同步（MAIN → PRE → DEV）

触发词：同步、sync、拉取上游更新

**A1. 同步 MAIN → PRE**

```bash
git checkout <PRE>
# ── 前置：保存 PRE 的 .gitexcludes 状态 ──
# （调用 3.3 子程序前置）
git pull --rebase origin <PRE>
git rebase origin/<MAIN>
# ── 后置：恢复 PRE 的排除文件 ──
# （调用 3.3 子程序后置）
git rev-list --left-right --count origin/<PRE>...<PRE>
```

推送策略：
- 仅 ahead（`0 N`）：`git push origin <PRE>`
- ahead + behind（`M N`，M>0）：确认团队同步窗口 → `git push --force-with-lease origin <PRE>`

**A2. 同步 PRE → DEV**

```bash
git checkout <DEV>
# ── 前置：保存 DEV 的 .gitexcludes 状态 ──
git pull --rebase origin <DEV>
git rebase origin/<PRE>
# ── 后置：恢复 DEV 的排除文件 ──
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
# ── 前置：保存 PRE 的 .gitexcludes 状态 ──
git pull --rebase origin <PRE>
git merge <DEV> --no-ff -m "merge: <DEV> into <PRE>"
# ── 后置：恢复 PRE 的排除文件 ──
```

##### 操作 C: 提交到主干（PRE → MAIN）

触发词：提交到主干、合入主干、merge to main、发布

> **安全检查**：禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。

建议通过 PR 流程：`<PRE> → <MAIN>`。

或直接合入（需用户确认）：

```bash
git checkout <MAIN>
# ── 前置：保存 MAIN 的 .gitexcludes 状态 ──
git pull --rebase origin <MAIN>
git merge <PRE> --no-ff -m "merge: <PRE> into <MAIN>"
# ── 后置：恢复 MAIN 的排除文件 ──
```

##### 操作 D: 基于指定分支 rebase

触发词：rebase、变基

```bash
git checkout <target-branch>
# ── 前置：保存 target-branch 的 .gitexcludes 状态 ──
git pull --rebase origin <target-branch>
git rebase origin/<base-branch>
# ── 后置：恢复 target-branch 的排除文件 ──
```

##### 操作 E: 自定义操作

对于无法匹配预定义操作的用户指令，根据 `.specify/memory/git-workflow.md` 中的规范理解用户意图，拆解为安全的 git 操作序列。遵守 Security 章节的安全底线。

##### 操作 F: 管理 `.gitexcludes`

触发词：排除规则、gitexcludes、配置排除、分支专属文件、添加排除、移除排除

管理当前分支或指定分支的 `.gitexcludes` 文件：

**F1. 查看当前状态**

```bash
# 查看各分支的 .gitexcludes 内容
git show origin/<MAIN>:.gitexcludes 2>/dev/null || echo "(not found)"
git show origin/<PRE>:.gitexcludes 2>/dev/null || echo "(not found)"
git show origin/<DEV>:.gitexcludes 2>/dev/null || echo "(not found)"
```

**F2. 编辑排除规则**

根据用户指令修改指定分支的 `.gitexcludes`：

```bash
git checkout <target-branch>
# 编辑 .gitexcludes（添加/移除规则）
git add .gitexcludes
git commit -m "chore: update .gitexcludes for <target-branch>"
git push origin <target-branch>
```

**F3. 首次清理（若被排除路径已被跟踪）**

若目标分支中 `.gitexcludes` 列出的路径已被 Git 跟踪，需一次性移除：

```bash
git checkout <target-branch>
# 从索引移除但保留本地文件
while IFS= read -r pattern; do
  [[ "$pattern" =~ ^[[:space:]]*#.*$ || -z "${pattern// }" ]] && continue
  [[ "$pattern" == '!'* ]] && continue
  git rm -r --cached "$pattern" 2>/dev/null || true
done < .gitexcludes
git commit -m "chore: untrack files listed in .gitexcludes"
git push origin <target-branch>
```

> **注意**：这只是取消跟踪，不会删除工作目录中的实际文件。后续同步操作会自动跳过这些文件。

##### 操作 G: 验证排除效果

触发词：验证排除、检查排除状态、确认排除生效

同步后验证排除规则是否生效：

```bash
# 在目标分支上检查：排除路径是否在最近同步中被修改
git diff HEAD~1 HEAD -- $(cat .gitexcludes | grep -v '^#' | grep -v '^$' | tr '\n' ' ')
# 期望输出为空（排除路径未变动）

# 检查 .gitexcludes 中的路径是否仍被跟踪
git ls-files -- $(cat .gitexcludes | grep -v '^#' | grep -v '^$' | tr '\n' ' ')
# 若输出为空，表示已清理；若有输出，表示仍被跟踪（需执行 F3 清理）
```

---

## Security / 安全底线

1. `<MAIN>` 禁止直接 push 未审查代码。
2. 禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。
3. 禁止 `git push -f`，仅允许 `git push --force-with-lease`。
4. 对共享分支执行强推前，必须完成"通知 + 同步窗口 + 回滚预案"。
5. 同步/合并后必须验证 `.gitexcludes` 匹配的路径未被意外修改。
6. `.gitexcludes` 文件本身是**固定排除项**，各分支独立维护，永不被其他分支版本覆盖。
7. 排除子程序的前置和后置必须打印明确的文件清单，供用户确认哪些文件被保护/移除。

## Known Issues & Mitigations

| 异常现象 | 根因 | 应对策略 |
|----------|------|----------|
| `git checkout` 报错，本地改动会被覆盖 | 工作区不干净 | 先完成前置校验再切换分支 |
| rebase 后变为 `M N`（双向分叉） | 共享分支 rebase 重写历史 | `--force-with-lease` 受控推送，走团队同步窗口 |
| `skipped previously applied commit` | 分支存在重复补丁或历史漂移 | 记录 commit id，继续 rebase，`git log --left-right --cherry-pick` 差异核对 |
| 选择性合并后排除路径仍被修改 | `.gitexcludes` 未存在或子程序未调用 | 确认目标分支存在 `.gitexcludes`，重新执行同步并确保子程序正常运行 |
| `git rm --cached` 后本地文件消失 | 某些 Git 版本行为差异 | 从工作区恢复（`git checkout HEAD -- <path>`）或从 stash 恢复 |
| `.gitexcludes` 文件被同步覆盖 | 子程序未将 `.gitexcludes` 加入隐含保护 | 检查子程序后置是否包含 `git checkout _gitexcludes_pre_sync -- .gitexcludes` |

---

## .specify/memory/git-workflow.md 文档维护

- **创建**：Bootstrap 调谐（Setup）完成后，使用 `${SKILL_HOME}/assets/git-workflow-template.md` 生成。
- **更新**：分支改名时更新 frontmatter 映射；新增异常经验追加到 Known Issues 章节；更新 `last_updated` 日期。
- **数据源**：`.specify/memory/git-workflow.md` frontmatter 是后续所有操作的唯一分支名数据源；各分支的 `.gitexcludes` 是排除规则的数据源。

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/git-workflow/SKILL.md>`
- Canonical Path: `.specify/skills/git-workflow/SKILL.md`

## Path Conventions

- `${SKILL_HOME}/<relative-path>` — Skill-owned resources (scripts, references, assets).
- `${SKILL_WORKDIR}/<relative-path>` — runtime/user-facing paths.

## Resources

### References (`${SKILL_HOME}/references/`)
- `instructions-lookup.md` — instructions 文档查找优先级表。
- `gitexcludes-subroutine.md` — `.gitexcludes` 通用排除子程序详细实现。

### Assets (`${SKILL_HOME}/assets/`)
- `git-workflow-template.md` — `.specify/memory/git-workflow.md` 生成模板，含 `<MAIN>` / `<PRE>` / `<DEV>` 占位符。

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
     --unit-id "skill:git-workflow" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
