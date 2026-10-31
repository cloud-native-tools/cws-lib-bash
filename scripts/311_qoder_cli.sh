# shellcheck shell=bash

# Qoder CLI - 命令行 AI Agent 工具（类似 Claude Code）
# 二进制命令：qodercli
# 文档：https://docs.qoder.com/en/cli/quick-start
# 与 qoder_ide.sh 中的 qoder IDE 命令严格区分

# ---------------------------------------------------------------------------
# 统一变量：不同工具仅此处不同，函数逻辑保持一致
# ---------------------------------------------------------------------------

# 二进制命令；可在 source 前导出 QODER_CLI_BIN 覆盖
QODER_CLI_BIN="${QODER_CLI_BIN:-qodercli}"

# 默认 option：所有命令执行时统一附加；可导出 QODER_CLI_OPTION 覆盖/扩展
QODER_CLI_OPTION="${QODER_CLI_OPTION:-}"

# 后台模式默认模型 / 推理强度 / 上下文窗口；可用同名环境变量或函数选项覆盖
# 默认值取自 xuanji-images 当前 session 配置（~/.qoder/settings.json: model=qmodel_38max/Qwen3.8-Max, effort=xhigh, contextWindow=1000000）
QODER_CLI_MODEL="${QODER_CLI_MODEL:-Qwen3.8-Max}"
QODER_CLI_EFFORT="${QODER_CLI_EFFORT:-xhigh}"
QODER_CLI_CONTEXT_WINDOW="${QODER_CLI_CONTEXT_WINDOW:-1000000}"

# 后台模式日志目录；可导出 QODER_CLI_LOG_DIR 覆盖
QODER_CLI_LOG_DIR="${QODER_CLI_LOG_DIR:-${TMPDIR:-/tmp}/qoder-cli}"

# 用户级配置根与临时根；可导出同名变量覆盖（测试用临时目录替换）
QODER_CLI_HOME="${QODER_CLI_HOME:-${HOME}/.qoder}"
QODER_CLI_TMPDIR="${QODER_CLI_TMPDIR:-${TMPDIR:-/tmp}}"

# 运行痕迹保留天数：临时标记 / 运行日志 / 会话转写；可导出同名变量覆盖
QODER_CLI_PRUNE_TMP_DAYS="${QODER_CLI_PRUNE_TMP_DAYS:-3}"
QODER_CLI_PRUNE_LOG_DAYS="${QODER_CLI_PRUNE_LOG_DAYS:-14}"
QODER_CLI_PRUNE_SESSION_DAYS="${QODER_CLI_PRUNE_SESSION_DAYS:-30}"

# ---------------------------------------------------------------------------
# 基础执行入口：所有模式函数都经由此入口，统一使用 *_BIN 与 *_OPTION
# ---------------------------------------------------------------------------

function qoder_cli_run() {
  # shellcheck disable=SC2086
  "${QODER_CLI_BIN}" ${QODER_CLI_OPTION} "$@"
}

# ---------------------------------------------------------------------------
# 生命周期：Install / Uninstall / Config
# ---------------------------------------------------------------------------

function qoder_cli_install() {
  # 官方安装器（仅支持 macOS/Linux）
  # 文档：https://docs.qoder.com/en/cli/quick-start

  log info "Installing Qoder CLI..."
  have curl || return "${RETURN_FAILURE:-1}"

  # 安装器会在 TMPDIR 下解压并执行二进制；若临时目录为 noexec 则回退到可执行的临时目录
  if tmpdir_exec_ok; then
    curl -fsSL https://qoder.com/install | bash
  else
    local install_tmpdir
    if ! install_tmpdir=$(tmpdir_ensure); then
      log error "no executable tmpdir available for installation"
      return "${RETURN_FAILURE:-1}"
    fi
    log warn "${TMPDIR:-/tmp} is not executable; using TMPDIR=${install_tmpdir} for installation"
    curl -fsSL https://qoder.com/install | TMPDIR="${install_tmpdir}" bash
  fi
}

function qoder_cli_uninstall() {
  log info "Uninstalling Qoder CLI..."
  if have npm; then
    npm uninstall -g @qoder-ai/qodercli && return "${RETURN_SUCCESS:-0}"
  fi
  log error "npm not found; please remove the ${QODER_CLI_BIN} binary manually"
  return "${RETURN_FAILURE:-1}"
}

function qoder_cli_config() {
  # 打开/管理配置
  qoder_cli_run config "$@"
}

