# Executes an interactive shell in a Docker container
function docker_exec() {
  docker exec -it "$1" ${2:-bash}
}

# Runs a Docker container with privileged access and host network
function docker_run() {
  docker run --rm -it --privileged --network host --user root --entrypoint /bin/sh $@
}

# Removes all containers with 'Exited' status
function docker_clean_exited() {
  docker ps -a | grep Exited | awk '{print $1}' | xargs docker rm -f
}

# Prunes unused Docker resources
function docker_prune() {
  docker system prune $@
}

# Aggressively prunes all unused Docker resources
function docker_prune_all() {
  docker system prune -a $@
}

# Creates a Docker bridge network
function docker_create_network() {
  IFADDR=${1}
  ip link add docker0 type bridge
  ip addr add "${IFADDR}" dev docker0
  ip link set docker0 up
  iptables -t nat -A POSTROUTING -s "${IFADDR}" ! -d "${IFADDR}" -j MASQUERADE
  echo 1 >/proc/sys/net/ipv4/ip_forward
}

# Generates a Dockerfile from image history
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

# Lists non-dangling Docker images
function docker_images() {
  docker images --filter "dangling=false"
}

# Shorthand function for docker-compose
function dp() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose $@
  fi

  if docker compose version >/dev/null 2>&1; then
    docker compose $@
  fi
}

# Starts Docker Compose services in detached mode
function dp_up() {
  dp up -d --compatibility --remove-orphans $@
}

# Recreates Docker Compose services
function dp_recreate() {
  dp up -d --force-recreate --no-deps $@
}

# Lists Docker Compose services
function dp_svc() {
  dp ps --services
}

# Extracts files from a Docker image to a destination directory
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

# Displays Docker containers with enhanced formatting
function docker_ps() {
  docker ps -a --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\n{{if .Ports}}{{with $p := split .Ports ", "}}{{range $p}}\t{{println .}}{{end}}{{end}}{{else}}\t\t{{println "No Ports"}}{{end}}'
}

# Lists only the names of running Docker containers
function docker_names() {
  docker ps | awk '{print $NF}' | grep -v NAMES
}

# Displays logs from a Docker container
function docker_logs() {
  local cid=${1}
  if [ -z "${cid}" ]; then
    log error "Usage: docker_logs <container_id>"
    return ${RETURN_FAILURE}
  else
    shift
  fi
  docker logs ${cid} $@ 2>&1
}

# Displays and parses OpenTelemetry logs from a Docker container
function docker_otlp_logs() {
  local cid=${1}
  if [ -z "${cid}" ]; then
    log error "Usage: docker_otlp_logs <container_id>"
    return ${RETURN_FAILURE}
  else
    shift
  fi
  docker_logs ${cid} $@ | grep '{"resourceLogs"' | parse_otlp_logs
}

# Parses OpenTelemetry logs into a human-readable format
function parse_otlp_logs() {
  cat >/tmp/otlp.jq <<EOF
# otlp-log-filter.jq
.resourceLogs[]?.scopeLogs[]?.logRecords[]? |
[
    (.attributes[]? | select(.key == "from").value.stringValue // "unknown"),
    (.observedTimeUnixNano | tonumber / 1e9 | strftime("%Y-%m-%dT%H:%M:%SZ")),
    .body.stringValue
] | join(" | ")
EOF
  jq -r -f /tmp/otlp.jq | column -t -s "|"
}
