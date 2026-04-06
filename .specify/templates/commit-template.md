
# Git Commit Message Template

> 目标：生成一个**单行**、简介、可读、可追溯的 commit message，用于：
>
> `git commit -m "{msg}"`

## Output (single line)

渲染后的 `{msg}` **必须且只能**是一行：

```text
[TYPE]([SCOPE]): [SUBJECT]
```

## Placeholders

- `[TYPE]`：提交类型（见下方 Allowed types）
- `[SCOPE]`：提交影响范围（优先用 feature/spec key，例如 `NNN-short-name`）
- `[SUBJECT]`：一句话摘要（祈使句/动词开头，≤72 chars 优先）

可选（用于生成 `[SCOPE]` / `[SUBJECT]` 的上下文字段）：

- `[BRANCH]`：当前分支名（例如 `feat/123-login-reset`）
- `[REQUIREMENTS_KEY]`：spec 目录 key（例如 `123-login-reset`）
- `[FEATURE_TITLE]`：feature 标题（优先来自 requirements.md 标题）
- `[DATE]`：ISO 日期（YYYY-MM-DD）

## Allowed types

优先从以下集合中选择一个：

- `feat`：新增/实现用户可感知能力（通常包含 `src/` 或运行逻辑变更）
- `fix`：缺陷修复
- `docs`：仅文档/规范/说明变更（不改变运行行为）
- `test`：仅测试变更
- `chore`：构建/工具/依赖/杂项（CI、脚本、格式化等）

## Scope rules

1. **优先**使用 `[REQUIREMENTS_KEY]` 作为 `[SCOPE]`：
	- 从 `.specify/specs/[REQUIREMENTS_KEY]/` 的目录名推导（例如 `123-login-reset`）
2. 若无法获得 `[REQUIREMENTS_KEY]`：
	- 从 `[BRANCH]` 推导一个简短 scope（去掉前缀 `feat/`、`fix/`、`chore/` 等；必要时截断）
3. `[SCOPE]` 应尽量短、稳定、可追溯（能对应到 spec 目录或 feature registry）

## Subject rules

- 用祈使句/动词开头：Implement/Add/Fix/Update/Refactor…（中文也可，但需简洁一致）
- 避免结尾句号
- 避免含糊表达：例如 “update stuff / misc changes”
- 优先让 subject 与 `[FEATURE_TITLE]` 或 spec 文档语义对齐

## Recommended patterns

- `feat([SCOPE]): implement [FEATURE_TITLE]`
- `fix([SCOPE]): resolve <short-problem>`
- `docs([SCOPE]): update specs and plans`

## Examples

```text
feat(123-login-reset): implement password reset flow
fix(123-login-reset): prevent token reuse after reset
docs(123-login-reset): align requirements and plan
chore(tooling): refresh prereq scripts
```

