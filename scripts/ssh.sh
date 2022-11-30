function ssh_local_to_remote() {
  local local_port=${1}
  local remote_port=${2}
  local jumper_ip=${3}
  local jumper_port=${4:-22}
  local jumper_user=${5:-root}
  ssh -nNT -L 127.0.0.1:${local_port}:127.0.0.1:${remote_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
}

function ssh_proxy() {
  local local_port=${1}
  local jumper_ip=${2}
  local jumper_port=${3:-22}
  local jumper_user=${4:-root}
  ssh -nNT -D ${local_port} -p ${jumper_port} ${jumper_user}@${jumper_ip}
}
