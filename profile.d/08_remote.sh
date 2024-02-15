export REMOTE_HOSTS_FILE="${HOME}/.remote/remote_hosts"
export SSH_CONFIG_FILE="${HOME}/.ssh/config"

function remote_get_hosts() {
  if [ -f remote.rc ]; then
    . remote.rc
  fi
  local hosts_file=${1:-${REMOTE_HOSTS_FILE}}
  if ! cat ${hosts_file}; then
    log error "$? cannot find ${hosts_file}"
  fi
}

function remote_upload() {
  local dest=$1
  shift
  local src=$@
  if [ -z "${dest}" ] || [ -z "${src}" ]; then
    log warn "Usage: remote_upload <dest> <src1> [src2] ..."
    return ${RETURN_FAILURE}
  fi
  for host in $(remote_get_hosts); do
    log info "Deploy [${src}] to ${host}:${dest}"
    scp -F ${SSH_CONFIG_FILE} -r ${src} ${host}:${dest}
  done
}

function remote_cmd() {
  for host in $(remote_get_hosts); do
    log plain "Run on [${host}]: [$@]"
    log plain "---"
    ssh -t -q ${host} -F ${SSH_CONFIG_FILE} -- "bash -l -c '$@';echo \"Exit Code: $?\""
    log plain "---"
  done
}

function remote_cmd_expect() {
  local password=$1
  shift
  for host in $(remote_get_hosts); do
    log plain "Run on [${host}]: [$@]"
    log plain "---"
    expect <<-EOF
    spawn ssh -t -q ${host} -F ${SSH_CONFIG_FILE} -- "bash -l -c '$@'"
    expect '*password:'
    send '${password}\r'
EOF
    log plain "---"
  done

}

function remote_sync_hostname() {
  for host in $(remote_get_hosts); do
    log plain "Run on [${host}]: [$@]"
    log plain "---"
    ssh -t -q ${host} -F ${SSH_CONFIG_FILE} -- "echo ${host} > /etc/hostname; hostname ${host}; hostname"
    log plain "---"
  done
}

function remote_download() {
  local target=${1}
  local root=${2}
  if [ -n "${target}" ]; then
    if [ -z "${root}" ]; then
      root=.
    fi
    for host in $(remote_get_hosts); do
      log info "Get ${host}:${target} ${root}"
      mkdir -pv $(dirname ${root}/${host}/${target})
      scp -F ${SSH_CONFIG_FILE} -r ${host}:${target} ${root}/${host}/${target}
    done
  else
    log warn "Usage: remote_download <abs path> "
  fi
}
