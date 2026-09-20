# 异常现象与应对策略

Known Issues & Mitigations — 常见 git 工作流异常的根因分析与应对。

| 异常现象 | 根因 | 应对策略 |
|----------|------|----------|
| `git checkout` 报错，本地改动会被覆盖 | 工作区不干净 | 先完成前置校验再切换分支 |
| rebase 后变为 `M N`（双向分叉） | 共享分支 rebase 重写历史 | `--force-with-lease` 受控推送，走团队同步窗口 |
| `skipped previously applied commit` | 分支存在重复补丁或历史漂移 | 记录 commit id，继续 rebase，`git log --left-right --cherry-pick` 差异核对 |
| 选择性合并后排除路径仍被修改 | `.gitexcludes` 未存在或子程序未调用 | 确认目标分支存在 `.gitexcludes`，重新执行同步并确保子程序正常运行 |
| `git rm --cached` 后本地文件消失 | 某些 Git 版本行为差异 | 从工作区恢复（`git checkout HEAD -- <path>`）或从 stash 恢复 |
| `.gitexcludes` 文件被同步覆盖 | 子程序未将 `.gitexcludes` 加入隐含保护 | 检查子程序后置是否包含 `git checkout _gitexcludes_pre_sync -- .gitexcludes` |
| 已建立工作流却被判为 Bootstrap（重复建文档风险） | 技能随分支版本化：自旧分支加载的旧版技能文本仍按过期位置约定（`docs/git-workflow.md` / `.specify/memory/git-workflow.md`）找状态文件，找不到即误入 Bootstrap | 按 Phase 0 版本漂移探测处理：以当前检出的技能文本为准重新加载，无条件探测 `.specify/git-workflow.md` 托管块，命中即以该块为数据源 |
| 链路恢复/追赶 rebase 报 `CONFLICT (add/add): .gitexcludes` | 下层分支补建 `.gitexcludes` 后，共同基线之后两侧各自新增同名文件，已有该文件的上层分支 rebase 时必然触发，可预判 | 解法确定——保留变基分支自己的版本：rebase 中被重放提交一侧为 `--theirs`，执行 `git checkout --theirs -- .gitexcludes && git add .gitexcludes && git rebase --continue`；merge 场景方向相反（接收分支保留自身版本用 `--ours`）。依据 Security 规则 6：各分支 `.gitexcludes` 永不被其他分支版本覆盖 |
