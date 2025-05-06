# Creates an SSH tunnel from local port to remote port through a jump host
function ssh_local_to_remote() {
  local local_ip=127.0.0.1
  local local_port=${1}
  local remote_ip=127.0.0.1
  local remote_port=${2}
  local jumper_ip=${3}
  local jumper_port=${4}
  local jumper_user=${5}
  if [ -z "${local_port}" -o -z "${remote_port}" -o -z "${jumper_ip}" ]; then
    log plain "Usage: ssh_local_to_remote {local_port} {remote_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
  else
    ssh_kill_by_port ${local_port}
    log "ssh forward ${local_ip}:${local_port}->${jumper_user}@${jumper_ip}:${jumper_port}->${remote_ip}:${remote_port}"
    if [ -z "${jumper_user}" ] || [ -z "${jumper_user}" ]; then
      ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
        -nNTf \
        -L ${local_ip}:${local_port}:${remote_ip}:${remote_port} \
        ${jumper_ip}
    else
      ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
        -nNTf \
        -L ${local_ip}:${local_port}:${remote_ip}:${remote_port} \
        -p ${jumper_port} \
        ${jumper_user}@${jumper_ip}
    fi
  fi
}

# Creates an SSH tunnel from remote port to local port through a jump host
function ssh_remote_to_local() {
  local remote_ip=127.0.0.1
  local remote_port=${1}
  local local_ip=127.0.0.1
  local local_port=${2}
  local jumper_ip=${3}
  local jumper_port=${4}
  local jumper_user=${5}
  local key_file=${6:-~/.ssh/id_rsa}
  if [ -z "${local_port}" -o -z "${remote_port}" -o -z "${jumper_ip}" ]; then
    log plain "Usage: ssh_remote_to_local {remote_port} {local_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
  else
    ssh_kill_by_port ${local_port}
    log "ssh forward ${remote_ip}:${remote_port}->${jumper_user}@${jumper_ip}:${jumper_port}->${local_ip}:${local_port}"
    if [ -z "${jumper_user}" ] || [ -z "${jumper_user}" ]; then
      ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
        -nNTf \
        -R ${remote_ip}:${remote_port}:${local_ip}:${local_port} \
        ${jumper_ip}
    else
      ssh -i ${key_file} \
        -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
        -nNTf \
        -R ${remote_ip}:${remote_port}:${local_ip}:${local_port} \
        -p ${jumper_port} \
        ${jumper_user}@${jumper_ip}
    fi
  fi
}

