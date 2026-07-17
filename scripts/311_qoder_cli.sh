# shellcheck shell=bash

# Qoder CLI - 命令行 Agent 程序（类似 Claude Code）
# 二进制命令：qodercli
# 与 qoder_ide.sh 中的 qoder IDE 命令严格区分

function qoder_cli_yolo() {
  # 拒绝 root：yolo 跳过全部权限检查，root 下风险不可控
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "qoder_cli_yolo: refused to run as root user" >&2
    return 1
  fi
  # 最大权限，让 agent 完全自主完成工作
  # 优先使用 --dangerously-skip-permissions，不支持时回退到 bypass_permissions 模式
  qodercli --dangerously-skip-permissions "$@" || qodercli --permission-mode bypass_permissions "$@"
}

function qoder_cli_dev() {
  # 交互式开发：文件编辑自动接受，其余操作需用户确认
  qodercli --permission-mode accept_edits "$@"
}

function qoder_cli_plan() {
  # 计划模式：只读分析，不执行任何修改操作
  qodercli --permission-mode default "$@"
}

function qoder_cli_auto() {
  # 自动模式：自动执行操作，减少确认交互
  qodercli --permission-mode auto "$@"
}

function qoder_cli_print() {
  # 管道非交互模式：自动输出结果
  qodercli --print "$@"
}

function qoder_cli_json() {
  # JSON 输出模式：用于程序化处理
  qodercli --print --output-format json "$@"
}
