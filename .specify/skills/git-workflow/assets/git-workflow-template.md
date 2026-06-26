---
main_branch: "<MAIN>"
pre_branch: "<PRE>"
dev_branch: "<DEV>"
last_updated: "<DATE>"
---

# Git 分支同步机制（<MAIN> / <PRE> / <DEV>）

> 本文档由 `git-workflow` 技能自动生成并维护，是项目 Git 工作流的唯一数据源。
> 如需修改分支名称，请直接编辑上方 frontmatter 中的字段。

## 1. 分支职责与固定关系

- `<MAIN>`：上游主干，只接收已通过版本验证的代码。
- `<PRE>`：预发发布分支，用于版本集成与环境验证。
- `<DEV>`：本地开发分支，所有新改动先在此开发与自测。

固定 rebase 关系（必须保持）：

1. `<PRE>` 基于 `<MAIN>` rebase。
2. `<DEV>` 基于 `<PRE>` rebase。

代码同步链路：`<MAIN> -> <PRE> -> <DEV>`
代码合入链路：`<MAIN> <- <PRE> <- <DEV>`

---

## 2. 前置校验（必须先过）

```bash
git fetch origin
git status --short --branch
git for-each-ref --format='%(refname:short) -> %(upstream:short)' refs/heads/<MAIN> refs/heads/<PRE> refs/heads/<DEV>
```

若工作区不干净，先处理：

```bash
# 方式1：推荐，提交本地改动
git add .
git commit -m "chore: save local work before sync"

# 方式2：临时保存（含未跟踪文件）
git stash push -u -m "pre-sync-<date>"
```

> Gate：`git status --short` 必须为空，才能进入下一步。

---

## 3. 同步流程

### 3.1 同步 `<MAIN> -> <PRE>`

```bash
git checkout <PRE>
git pull --rebase origin <PRE>
git rebase origin/<MAIN>
git rev-list --left-right --count origin/<PRE>...<PRE>
```

推送策略：

- 仅 ahead（形如 `0 N`）：`git push origin <PRE>`
- ahead+behind（形如 `M N` 且 `M>0,N>0`）：
  1. 在团队同步窗口执行；
  2. 通知所有基于 `<PRE>` 开发的同学先暂停拉取；
  3. 使用：`git push --force-with-lease origin <PRE>`

### 3.2 同步 `<PRE> -> <DEV>`

```bash
git checkout <DEV>
git pull --rebase origin <DEV>
git rebase origin/<PRE>
git rev-list --left-right --count origin/<DEV>...<DEV>
```

若出现 `skipped previously applied commit`：

- 记录 commit id；
- 继续完成 rebase；
- 执行一次差异核对：

```bash
git log --left-right --cherry-pick --oneline origin/<DEV>...<DEV>
```

推送策略与 `<PRE>` 相同：

- `0 N`：正常 push。
- `M N`：团队确认后 `git push --force-with-lease origin <DEV>`。

### 3.3 恢复临时保存（若使用过 stash）

```bash
git stash list
git stash pop
```

---

## 4. 开发、提测、发布链路

1. 新修改只进 `<DEV>`，完成本地验证（至少 `lint + test + build`）。
2. 发起 PR `<DEV> -> <PRE>`，在预发做版本测试。
3. 版本测试通过后，发起 PR `<PRE> -> <MAIN>`。

> 规范链路：`<DEV>`（开发）→ `<PRE>`（版本测试）→ `<MAIN>`（最终合入）

---

## 5. 冲突与异常处理

rebase 冲突：

```bash
git add <冲突文件>
git rebase --continue
```

放弃本次 rebase：

```bash
git rebase --abort
```

---

## 6. 发布分支安全底线

1. `<MAIN>` 禁止直接 push 未审查代码。
2. 禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。
3. 禁止 `git push -f`，仅允许 `git push --force-with-lease`。
4. 对共享分支执行强推前，必须完成"通知 + 同步窗口 + 回滚预案"。

---

## 7. Known Issues

> 在实际使用中遇到的异常及对策，由 git-workflow 技能在执行过程中自动追加。

| 异常现象 | 根因分析 | 应对策略 |
|----------|----------|----------|
| `git checkout` 报错，本地改动会被覆盖 | 工作区不干净 | 执行前置校验后再切换分支 |
| rebase 后 `origin/...<branch>...<branch>` 变为 `M N`（双向分叉） | 共享分支 rebase 重写提交历史 | 使用 `--force-with-lease` 受控推送，走团队同步窗口 |
| rebase 过程出现 `skipped previously applied commit` | 分支存在重复补丁（patch-id 重复）或历史漂移 | 记录 commit id，继续完成 rebase，执行 `git log --left-right --cherry-pick` 差异核对 |
| 选择性合并后排除路径仍被修改 | `.gitexcludes` 未存在或同步子程序未正确执行 | 确认目标分支存在 `.gitexcludes`，重新执行同步 |

---

## 8. 分支排除规则（.gitexcludes）

每个分支通过根目录的 `.gitexcludes` 文件定义本分支的专属文件。语法与 `.gitignore` 完全一致。

### 8.1 设计原则

- **每个分支有自己的 `.gitexcludes`**：内容可以不同，各自维护。
- **目标分支说了算**：无论向哪个分支同步代码，目标分支的 `.gitexcludes` 匹配的文件都会被保护。
- **方向无关**：无论 MAIN→DEV 还是 DEV→MAIN，目标分支的专属文件始终受保护。
- **隐含保护**：`.gitexcludes` 文件本身也被保护，不会被其他分支的版本覆盖。

### 8.2 各分支配置示例

**`<MAIN>` 分支的 `.gitexcludes`**：

```gitignore
# 开发专属文件，不同步到主干
.github/
.claude/
.vscode/
.qoder/
```

**`<PRE>` 分支的 `.gitexcludes`**：

```gitignore
# 仅 IDE 配置不同步到预发
.vscode/
```

**`<DEV>` 分支的 `.gitexcludes`**：

```gitignore
# DEV 接收所有代码，无排除
```

### 8.3 工作机制

同步/合并操作自动执行以下流程：

1. 切换到目标分支后，保存 `.gitexcludes` 匹配文件的当前状态
2. 执行 rebase 或 merge
3. 恢复被保护文件到同步前的状态
4. 若有变更则自动提交恢复记录

### 8.4 验证

同步后执行：

```bash
# 确认排除路径未被修改
git diff HEAD~1 HEAD -- $(cat .gitexcludes | grep -v '^#' | grep -v '^$' | tr '\n' ' ')
# 期望输出为空
```

### 8.5 管理排除规则

要添加或移除排除路径：

1. 切换到目标分支。
2. 编辑 `.gitexcludes` 文件。
3. `git add .gitexcludes && git commit -m "chore: update .gitexcludes"`。
4. 若新增路径已被本分支跟踪，执行 `git rm -r --cached <path>` 取消跟踪。
