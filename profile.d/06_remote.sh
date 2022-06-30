function remote_get_hosts() {
    local hosts_file=${1:-~/remote_hosts}
    if [ -z "${REMOTE_HOSTS}" ]; then
        cat ${hosts_file}
    else
        echo ${REMOTE_HOSTS}
    fi
}

function remote_deploy() {
    local dest=$1
    shift
    local src=$@
    for host in $(remote_get_hosts); do
        echo "Deploy [$src] to $host:${dest}"
        scp $src ${host}:$dest
    done
}

function remote_cmd() {
    for host in $(remote_get_hosts); do
        echo "Run on [$host]: [$@]"
        ssh -t $host -- "bash -l -c '$@'"
    done
}
