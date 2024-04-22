function ssh_local_to_remote() {
  local local_ip=127.0.0.1
  local local_port=${1}
  local remote_ip=127.0.0.1
  local remote_port=${2}
  local jumper_ip=${3}
  local jumper_port=${4:-22}
  local jumper_user=${5:-root}
  if [ -z "${local_port}" -o -z "${remote_port}" -o -z "${jumper_ip}" ]; then
    log plain "Usage: ssh_local_to_remote {local_port} {remote_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
  else
    ssh_kill_by_port ${local_port}
    log "ssh forward ${local_ip}:${local_port}->${jumper_user}@${jumper_ip}:${jumper_port}->${remote_ip}:${remote_port}"
    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -nNTf -L ${local_ip}:${local_port}:${remote_ip}:${remote_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
  fi
}

function ssh_remote_to_local() {
  local remote_ip=127.0.0.1
  local remote_port=${1}
  local local_ip=127.0.0.1
  local local_port=${2}
  local jumper_ip=${3}
  local jumper_port=${4:-22}
  local jumper_user=${5:-root}
  local key_file=${6:-~/.ssh/id_rsa}
  if [ -z "${local_port}" -o -z "${remote_port}" -o -z "${jumper_ip}" ]; then
    log plain "Usage: ssh_remote_to_local {remote_port} {local_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
  else
    ssh_kill_by_port ${local_port}
    log "ssh forward ${remote_ip}:${remote_port}->${jumper_user}@${jumper_ip}:${jumper_port}->${local_ip}:${local_port}"
    ssh -i ${key_file} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -nNTf -R ${remote_ip}:${remote_port}:${local_ip}:${local_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
  fi
}

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

function ssh_kill_by_port() {
  local port=${1}
  local ssh_pid=$(lsof -i -n -P | grep LISTEN | grep ${port} -w | grep ssh -w | tr -s ' ' | cut -d' ' -f2)
  if [ -n "${ssh_pid}" ]; then
    log warn "kill a ssh agent [${ssh_pid}] listen on [${port}]"
    kill -15 ${ssh_pid}
  fi
}

function ssh_host_config() {
  local host=${1}
  local port=${2:-22}
  local name=${3:-${host}}
  local user=${4:-root}
  local key=${5:-~/.ssh/id_rsa}
  echo "Host ${name}"
  echo "  HostName ${host}"
  echo "  Port ${port}"
  echo "  User ${user}"
  echo "  IdentityFile ${key}"
  echo "  ServerAliveInterval 5"
  echo "  PubkeyAcceptedAlgorithms +ssh-rsa"
  echo "  UserKnownHostsFile /dev/null"
  echo "  StrictHostKeyChecking no"
}

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

function ssh_generate_key() {
  local email=${1}
  local passphrase=${2:-""}
  local key_file=${3:-./id_rsa}
  if [ -z "${email}" ]; then
    log error "Usage: ssh_generate_key {email} [passphrase] [key_file=./id_rsa]"
    return ${RETURN_FAILURE}
  fi
  ssh-keygen -t rsa -b 4096 -f ${key_file} -C "${email}" -N "${passphrase}"
}
