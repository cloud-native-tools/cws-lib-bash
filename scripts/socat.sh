# socat debug: set SOCAT_DEBUG=1 to enable socat verbose output (-d -d)
_socat_debug_opts() { [[ "${SOCAT_DEBUG:-0}" == "1" ]] && echo "-d -d" || echo ""; }

function socat_tcp_to_unix() {
  local listen_port=${1:?"Usage: socat_tcp_to_unix <listen_port> <unix_file>"}
  local unix_file=${2:?"Usage: socat_tcp_to_unix <listen_port> <unix_file>"}

  if [[ ! -S "${unix_file}" ]]; then
    echo "[ERROR] socat_tcp_to_unix: unix socket not found: ${unix_file}" >&2
    return 1
  fi

  echo "[INFO] socat_tcp_to_unix: forwarding TCP :${listen_port} -> UNIX ${unix_file}" >&2
  # shellcheck disable=SC2046
  socat $(_socat_debug_opts) "TCP4-LISTEN:${listen_port},reuseaddr,fork" "UNIX-CLIENT:${unix_file}"
}

function socat_unix_to_tcp() {
  local unix_file=${1:?"Usage: socat_unix_to_tcp <unix_file> <target_host:port | port>"}
  local target_port=${2:?"Usage: socat_unix_to_tcp <unix_file> <target_host:port | port>"}

  if [[ -S "${unix_file}" ]]; then
    echo "[WARN] socat_unix_to_tcp: removing existing socket: ${unix_file}" >&2
    rm -f "${unix_file}"
  fi

  # parse target: if pure number, default to localhost
  if [[ "${target_port}" =~ ^[0-9]+$ ]]; then
    target_port="localhost:${target_port}"
  fi

  echo "[INFO] socat_unix_to_tcp: forwarding UNIX ${unix_file} -> TCP ${target_port}" >&2
  # shellcheck disable=SC2046
  socat $(_socat_debug_opts) "UNIX-LISTEN:${unix_file},reuseaddr,fork" "TCP4:${target_port}"
}

function socat_tcp_to_tcp() {
  local listen_addr=${1:?"Usage: socat_tcp_to_tcp [bind_addr:]<port> <target_host:port | port>"}
  local target_port=${2:?"Usage: socat_tcp_to_tcp [bind_addr:]<port> <target_host:port | port>"}

  # parse listen: support "port" or "bind:port"
  local listen_opts
  if [[ "${listen_addr}" == *:* ]]; then
    local bind_host="${listen_addr%:*}"
    local bind_port="${listen_addr##*:}"
    listen_opts="TCP4-LISTEN:${bind_port},bind=${bind_host},reuseaddr,fork"
  else
    listen_opts="TCP4-LISTEN:${listen_addr},reuseaddr,fork"
  fi

  # parse target: if pure number, default to localhost
  if [[ "${target_port}" =~ ^[0-9]+$ ]]; then
    target_port="localhost:${target_port}"
  fi

  echo "[INFO] socat_tcp_to_tcp: forwarding ${listen_addr} -> ${target_port}" >&2
  # shellcheck disable=SC2046
  socat $(_socat_debug_opts) "${listen_opts}" "TCP4:${target_port}"
}

function socat_stdin_to_unix() {
  local target_socket=${1:?"Usage: socat_stdin_to_unix <target_socket>"}

  if [[ ! -S "${target_socket}" ]]; then
    echo "[ERROR] socat_stdin_to_unix: unix socket not found: ${target_socket}" >&2
    return 1
  fi

  echo "[INFO] socat_stdin_to_unix: attaching stdin to ${target_socket} (Ctrl+Q to detach)" >&2
  socat "stdin,raw,echo=0,escape=0x11" "unix-connect:${target_socket}"
}
