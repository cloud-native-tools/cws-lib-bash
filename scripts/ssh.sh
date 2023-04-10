function ssh_local_to_remote() {
  local local_ip=127.0.0.1
  local local_port=${1}
  local remote_ip=127.0.0.1
  local remote_port=${2}
  local jumper_ip=${3}
  local jumper_port=${4:-22}
  local jumper_user=${5:-root}
  local ssh_opts="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -nNTf -L"
  if [ -z "${local_port}" -o -z "${remote_port}" -o -z "${jumper_ip}" ]; then
    echo "Usage: ssh_local_to_remote {local_port} {remote_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
  else
    ssh_kill_by_port ${local_port}
    log "ssh forward ${local_ip}:${local_port}->${jumper_user}@${jumper_ip}:${jumper_port}->${remote_ip}:${remote_port}"
    ssh ${ssh_opts} ${local_ip}:${local_port}:${remote_ip}:${remote_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
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
  local ssh_opts="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -nNTf -R"
  if [ -z "${local_port}" -o -z "${remote_port}" -o -z "${jumper_ip}" ]; then
    echo "Usage: ssh_remote_to_local {remote_port} {local_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
  else
    ssh_kill_by_port ${local_port}
    log "ssh forward ${remote_ip}:${remote_port}->${jumper_user}@${jumper_ip}:${jumper_port}->${local_ip}:${local_port}"
    ssh ${ssh_opts} ${remote_ip}:${remote_port}:${local_ip}:${local_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
  fi
}

function ssh_proxy() {
  local local_port=${1}
  local jumper_ip=${2}
  local jumper_port=${3:-22}
  local jumper_user=${4:-root}
  if [ -z "${local_port}" -o -z "${jumper_ip}" ]; then
    echo "Usage: ssh_proxy {local_port} {jumper_ip} [jumper_port=22] [jumper_user=root]"
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
    log "kill a ssh agent listen on ${port}"
    kill -9 ${ssh_pid}
  fi
}
