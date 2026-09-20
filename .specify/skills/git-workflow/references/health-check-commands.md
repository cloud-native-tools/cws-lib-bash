# 全维度体检命令序列

Phase 2（分支结构、同步状态、`.gitexcludes` 一致性检查、维护报告模板）的完整命令序列。SKILL.md 保留步骤骨架，此处承载观测命令与报告格式。

## 分支结构检查

```bash
git fetch origin
git branch -a --format='%(refname:short)'
git for-each-ref --format='%(refname:short) -> %(upstream:short)' refs/heads/<MAIN> refs/heads/<PRE> refs/heads/<DEV>
```

检查项：

- `MAIN`、`PRE`、`DEV` 分支是否存在于本地和远端
- 分支 tracking 关系是否正确

## 同步状态检查

```bash
git rev-list --left-right --count origin/<MAIN>...origin/<PRE>
git rev-list --left-right --count origin/<PRE>...origin/<DEV>
git rev-list --left-right --count origin/<MAIN>...origin/<DEV>
```

## .gitexcludes 一致性检查

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

## 维护报告模板

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

### Git Workflow 块一致性
- `.specify/git-workflow.md` 托管块（分支名与实际一致）: ✅ / ❌ 问题描述
- START/END 标记成对存在: ✅ / ❌
- 无遗留第二数据源（docs/git-workflow.md、.specify/memory/git-workflow.md、旧版 instructions.md 内联 `## Git Workflow` 块）: ✅ / ⚠️ 冗余待处理（路径）

### 建议操作
- （列出需要执行的操作，如有）
```
