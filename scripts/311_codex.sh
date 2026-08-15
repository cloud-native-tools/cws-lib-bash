# shellcheck shell=bash

function codex_dev() {
  # 交互式开发：仅受信只读命令免批准，其余操作需用户确认（最接近旧 suggest）
  codex -a untrusted "$@"
}

function codex_yolo() {
  # 拒绝 root：yolo 跳过全部权限检查，root 下风险不可控
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "codex_yolo: refused to run as root user" >&2
    return 1
  fi
  # 最大权限：跳过全部审批与沙箱，让 agent 完全自主完成工作
  codex --dangerously-bypass-approvals-and-sandbox "$@"
}

function codex_print() {
  codex --quiet "$@"
}
