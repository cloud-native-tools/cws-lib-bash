# shellcheck shell=bash

# OpenCode - 开源终端 AI Agent 工具
# 二进制命令：opencode
# 文档：https://opencode.ai/docs/cli/

# ---------------------------------------------------------------------------
# 统一变量：不同工具仅此处不同，函数逻辑保持一致
# ---------------------------------------------------------------------------

# 二进制命令；可在 source 前导出 OPENCODE_BIN 覆盖
OPENCODE_BIN="${OPENCODE_BIN:-opencode}"

# 默认 option：所有命令执行时统一附加；可导出 OPENCODE_OPTION 覆盖/扩展
OPENCODE_OPTION="${OPENCODE_OPTION:-}"

# ---------------------------------------------------------------------------
# 基础执行入口：所有模式函数都经由此入口，统一使用 *_BIN 与 *_OPTION
# ---------------------------------------------------------------------------

function opencode_run() {
  # shellcheck disable=SC2086
  "${OPENCODE_BIN}" ${OPENCODE_OPTION} "$@"
}

# ---------------------------------------------------------------------------
# 生命周期：Install / Uninstall / Config
# ---------------------------------------------------------------------------

function opencode_install() {
  # 官方安装器（仅支持 macOS/Linux）
  # 文档：https://opencode.ai/docs/
  log info "Installing OpenCode..."
  have curl || return "${RETURN_FAILURE:-1}"
  curl -fsSL https://opencode.ai/install | bash
}

function opencode_uninstall() {
  # 内置卸载命令，移除全部相关文件
  log info "Uninstalling OpenCode..."
  opencode_run uninstall --force
}

function opencode_config() {
  # 配置 Provider 凭据（登录）
  opencode_run auth login "$@"
}

# ---------------------------------------------------------------------------
# 运行模式：YOLO / Dev / Plan / Print / JSON
# ---------------------------------------------------------------------------

function opencode_yolo() {
  # 拒绝 root：yolo 跳过全部权限检查，root 下风险不可控
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "opencode_yolo: refused to run as root user" >&2
    return 1
  fi
  # 最大权限：优先 --yolo，不支持时回退到 --auto-approve（自动批准）
  opencode_run --yolo "$@" || opencode_run --auto-approve "$@"
}

function opencode_dev() {
  # 交互式开发：自动批准未显式拒绝的权限
  opencode_run --auto-approve "$@"
}

function opencode_auto() {
  # 自动模式：opencode 仅提供 --auto-approve 一级自动批准
  opencode_run --auto-approve "$@"
}

function opencode_plan() {
  # 计划模式：只读分析（通过实验开关启用）
  OPENCODE_EXPERIMENTAL_PLAN_MODE=true opencode_run "$@"
}

function opencode_print() {
  # 管道非交互模式：直接输出结果
  opencode_run run "$@"
}

function opencode_json() {
  # JSON 输出模式：用于程序化处理
  opencode_run run --format json "$@"
}
