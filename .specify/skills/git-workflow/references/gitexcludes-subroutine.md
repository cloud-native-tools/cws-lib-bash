# .gitexcludes 通用排除子程序

所有同步/合并操作均自动调用此子程序。**目标分支**的 `.gitexcludes` 决定哪些文件被保护。

## 设计原则

- **谁接收代码（目标分支），谁的 `.gitexcludes` 说了算。**
- 方向无关——无论 MAIN→DEV 还是 DEV→MAIN，目标分支的专属文件始终受保护。
- **`.gitexcludes` 文件本身是固定排除项**：各分支的 `.gitexcludes` 内容可以不同，因此它永远不会被其他分支的版本覆盖，无需在文件中显式列出自己。
- `.gitexcludes` 语法与 `.gitignore` 完全一致（支持 glob 模式、注释行 `#`、否定模式 `!`）。
- **所有排除/恢复操作必须打印明确信息**，供用户确认哪些文件被保护、哪些被移除。

## 前置（sync 前）

切换到目标分支后，读取其 `.gitexcludes` 并记录被保护文件的当前状态：

```bash
if [ -f .gitexcludes ]; then
  # 解析 .gitexcludes 并列出匹配的已跟踪文件
  EXCLUDED_FILES=$(while IFS= read -r pattern; do
    [[ "$pattern" =~ ^[[:space:]]*#.*$ || -z "${pattern// }" ]] && continue
    [[ "$pattern" == '!'* ]] && continue
    git ls-files -- "$pattern" 2>/dev/null
  done < .gitexcludes)

  # 打印被保护文件清单供用户确认
  echo "=== .gitexcludes: 以下文件将在同步后被保护（不被覆盖） ==="
  echo "  [FIXED] .gitexcludes  (固定排除，各分支独立维护)"
  if [ -n "$EXCLUDED_FILES" ]; then
    echo "$EXCLUDED_FILES" | while IFS= read -r f; do
      echo "  [EXCL]  $f"
    done
  else
    echo "  (无额外排除文件)"
  fi
  echo "==="

  # 清理可能残留的旧标签（防止上次异常中断后指向错误 commit）
  git tag -d _gitexcludes_pre_sync 2>/dev/null || true
  # 保存当前状态（创建临时标签）
  git tag _gitexcludes_pre_sync HEAD
fi
```

## 后置（sync 后）

同步操作完成后，恢复被保护文件到同步前的状态，并移除不应存在的新引入文件：

```bash
if git rev-parse _gitexcludes_pre_sync >/dev/null 2>&1; then
  RESTORED_COUNT=0
  REMOVED_COUNT=0

  if [ -f .gitexcludes ]; then
    echo "=== .gitexcludes: 执行后置恢复 ==="
    while IFS= read -r pattern; do
      [[ "$pattern" =~ ^[[:space:]]*#.*$ || -z "${pattern// }" ]] && continue
      [[ "$pattern" == '!'* ]] && continue
      # 恢复 tag 中存在的文件到旧状态
      git checkout _gitexcludes_pre_sync -- "$pattern" 2>/dev/null && {
        echo "  [✓ RESTORED] $pattern"
        RESTORED_COUNT=$((RESTORED_COUNT + 1))
      }
      # 移除 tag 中不存在但被 sync 引入的新文件（排除路径中的新增）
      git ls-files -- "$pattern" 2>/dev/null | while IFS= read -r f; do
        if ! git show _gitexcludes_pre_sync:"$f" >/dev/null 2>&1; then
          git rm --cached "$f" 2>/dev/null && echo "  [✗ REMOVED]  $f"
          REMOVED_COUNT=$((REMOVED_COUNT + 1))
        fi
      done
    done < .gitexcludes
  fi

  # 固定排除：始终恢复 .gitexcludes 文件本身（各分支独立维护）
  git checkout _gitexcludes_pre_sync -- .gitexcludes 2>/dev/null && echo "  [✓ FIXED]    .gitexcludes (固定排除，已恢复本分支版本)"

  echo "=== 恢复完成: restored=$RESTORED_COUNT, removed=$REMOVED_COUNT ==="

  # 若有变更则提交
  git diff --cached --quiet || git commit -m "chore: restore branch-exclusive files after sync"

  # 清理临时标签
  git tag -d _gitexcludes_pre_sync
fi
```

## 使用方式

在每个同步/合并操作中：

1. 切换到目标分支后执行**前置**
2. 执行 rebase 或 merge
3. 执行**后置**

## 示例：完整操作序列

```bash
# 同步 MAIN → PRE 的完整流程
git checkout <PRE>

# ── 前置 ──
git tag -d _gitexcludes_pre_sync 2>/dev/null || true
git tag _gitexcludes_pre_sync HEAD
echo "=== .gitexcludes: 以下文件将在同步后被保护 ==="
echo "  [FIXED] .gitexcludes"
cat .gitexcludes | grep -v '^#' | grep -v '^$' | while read -r p; do
  echo "  [EXCL]  $(git ls-files -- "$p" 2>/dev/null)"
done
echo "==="

# ── 同步 ──
git pull --rebase origin <PRE>
git rebase origin/<MAIN>

# ── 后置 ──
echo "=== .gitexcludes: 执行后置恢复 ==="
if [ -f .gitexcludes ]; then
  while IFS= read -r pattern; do
    [[ "$pattern" =~ ^[[:space:]]*#.*$ || -z "${pattern// }" ]] && continue
    [[ "$pattern" == '!'* ]] && continue
    git checkout _gitexcludes_pre_sync -- "$pattern" 2>/dev/null && echo "  [✓ RESTORED] $pattern"
    git ls-files -- "$pattern" 2>/dev/null | while IFS= read -r f; do
      git show _gitexcludes_pre_sync:"$f" >/dev/null 2>&1 || { git rm --cached "$f" 2>/dev/null && echo "  [✗ REMOVED]  $f"; }
    done
  done < .gitexcludes
  git checkout _gitexcludes_pre_sync -- .gitexcludes 2>/dev/null && echo "  [✓ FIXED]    .gitexcludes"
  git diff --cached --quiet || git commit -m "chore: restore branch-exclusive files after sync"
fi
echo "=== 恢复完成 ==="
git tag -d _gitexcludes_pre_sync 2>/dev/null || true
```

## 注意事项

- `.gitexcludes` 文件本身是**固定排除项**，无需在文件中列出自己。各分支可能有不同的排除规则，因此它永远不被其他分支覆盖。
- 前置和后置均会打印明确的信息（`[EXCL]`、`[✓ RESTORED]`、`[✗ REMOVED]`、`[✓ FIXED]`），供用户确认排除结果。
- 临时标签 `_gitexcludes_pre_sync` 仅存在于操作过程中，完成后立即清理。
- 若 rebase 产生冲突，需先解决冲突再执行后置。
- 否定模式 `!` 当前被跳过（简化处理），未来可按需扩展。
- `git ls-files -- "$pattern"` 使用 pathspec 匹配，对目录级 pattern（如 `.github/`）会匹配其下所有文件。