function qoder_cli_prune() {
  # 清理过期运行痕迹，降低启动 / 退出 / --resume 时的目录扫描与转写开销
  # Usage: qoder_cli_prune [--apply] [-t days] [-l days] [-s days]
  #   -t  临时标记（qoder-*-cwd 与旧版本原生缓存）保留天数（默认 3）
  #   -l  logs/runs 运行日志保留天数（默认 14）
  #   -s  会话转写（projects/*/transcript）与 logs/sessions 保留天数（默认 30）
  # 默认 dry-run 只报告将删除的条目数；--apply 才真正删除
  local apply=0
  local tmp_days="${QODER_CLI_PRUNE_TMP_DAYS}"
  local log_days="${QODER_CLI_PRUNE_LOG_DAYS}"
  local session_days="${QODER_CLI_PRUNE_SESSION_DAYS}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --apply) apply=1; shift ;;
      -t) tmp_days="$2"; shift 2 ;;
      -l) log_days="$2"; shift 2 ;;
      -s) session_days="$2"; shift 2 ;;
      *)
        log error "qoder_cli_prune: unknown argument $1"
        return "${RETURN_FAILURE:-1}"
        ;;
    esac
  done

  local home="${QODER_CLI_HOME}"
  local tmp="${QODER_CLI_TMPDIR}"
  if [[ ! -d "${home}" ]]; then
    log error "qoder_cli_prune: qodercli home not found: ${home}"
    return "${RETURN_FAILURE:-1}"
  fi

  local n_tx n_logs n_sessions n_marks n_natives
  n_tx=$(find "${home}/projects" -name "*.jsonl" -mtime +"${session_days}" 2>/dev/null | wc -l)
  n_logs=$(find "${home}/logs/runs" -mindepth 1 -maxdepth 1 -type d -mtime +"${log_days}" 2>/dev/null | wc -l)
  n_sessions=$(find "${home}/logs/sessions" -mindepth 1 -maxdepth 1 -type d -mtime +"${session_days}" 2>/dev/null | wc -l)
  n_marks=$(find "${tmp}" -maxdepth 1 -name "qoder-*-cwd" -mtime +"${tmp_days}" 2>/dev/null | wc -l)

  # 原生缓存按版本分目录（qodercli-natives-v<ver>-<user>）：保留 mtime 最新的一组
  local keep_prefix=""
  local newest=""
  if [[ -d "${tmp}" ]]; then
    # shellcheck disable=SC2012  # 版本目录名仅由字母数字与点组成，无空白风险
    newest=$(ls -td "${tmp}"/qodercli-natives-* 2>/dev/null | head -1)
  fi
  if [[ -n "${newest}" ]]; then
    keep_prefix=$(basename "${newest}" | sed -n 's/^\(qodercli-natives-v[0-9][0-9.]*\)-.*/\1/p')
  fi
  if [[ -n "${keep_prefix}" ]]; then
    n_natives=$(find "${tmp}" -maxdepth 1 -name "qodercli-natives-*" ! -name "${keep_prefix}-*" 2>/dev/null | wc -l)
  else
    n_natives=0
  fi

  if [[ "${apply}" -eq 1 ]]; then
    find "${home}/projects" -name "*.jsonl" -mtime +"${session_days}" -delete 2>/dev/null
    find "${home}/logs/runs" -mindepth 1 -maxdepth 1 -type d -mtime +"${log_days}" -exec rm -rf {} + 2>/dev/null
    find "${home}/logs/sessions" -mindepth 1 -maxdepth 1 -type d -mtime +"${session_days}" -exec rm -rf {} + 2>/dev/null
    find "${tmp}" -maxdepth 1 -name "qoder-*-cwd" -mtime +"${tmp_days}" -delete 2>/dev/null
    if [[ -n "${keep_prefix}" ]]; then
      find "${tmp}" -maxdepth 1 -name "qodercli-natives-*" ! -name "${keep_prefix}-*" -exec rm -rf {} + 2>/dev/null
    fi
  fi

  local mode="dry-run"
  [[ "${apply}" -eq 1 ]] && mode="applied"
  printf 'qodercli_prune: session_transcripts=%s run_logs=%s session_dirs=%s tmp_markers=%s stale_natives=%s (%s)\n' \
    "${n_tx}" "${n_logs}" "${n_sessions}" "${n_marks}" "${n_natives}" "${mode}"
  return "${RETURN_SUCCESS:-0}"
}

# ---------------------------------------------------------------------------
# 运行模式：YOLO / Dev / Plan / Print / JSON
# ---------------------------------------------------------------------------

function qoder_cli_yolo() {
  # 拒绝 root：yolo 跳过全部权限检查，root 下风险不可控
  if is_root; then
    echo "qoder_cli_yolo: refused to run as root user" >&2
    return 1
  fi
  # 最大权限，让 agent 完全自主完成工作
  # 优先使用 --dangerously-skip-permissions，不支持时回退到 bypass_permissions 模式
  qoder_cli_run --dangerously-skip-permissions "$@" ||
    qoder_cli_run --permission-mode bypass_permissions "$@"
}

