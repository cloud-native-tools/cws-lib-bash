---
id: "20260811T183321Z-skill-cli-setup"
unit_id: "skill:cli-setup"
unit_type: "skill"
run_id: "codex-approval-mode-removed-20260812"
scope: "local"
partial: false
created: "2026-08-11T18:33:21Z"
summary: "codex-cli 0.146.0 已移除 --approval-mode 参数（codex_yolo 启动报错 unexpected argument）。cli-setup 技能两处仍引用旧 flag：scripts/config-agent.sh:526（codex dev 分支 --approval-mode suggest）与 references/permission-modes.md（"
---

## Review
codex-cli 0.146.0 已移除 --approval-mode 参数（codex_yolo 启动报错 unexpected argument）。cli-setup 技能两处仍引用旧 flag：scripts/config-agent.sh:526（codex dev 分支 --approval-mode suggest）与 references/permission-modes.md（dev/yolo 两行及 codex.sh 说明）。新版等价物：-a/--ask-for-approval <untrusted|on-failure|on-request|never>、-s/--sandbox <read-only|workspace-write|danger-full-access>、真 yolo 用 --dangerously-bypass-approvals-and-sandbox；--full-auto 亦已移除。项目自有脚本 scripts/311_codex.sh 已先行修复（codex_dev→-a untrusted，codex_yolo→dangerously-bypass+root 拒绝保护），测试同步更新并通过。

## Optimization Points
- 1. config-agent.sh codex 分支改为：dev) codex -a untrusted；yolo) codex --dangerously-bypass-approvals-and-sandbox（保留 root 拒绝保护）。2. permission-modes.md 的 codex 行同步改写，并注明 --approval-mode 自 codex-cli 0.146 起移除。3. 建议框架在 permission-modes.md 增加 CLI 版本探测指引：分发模板前以 <cli> --help 验证 flag 仍存在。
