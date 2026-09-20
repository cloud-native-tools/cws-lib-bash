# 定向收敛命令序列

Phase 3（前置校验）与操作 A-G（代码同步、合入预发/主干、rebase、`.gitexcludes` 管理、验证排除）的完整命令序列。SKILL.md 保留操作触发词与推送策略决策，此处承载命令细节。

所有同步/合并操作均自动调用 [gitexcludes-subroutine.md](./gitexcludes-subroutine.md) 的前置/后置子程序——以下命令中 `# ── 前置 ──` / `# ── 后置 ──` 注释处即子程序调用点。

## 前置校验

```bash
git fetch origin
git status --short --branch
```

若工作区不干净，先判定残留改动的归属，再选择路径：

- **残留属于本工作流操作本身**（如刚编辑的 `.gitexcludes`、状态文件或同步前置产物）：将其作为本次操作的一部分归组提交，不要求用户另行处理。
- **残留属于其他工作**：向用户建议以下两种方式之一：

```bash
# 方式 1：推荐 — 提交本地改动
git add . && git commit -m "chore: save local work before sync"

# 方式 2：临时保存（含未跟踪文件）
git stash push -u -m "pre-sync-$(date +%Y%m%d)"
```

> **警告**：禁止用破坏性手段清空工作区来通过本 Gate——`git reset --hard`、`git checkout -- .`、`git restore .`、`git clean -f` 会不可逆地丢弃未提交工作；只允许上面的提交或 stash 路径。

> **Gate**：`git status --short` 必须为空，才能继续执行。

## 操作 A: 代码同步

触发词：同步、sync、拉取上游更新

### A1. 同步 MAIN → PRE

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

### A2. 同步 PRE → DEV

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

### A3. 恢复临时保存

若使用过 stash：

```bash
git stash list && git stash pop
```

## 操作 B: 提交到预发

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

## 操作 C: 提交到主干

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

## 操作 D: rebase

触发词：rebase、变基

```bash
git checkout <target-branch>
# ── 前置：保存 target-branch 的 .gitexcludes 状态 ──
git pull --rebase origin <target-branch>
git rebase origin/<base-branch>
# ── 后置：恢复 target-branch 的排除文件 ──
```

## 操作 F: 管理 .gitexcludes

触发词：排除规则、gitexcludes、配置排除、分支专属文件、添加排除、移除排除

### F1. 查看当前状态

```bash
# 查看各分支的 .gitexcludes 内容
git show origin/<MAIN>:.gitexcludes 2>/dev/null || echo "(not found)"
git show origin/<PRE>:.gitexcludes 2>/dev/null || echo "(not found)"
git show origin/<DEV>:.gitexcludes 2>/dev/null || echo "(not found)"
```

### F2. 编辑排除规则

根据用户指令修改指定分支的 `.gitexcludes`：

```bash
git checkout <target-branch>
# 编辑 .gitexcludes（添加/移除规则）
git add .gitexcludes
git commit -m "chore: update .gitexcludes for <target-branch>"
git push origin <target-branch>
```

### F3. 首次清理

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

## 操作 G: 验证排除效果

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