function qoder_cli_dev() {
  # 交互式开发：文件编辑自动接受，其余操作需用户确认
  qoder_cli_run --permission-mode accept_edits "$@"
}

function qoder_cli_plan() {
  # 计划模式：只读分析，不执行任何修改操作
  qoder_cli_run --permission-mode default "$@"
}

function qoder_cli_auto() {
  # 自动模式：自动执行操作，减少确认交互
  qoder_cli_run --permission-mode auto "$@"
}

function qoder_cli_print() {
  # 管道非交互模式：直接输出结果
  qoder_cli_run --print "$@"
}

function qoder_cli_json() {
  # JSON 输出模式：用于程序化处理
  qoder_cli_run --print --output-format json "$@"
}

function qoder_cli_background() {
  # 后台非交互模式：脱离前台进程持续运行，前台退出不影响任务执行
  # 用法: qoder_cli_background [-m model] [-e effort] [-c context] [-l log_file] [qodercli args...] <query...>
  #   -m, --model           模型名（默认 $QODER_CLI_MODEL）
  #   -e, --effort          推理强度（默认 $QODER_CLI_EFFORT）
  #   -c, --context-window  上下文窗口大小（默认 $QODER_CLI_CONTEXT_WINDOW）
  #   -l, --log-file        日志文件路径（默认 $QODER_CLI_LOG_DIR/qoder-cli-<时间戳>.log）
  # 返回: stdout 打印后台进程 PID；完整输出追加到日志文件
  # 安全: 与 yolo 一致跳过权限检查，默认拒绝 root；导出 QODER_CLI_BACKGROUND_ALLOW_ROOT=1 放行

  if [[ "$(id -u)" -eq 0 && "${QODER_CLI_BACKGROUND_ALLOW_ROOT:-}" != "1" ]]; then
    echo "qoder_cli_background: refused to run as root user (set QODER_CLI_BACKGROUND_ALLOW_ROOT=1 to override)" >&2
    return 1
  fi

  local model="${QODER_CLI_MODEL}"
  local effort="${QODER_CLI_EFFORT}"
  local context="${QODER_CLI_CONTEXT_WINDOW}"
  local log_file=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -m|--model)           model="$2"; shift 2 ;;
      -e|--effort)          effort="$2"; shift 2 ;;
      -c|--context-window)  context="$2"; shift 2 ;;
      -l|--log-file)        log_file="$2"; shift 2 ;;
      *) break ;;
    esac
  done

  if ! mkdir -p "${QODER_CLI_LOG_DIR}"; then
    log error "qoder_cli_background: cannot create log dir ${QODER_CLI_LOG_DIR}"
    return "${RETURN_FAILURE:-1}"
  fi
  if [[ -z "${log_file}" ]]; then
    log_file="${QODER_CLI_LOG_DIR}/qoder-cli-$(date +%Y%m%d-%H%M%S)-$$.log"
  fi

  local args=(--print --dangerously-skip-permissions)
  [[ -n "${model}" ]]   && args+=(--model "${model}")
  [[ -n "${effort}" ]]  && args+=(--reasoning-effort "${effort}")
  [[ -n "${context}" ]] && args+=(--context-window "${context}")

  # 日志头：记录启动元信息，便于事后审计
  {
    echo "=== qoder_cli_background started at $(date '+%Y-%m-%d %H:%M:%S') ==="
    echo "launcher_pid: $$"
    echo "cwd: $(pwd)"
    echo "model: ${model:-<default>}  effort: ${effort:-<default>}  context_window: ${context:-<default>}"
    echo "extra_args: $*"
    echo "============================================================="
  } >> "${log_file}"

  # 双重守护：setsid 另开会话（优先），nohup 忽略 SIGHUP；stdin 脱离 tty
  # shellcheck disable=SC2086
  if have setsid; then
    setsid nohup "${QODER_CLI_BIN}" ${QODER_CLI_OPTION} "${args[@]}" "$@" </dev/null >>"${log_file}" 2>&1 &
  else
    nohup "${QODER_CLI_BIN}" ${QODER_CLI_OPTION} "${args[@]}" "$@" </dev/null >>"${log_file}" 2>&1 &
  fi
  local bg_pid=$!

  # log info 走 stderr，保证 stdout 仅输出 PID（可用 $(...) 直接捕获）
  log info "qoder_cli_background: pid=${bg_pid} log=${log_file}" >&2
  echo "${bg_pid}"
}
