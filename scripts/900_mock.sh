# shellcheck shell=bash

# mock_it <target> [args...]
#
# 透明拦截一个可执行文件：先记录调用栈，再以原 argv[0] 执行 <target>.ori。
# 用法约定：把原二进制改名为 <name>.ori，再用同名包装脚本调用本函数：
#   #!/usr/bin/env bash
#   source /path/to/cws_bash_env
#   mock_it "$0" "$@"
#
# 日志目录选择顺序：MOCK_LOG_DIR > /var/log（仅 root）> ${TMPDIR:-/tmp}。
# macOS 普通用户没有 /var/log 写权限，会自动落到 TMPDIR。
function mock_it() {
  local target="${1:-}"
  if [ -z "${target}" ]; then
    log error "Usage: mock_it <target> [args...]"
    return "${RETURN_FAILURE:-1}"
  fi
  shift

  # 裸命令名经 PATH 解析，保证 <target>.ori 与目标同目录
  if [[ "${target}" != */* ]]; then
    local resolved
    resolved=$(command -v "${target}" 2>/dev/null)
    if [ -n "${resolved}" ]; then
      target="${resolved}"
    fi
  fi
  if [ ! -e "${target}" ]; then
    log error "mock_it: target not found: ${target}"
    return "${RETURN_FAILURE:-1}"
  fi

  local self_name
  self_name=$(basename "${target}")
  local ori="${target}.ori"
  if [ ! -x "${ori}" ]; then
    log error "mock_it: original binary not executable: ${ori}"
    return "${RETURN_FAILURE:-1}"
  fi

  local log_dir="${MOCK_LOG_DIR:-}"
  if [ -z "${log_dir}" ]; then
    if [ "${EUID:-$(id -u)}" -eq 0 ]; then
      log_dir=/var/log
    else
      log_dir="${TMPDIR:-/tmp}"
    fi
  fi
  if ! mkdir -p "${log_dir}" 2>/dev/null || [ ! -w "${log_dir}" ]; then
    log warn "mock_it: ${log_dir} is not writable; falling back to ${TMPDIR:-/tmp}"
    log_dir="${TMPDIR:-/tmp}"
  fi
  local mock_log="${log_dir%/}/${self_name}-mock.log"

  {
    printf '======================= %s =======\n' "$(date)"
    dump_stack
  } >>"${mock_log}" 2>&1 || log warn "mock_it: failed to write log: ${mock_log}"

  # exec -a 需要 bash >= 4；macOS 自带 bash 3.2 不支持，只能退化为普通 exec
  if [ -n "${BASH_VERSION:-}" ] && [ "${BASH_VERSINFO[0]:-0}" -ge 4 ]; then
    exec -a "${self_name}" "${ori}" "$@"
  fi
  log warn "mock_it: bash ${BASH_VERSION:-?} lacks 'exec -a'; argv[0] will not be overridden"
  exec "${ori}" "$@"
}