# Creates an SSH proxy on a local port through a jump host
function ssh_proxy() {
  local local_port=${1}
  local jumper_ip=${2}
  local jumper_port=${3:-22}
  local jumper_user=${4:-root}
  if [ -z "${local_port}" -o -z "${jumper_ip}" ]; then
    log plain "Usage: ssh_proxy {local_port} {jumper_ip} [jumper_port=22] [jumper_user=root]\n"
  else
    ssh_kill_by_port ${local_port}
    log "ssh proxy :${local_port}->${jumper_user}@${jumper_ip}:${jumper_port}->*"
    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -nNTf -D ${local_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
  fi
}

# Kills an SSH process listening on a specific port
function ssh_kill_by_port() {
  local port=${1}
  local ssh_pid=$(lsof -i -n -P | grep LISTEN | grep ${port} -w | grep ssh -w | tr -s ' ' | cut -d' ' -f2)
  if [ -n "${ssh_pid}" ]; then
    log warn "kill a ssh agent [${ssh_pid}] listen on [${port}]"
    kill -15 ${ssh_pid}
  fi
}

# Generates an SSH host configuration
function ssh_add_host_config() {
  local host=${1}
  local port=${2:-22}
  local name=${3:-${host}}
  local user=${4:-root}
  local key=${5:-~/.ssh/id_rsa}
  echo "Host ${name}"
  echo "  Hostname ${host}"
  echo "  Port ${port}"
  echo "  User ${user}"
  echo "  IdentityFile ${key}"
  echo "  ServerAliveInterval 5"
  echo "  UserKnownHostsFile /dev/null"
  echo "  StrictHostKeyChecking no"
}

# Waits for an SSH node to be ready
function ssh_wait_node_ready() {
  local name=${1}
  local timeout=${2}
  local config_file=${3:-ssh/config}

  local success_count=0
  local wait_time=0

  while true; do
    ssh -o BatchMode=yes -o ConnectTimeout=1 -F ${config_file} -t -q ${name} echo 1
    if [ $? -eq 0 ]; then
      if [ ${success_count} -lt 5 ]; then
        echo "${name} success count: ${success_count}"
        ((success_count++))
      else
        echo "${name} is ready, elapsed time: ${wait_time}s"
        exit 0
      fi
    elif [ ${wait_time} -ge ${timeout} ]; then
      echo "echo ${name} is not ready after ${wait_time}s and timeout, exit"
      exit 1
    else
      echo "echo ${name} is not ready after ${wait_time}s, keep waiting..."
    fi
    sleep 1
    ((wait_time++))
  done
}

# Generates an SSH key pair
function ssh_generate_key() {
  local email=${1}
  local passphrase=${2:-""}
  local key_file=${3:-./id_rsa}
  if [ -z "${email}" ]; then
    log error "Usage: ssh_generate_key {email} [passphrase] [key_file=./id_rsa]"
    return ${RETURN_FAILURE}
  fi
  ssh-keygen -t rsa -b 4096 -f ${key_file} -C "${email}" -N "${passphrase}"
  chmod 400 ${key_file} ${key_file}.pub
}

# Fixes permissions for SSH-related files
function ssh_fix_permission() {
  local target=${1:-${PWD}}
  find ${target} \( -name id_rsa -o -name id_rsa.pub -o -name authorized_keys -o -name known_hosts \) | xargs chmod 400
}

# Pings an SSH host
function ssh_ping() {
  local host_name=${1}
  local config_file=${2}
  if [ -z "${host_name}" ]; then
    return ${RETURN_FAILURE}
  else
    shift
  fi
  if [ -z "${config_file}" ]; then
    config_file=~/.ssh/config
  else
    shift
  fi
  if ssh -o ConnectTimeout=5 -F ${config_file} ${host_name} $@ exit >/dev/null 2>&1; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

# Logs into an SSH host using expect
function ssh_expect_login() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-root}
  if [ -z "${host}" ]; then
    log error "Usage: ssh_expect_login <host> [port] [user]"
    return ${RETURN_FAILURE}
  fi
  if ! have expect; then
    log error "[expect] is required, use 'yum install expect' or 'apt-get install expect' to install it."
    return ${RETURN_FAILURE}
  fi
  if [ -z "${SSH_EXPECT_PASSWORD}" ]; then
    log warn "SSH_EXPECT_PASSWORD is not set, using prompt to input password."
    echo -n "Enter your password: "
    read -s password
  else
    local password="${SSH_EXPECT_PASSWORD}"
  fi

  if [ -z "${password}" ]; then
    log error "Password is required."
    return ${RETURN_FAILURE}
  fi
  expect -f ${CWS_LIB_BASH_HOME}/expect/login.expect \
    ${host} \
    ${port} \
    ${user} \
    "${password}"
}

# Adds an SSH key to an authorized_keys file on a remote host using expect
function ssh_expect_add_auth_key() {
  local host=${1}
  local port=${2:-22}
  local user=${3:-root}
  local keyfile=${4:-~/.ssh/id_rsa.pub}
  if [ -z "${host}" ]; then
    log error "Usage: ssh_expect_add_auth_key {host} [port=22] [user=root] [keyfile=~/.ssh/id_rsa.pub]"
    return ${RETURN_FAILURE}
  fi
  if ! have expect; then
    log error "[expect] is required, use 'yum install expect' or 'apt-get install expect' to install it."
    return ${RETURN_FAILURE}
  fi
  if [ ! -f "${keyfile}" ]; then
    log error "Keyfile ${keyfile} does not exist."
    return ${RETURN_FAILURE}
  fi

  if [ -z "${SSH_EXPECT_PASSWORD}" ]; then
    log warn "SSH_EXPECT_PASSWORD is not set, using prompt to input password."
    echo -n "Enter your password: "
    read -s password
  else
    local password="${SSH_EXPECT_PASSWORD}"
  fi
  if [ -z "${password}" ]; then
    log error "Password is required."
    return ${RETURN_FAILURE}
  fi
  local cmd=$(
    cat <<EOF
sudo bash -c \"echo '$(cat ${keyfile})' >> /root/.ssh/authorized_keys\"
EOF
  )
  expect -f ${CWS_LIB_BASH_HOME}/expect/cmd.expect \
    ${host} \
    ${port} \
    ${user} \
    "${password}" \
    "${cmd}" ||
    {
      log error "Failed to add SSH key for ${host}."
      return ${RETURN_FAILURE}
    }
  log info "SSH key added successfully for ${host}."
  return ${RETURN_SUCCESS}
}
