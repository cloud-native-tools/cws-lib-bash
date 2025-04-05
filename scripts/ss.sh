# Socket Statistics (ss) utility functions

# Lists all Unix domain sockets with absolute addresses
function ss_unix_abs() {
  # List all Unix domain sockets with absolute addresses
  ss -xp | grep -E "^u_str.*path=/" $@
}

# Lists all Unix domain sockets
function ss_unix_all() {
  # List all Unix domain sockets
  ss -xp $@
}

# Lists TCP sockets
function ss_tcp() {
  # List TCP sockets
  ss -tp $@
}

# Lists UDP sockets
function ss_udp() {
  # List UDP sockets
  ss -up $@
}

# Shows all listening sockets
function ss_listening() {
  # Show all listening sockets
  ss -l $@
}

# Shows established connections
function ss_established() {
  # Show established connections
  ss -o state established $@
}

# Shows sockets used by a specific process
function ss_process() {
  # Show sockets used by a specific process
  local process_name=$1
  if [ -z "${process_name}" ]; then
    echo "Usage: ss_process <process_name>"
    return 1
  fi
  ss -p | grep ${process_name}
}

# Shows sockets using a specific port
function ss_port() {
  # Show sockets using a specific port
  local port=$1
  if [ -z "${port}" ]; then
    echo "Usage: ss_port <port_number>"
    return 1
  fi
  ss -tuln sport = :${port} or dport = :${port}
}

# Finds Unix socket by path pattern
function ss_find_socket_by_path() {
  # Find Unix socket by path pattern
  local path_pattern=$1
  if [ -z "${path_pattern}" ]; then
    echo "Usage: ss_find_socket_by_path <path_pattern>"
    return 1
  fi
  ss -xp | grep -E "path=${path_pattern}"
}

# Shows socket statistics summary
function ss_summary() {
  # Show socket statistics summary
  echo "=== Socket Summary ==="
  echo "TCP sockets: $(ss -t | wc -l)"
  echo "UDP sockets: $(ss -u | wc -l)"
  echo "Unix sockets: $(ss -x | wc -l)"
  echo "Listening sockets: $(ss -l | wc -l)"
  echo "Established connections: $(ss -o state established | wc -l)"
}
