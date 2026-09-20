# Bootstrap 调谐命令序列

Phase 0（遗留配置迁移）与 Phase 1（分支检测、创建、`.gitexcludes` 初始化、写入 Git Workflow 块）的完整命令序列。SKILL.md 保留步骤骨架与交互决策逻辑，此处承载操作细节。

## 遗留配置迁移

分支信息现在只存在于专用状态文件 `${SKILL_WORKDIR}/.specify/git-workflow.md` 的 Git Workflow 托管块中（写入规则见 [instructions-lookup.md](./instructions-lookup.md)），本技能**不再生成独立工作流文档**。执行任何模式前，若检测到任一遗留来源，把其分支映射提取出来填入托管块：

```bash
for legacy in "${SKILL_WORKDIR}/.specify/memory/git-workflow.md" "${SKILL_WORKDIR}/docs/git-workflow.md"; do
  [ -f "$legacy" ] || continue
  echo "legacy config found: $legacy"
  sed -n '/^---$/,/^---$/p' "$legacy" \
    | grep -E '^(main_branch|pre_branch|dev_branch|last_updated):' \
    | sed 's/"//g'
done
```

把提取到的 `main_branch` / `pre_branch` / `dev_branch` 写入块的 MAIN / PRE / DEV 行，并刷新 `Last updated`。

- 迁移完成后，遗留文件即为**冗余数据源**：在报告中列出其路径并建议用户删除或归档，**不要自动删除**（可能含用户手写的补充内容，删除不可逆）。
- 旧版 instructions.md 内联的 `## Git Workflow` 块也是遗留来源：把其中分支表迁入 `.specify/git-workflow.md` 托管块后，将 instructions.md 中该节替换为指向新文件的指针句（由 `/speckit.instructions` 收敛，不要手改整份文件）。
- 若 instructions 文件的 Documentation Map 仍有指向 `docs/git-workflow.md` 或 `.specify/memory/git-workflow.md` 的引用行，删除该行——已无独立文档可引用。

## 分支检测

```bash
git branch -a --format='%(refname:short)'
```

## 创建缺失分支

若用户确认需要新建某个层级分支：

```bash
git checkout -b <PRE> origin/<MAIN>
git push -u origin <PRE>

git checkout -b <DEV> origin/<PRE>
git push -u origin <DEV>
```

## 初始化 .gitexcludes

`.gitexcludes` 机制详见 [gitexcludes-subroutine.md](./gitexcludes-subroutine.md) 的设计原则。此处仅列出初始化命令。

询问用户：每个分支是否有「仅属于本分支、不应同步到其他分支」的目录或文件。示例提问：「是否有某些目录/文件只属于特定分支？例如 `.github/`、`.claude/`、`.vscode/` 只保留在开发分支，不同步到主干？」

`.gitexcludes` 机制说明：

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

## 写入 Git Workflow 块

用 `${SKILL_HOME}/assets/git-workflow-block.md` 填充分支名、tracking 与日期，整文件渲染写入 `${SKILL_WORKDIR}/.specify/git-workflow.md`。文件不存在时按模板创建（含文件头说明 + 托管块）；标记内替换规则与读取命令：见 [instructions-lookup.md](./instructions-lookup.md)。

不要在 docs/ 文档空间额外添加引用行——`.specify/git-workflow.md` 是机器维护的状态文件，不是文档页。
