# Check if expect is available
function expect_check_available() {
  if ! command -v expect &>/dev/null; then
    log error "expect command not found. Please install expect package."
    return ${RETURN_FAILURE}
  fi
  return ${RETURN_SUCCESS}
}

# Generate a dynamic expect script for running a command on a remote host
function expect_generate_cmd_script() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-$USER}
  local password=${4}
  local cmd=${5}

  if [ -z "${host}" ] || [ -z "${password}" ] || [ -z "${cmd}" ]; then
    log error "Usage: expect_generate_cmd_script <host> [port] [user] <password> <cmd>"
    return ${RETURN_FAILURE}
  fi

  local script_content
  script_content=$(
    cat <<EOF
#!/usr/bin/expect

set timeout -1

trap {
  set rows [stty rows]
  set cols [stty columns]
  stty rows \$rows columns \$cols < \$spawn_out(slave,name)
 } WINCH

set host "${host}"
set port "${port}"
set user "${user}"
set password "${password}"
set cmd "${cmd}"
spawn ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -p \$port \$user@\$host
expect "*assword:" {
  send "\$password\r"
}
expect "\\\[*@" {
  send "\$cmd\r"
}
expect "\\\[*@" {
  send "exit\r"
  expect eof
}
EOF
  )
  echo "${script_content}"
  return ${RETURN_SUCCESS}
}

# Generate a dynamic expect script for interactive login to a remote host
function expect_generate_login_script() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-$USER}
  local password=${4}

  if [ -z "${host}" ] || [ -z "${password}" ]; then
    log error "Usage: expect_generate_login_script <host> [port] [user] <password>"
    return ${RETURN_FAILURE}
  fi

  local script_content
  script_content=$(
    cat <<EOF
#!/usr/bin/expect

set timeout -1

trap {
  set rows [stty rows]
  set cols [stty columns]
  stty rows \$rows columns \$cols < \$spawn_out(slave,name)
 } WINCH

set host "${host}"
set port "${port}"
set user "${user}"
set password "${password}"
spawn ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -p \$port \$user@\$host
expect "*assword:" {
  send "\$password\r"
}
interact {
  eof {
    exit
  }
}
EOF
  )
  echo "${script_content}"
  return ${RETURN_SUCCESS}
}

# Execute a command on a remote host using expect
function expect_execute_cmd() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-$USER}
  local password=${4}
  local cmd=${5}

  if [ -z "${host}" ] || [ -z "${password}" ] || [ -z "${cmd}" ]; then
    log error "Usage: expect_execute_cmd <host> [port] [user] <password> <cmd>"
    return ${RETURN_FAILURE}
  fi

  # Check if expect is available
  if ! expect_check_available; then
    return ${RETURN_FAILURE}
  fi

  local temp_script
  temp_script=$(mktemp)

  expect_generate_cmd_script "${host}" "${port}" "${user}" "${password}" "${cmd}" >"${temp_script}"
  chmod +x "${temp_script}"

  # Execute the script
  "${temp_script}"
  local exit_code=$?

  # Clean up
  rm -f "${temp_script}"

  return ${exit_code}
}

# Login to a remote host using expect
function expect_login() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-$USER}
  local password=${4}

  if [ -z "${host}" ] || [ -z "${password}" ]; then
    log error "Usage: expect_login <host> [port] [user] <password>"
    return ${RETURN_FAILURE}
  fi

  # Check if expect is available
  if ! expect_check_available; then
    return ${RETURN_FAILURE}
  fi

  local temp_script
  temp_script=$(mktemp)

  expect_generate_login_script "${host}" "${port}" "${user}" "${password}" >"${temp_script}"
  chmod +x "${temp_script}"

  # Execute the script
  "${temp_script}"
  local exit_code=$?

  # Clean up
  rm -f "${temp_script}"

  return ${exit_code}
}

# Execute a command on a remote host using the static expect script
function expect_static_cmd() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-$USER}
  local password=${4}
  local cmd=${5}

  if [ -z "${host}" ] || [ -z "${password}" ] || [ -z "${cmd}" ]; then
    log error "Usage: expect_static_cmd <host> [port] [user] <password> <cmd>"
    return ${RETURN_FAILURE}
  fi

  # Check if expect is available
  if ! expect_check_available; then
    return ${RETURN_FAILURE}
  fi

  # Locate the expect script
  local script_path
  script_path="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../expect/cmd.expect"

  if [ ! -f "${script_path}" ]; then
    log error "Static expect script not found at ${script_path}"
    return ${RETURN_FAILURE}
  fi

  # Execute the script
  expect "${script_path}" "${host}" "${port}" "${user}" "${password}" "${cmd}"
  return $?
}

# Login to a remote host using the static expect script
function expect_static_login() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-$USER}
  local password=${4}

  if [ -z "${host}" ] || [ -z "${password}" ]; then
    log error "Usage: expect_static_login <host> [port] [user] <password>"
    return ${RETURN_FAILURE}
  fi

  # Check if expect is available
  if ! expect_check_available; then
    return ${RETURN_FAILURE}
  fi

  # Locate the expect script
  local script_path
  script_path="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../expect/login.expect"

  if [ ! -f "${script_path}" ]; then
    log error "Static expect script not found at ${script_path}"
    return ${RETURN_FAILURE}
  fi

  # Execute the script
  expect "${script_path}" "${host}" "${port}" "${user}" "${password}"
  return $?
}
