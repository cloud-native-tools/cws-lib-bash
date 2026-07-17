# shellcheck shell=bash

# Claude Code - Anthropic 的命令行 AI Agent 工具
# 二进制命令：claude
# 文档：https://code.claude.com/docs/en/cli-reference

# ---------------------------------------------------------------------------
# 统一变量：不同工具仅此处不同，函数逻辑保持一致
# ---------------------------------------------------------------------------

# 二进制命令；可在 source 前导出 CLAUDE_BIN 覆盖
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

# 默认 option：所有命令执行时统一附加；可导出 CLAUDE_OPTION 覆盖/扩展
CLAUDE_OPTION="${CLAUDE_OPTION:-}"

# ---------------------------------------------------------------------------
# 基础执行入口：所有模式函数都经由此入口，统一使用 *_BIN 与 *_OPTION
# ---------------------------------------------------------------------------

function claude_run() {
  # shellcheck disable=SC2086
  "${CLAUDE_BIN}" ${CLAUDE_OPTION} "$@"
}

# ---------------------------------------------------------------------------
# 生命周期：Install / Uninstall / Config
# ---------------------------------------------------------------------------

function claude_install() {
  # 官方原生安装器（仅支持 macOS/Linux）
  # 文档：https://code.claude.com/docs/en/setup
  log info "Installing Claude Code..."
  have curl || return "${RETURN_FAILURE:-1}"
  curl -fsSL https://claude.ai/install.sh | bash
}

function claude_uninstall() {
  log info "Uninstalling Claude Code..."
  if have npm; then
    npm uninstall -g @anthropic-ai/claude-code && return "${RETURN_SUCCESS:-0}"
  fi
  log error "npm not found; please remove the ${CLAUDE_BIN} binary manually"
  return "${RETURN_FAILURE:-1}"
}

function claude_config() {
  # 打开/管理配置
  claude_run config "$@"
}

# ---------------------------------------------------------------------------
# 运行模式：YOLO / Dev / Plan / Print / JSON
# ---------------------------------------------------------------------------

function claude_yolo() {
  # 拒绝 root：yolo 跳过全部权限检查，root 下风险不可控
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "claude_yolo: refused to run as root user" >&2
    return 1
  fi
  # 最大权限：跳过全部权限检查，让 agent 完全自主完成工作
  claude_run --dangerously-skip-permissions "$@"
}

function claude_dev() {
  # 交互式开发：文件编辑自动接受，其余操作需用户确认
  claude_run --permission-mode acceptEdits "$@"
}

function claude_plan() {
  # 计划模式：只读分析，不执行任何修改操作
  claude_run --permission-mode plan "$@"
}

function claude_auto() {
  # 自动模式：自动执行操作，减少确认交互
  claude_run --permission-mode auto "$@"
}

function claude_print() {
  # 管道非交互模式：直接输出结果
  claude_run --print "$@"
}

function claude_json() {
  # JSON 输出模式：用于程序化处理
  claude_run --print --output-format json "$@"
}
