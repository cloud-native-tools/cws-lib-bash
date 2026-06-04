function socat_tcp_to_unix() {
  local listen_port=${1:?"Usage: socat_tcp_to_unix <listen_port> <unix_file>"}
  local unix_file=${2:?"Usage: socat_tcp_to_unix <listen_port> <unix_file>"}

  if [[ ! -S "${unix_file}" ]]; then
    echo "[ERROR] socat_tcp_to_unix: unix socket not found: ${unix_file}" >&2
    return 1
  fi

  echo "[INFO] socat_tcp_to_unix: forwarding TCP :${listen_port} -> UNIX ${unix_file}" >&2
  socat -d "TCP4-LISTEN:${listen_port},reuseaddr,fork" "UNIX-CLIENT:${unix_file}"
}

function socat_unix_to_tcp() {
  local unix_file=${1:?"Usage: socat_unix_to_tcp <unix_file> <listen_port>"}
  local listen_port=${2:?"Usage: socat_unix_to_tcp <unix_file> <listen_port>"}

  if [[ -S "${unix_file}" ]]; then
    echo "[WARN] socat_unix_to_tcp: removing existing socket: ${unix_file}" >&2
    rm -f "${unix_file}"
  fi

  echo "[INFO] socat_unix_to_tcp: forwarding UNIX ${unix_file} -> TCP localhost:${listen_port}" >&2
  socat -d "UNIX-LISTEN:${unix_file},reuseaddr,fork" "TCP4:localhost:${listen_port}"
}

function socat_tcp_to_tcp() {
  local listen_port=${1:?"Usage: socat_tcp_to_tcp <listen_port> <target_host:port>"}
  local target_port=${2:?"Usage: socat_tcp_to_tcp <listen_port> <target_host:port>"}

  echo "[INFO] socat_tcp_to_tcp: forwarding TCP :${listen_port} -> TCP ${target_port}" >&2
  socat -d "TCP4-LISTEN:${listen_port},reuseaddr,fork" "TCP4:${target_port}"
}

function socat_stdin_to_unix() {
  local target_socket=${1:?"Usage: socat_stdin_to_unix <target_socket>"}

  if [[ ! -S "${sock_path}" ]]; then
    echo "[ERROR] socat_stdin_to_unix: unix socket not found: ${sock_path}" >&2
    return 1
  fi

  echo "[INFO] socat_stdin_to_unix: attaching stdin to ${target_socket} (Ctrl+Q to detach)" >&2
  socat "stdin,raw,echo=0,escape=0x11" "unix-connect:${target_socket}"
}
