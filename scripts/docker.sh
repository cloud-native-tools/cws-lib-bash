function docker_exec() {
  docker exec -it "$1" ${2:-bash}
}

function docker_run() {
  docker run --rm -it --privileged --network host --user root --entrypoint /bin/sh $@
}

function docker_clean_exited() {
  docker ps -a | grep Exited | awk '{print $1}' | xargs docker rm -f
}

function docker_prune() {
  docker system prune -a
}

function docker_create_network() {
  IFADDR=${1}
  ip link add docker0 type bridge
  ip addr add "${IFADDR}" dev docker0
  ip link set docker0 up
  iptables -t nat -A POSTROUTING -s "${IFADDR}" ! -d "${IFADDR}" -j MASQUERADE
  echo 1 >/proc/sys/net/ipv4/ip_forward
}

function docker_generate_dockerfile() {
  local img=$1
  docker history --no-trunc ${img} |
    tac |
    tr -s ' ' |
    cut -d " " -f 5- |
    sed 's,^/bin/sh -c #(nop) ,,g' |
    sed 's,^/bin/sh -c,RUN,g' |
    sed 's, && ,\n  & ,g' |
    sed 's,\s*[0-9]*[\.]*[0-9]*\s*[kMG]*B\s*$,,g' |
    head -n -1
}

function docker_images() {
  docker images --filter "dangling=false"
}

function dp() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose $@
  fi

  if docker compose version >/dev/null 2>&1; then
    docker compose $@
  fi
}

function dp_up() {
  dp up -d --compatibility --remove-orphans $@
}

function dp_recreate() {
  dp up -d --force-recreate --no-deps $@
}

function dp_svc() {
  dp ps --services
}

function docker_import_env() {
  local docker_file=${1}
  grep -w "ENV" ${docker_file} | sed -E 's/^ *ENV \+\([^ ]\+\) \(.*\)/export \1="\2"/g'
}

function docker_extract() {
  local img=${1}
  local dest=${2:-${PWD}/rootfs}
  if [ -z "${img}" ]; then
    log warn "Usage: docker_extract <image> [dest=${PWD}]"
    return ${RETURN_FAILURE}
  else
    local cid=$(docker create --entrypoint 'sleep 99999' ${img})
    mkdir -pv ${dest}
    docker export ${cid} | tar -xC ${dest}
    docker rm -f ${cid}
    return ${RETURN_SUCCESS}
  fi
}

function docker_ps() {
  docker ps -a --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\n{{if .Ports}}{{with $p := split .Ports ", "}}{{range $p}}\t{{println .}}{{end}}{{end}}{{else}}\t\t{{println "No Ports"}}{{end}}'
}

function docker_names() {
  docker ps | awk '{print $NF}' | grep -v NAMES
}
