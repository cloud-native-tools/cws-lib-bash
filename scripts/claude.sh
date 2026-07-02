# shellcheck shell=bash

function claude_yolo() {
  # 拒绝 root：yolo 跳过全部权限检查，root 下风险不可控
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "claude_yolo: refused to run as root user" >&2
    return 1
  fi
  # 最大权限 + 最大 effort，让 agent 完全自主完成工作
  claude --permission-mode bypassPermissions --effort xhigh "$@"
}

function claude_dev() {
  # 交互式开发：文件编辑自动接受，其余操作需用户确认
  claude --permission-mode acceptEdits "$@"
}

function claude_pipe() {
  # 管道非交互模式：自动输出 + 跳过权限检查（与 yolo 等效权限）
  claude --print --permission-mode bypassPermissions "$@"
}
