function remote_get_hosts() {
    local hosts_file_root="${HOME}/.remote"
    local hosts_file=${1:-remote_hosts}
    if ! cat ${hosts_file_root}/${hosts_file}; then
        log error "$? cannot find ${hosts_file_root}/${hosts_file}"
    fi
}

function remote_deploy() {
    local dest=$1
    shift
    local src=$@
    for host in $(remote_get_hosts); do
        echo "Deploy [${src}] to ${host}:${dest}"
        scp -r ${src} ${host}:${dest}
    done
}

function remote_cmd() {
    for host in $(remote_get_hosts); do
        echo "Run on [${host}]: [$@]"
        echo "---"
        ssh -t -q ${host} -- "bash -l -c '$@'"
        echo "---"
    done
}

function remote_cmd_expect() {
    local password=$1
    shift
    for host in $(remote_get_hosts); do
        echo "Run on [${host}]: [$@]"
        echo "---"
        expect <<-EOF
    spawn ssh -t -q ${host} -- "bash -l -c '$@'"
    expect '*password:'
    send '${password}\r'
EOF
        echo "---"
    done

}

function remote_sync_hostname() {
    for host in $(remote_get_hosts); do
        echo "Run on [${host}]: [$@]"
        echo "---"
        ssh -t -q ${host} -- "echo ${host} > /etc/hostname; hostname ${host}; hostname"
        echo "---"
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
            echo "Get ${host}:${target} ${root}"
            mkdir -pv $(dirname ${root}/${host}/${target})
            scp -r ${host}:${target} ${root}/${host}/${target}
        done
    else
        echo "Usage: remote_download <abs path> "
    fi
}
