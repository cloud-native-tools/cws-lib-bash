# Executes an interactive shell in a Docker container
function docker_exec() {
  docker exec -i "$1" ${2:-bash}
}

function docker_login() {
  docker exec -it "$1" ${2:-bash}
}

# Resolve a host user's home directory (getent on Linux, dscl on macOS).
function _docker_cp_host_home() {
  local user=$1
  if command -v getent >/dev/null 2>&1; then
    getent passwd "${user}" 2>/dev/null | cut -d: -f6
  elif is_macos; then
    dscl . -read "/Users/${user}" NFSHomeDirectory 2>/dev/null | awk '{print $2}'
  fi
}

# Expand a literal leading "~" in <path> against <home>; other paths pass through.
function _docker_cp_expand_home() {
  local path=$1
  local home=$2
  case "${path}" in
    '~') echo "${home}" ;;
    '~/'*) echo "${home}/${path#\~/}" ;;
    *) echo "${path}" ;;
  esac
}

# Copies a host directory or file into a running Docker container. --dest-dir
# is the full target path inside the container -- not a parent directory -- so
# `--src-dir '~/.ssh' --dest-user develop` lands the contents at develop's
# ~/.ssh. The target is created when missing and merged when it already exists;
# the payload travels as a base64 tar (encode_files) and the result is handed
# to --dest-user via chown -R (the extraction runs as the exec user -- root by
# default -- so without it the copy would stay root-owned and break e.g. sshd
# StrictModes).
#
# A literal leading "~" resolves per user: against --src-user's home on the
# host, against --dest-user's home inside the container -- so the same "~/.ssh"
# means different homes when the two users differ. Bash only leaves "~" literal
# when the value is quoted; an unquoted ~user/... is expanded by the caller's
# shell before the function sees it.
#
# Usage: docker_cp <container> --src-dir DIR [--src-user USER]
#                  [--dest-dir DIR] [--dest-user USER]
#   --src-dir   host path to copy (required); ~ / ~/... resolves for --src-user
#   --src-user  host user (default: root)
#   --dest-dir  full target path in the container (default: the --src-dir
#               value, with ~ re-resolved for --dest-user)
#   --dest-user container user that owns the result (default: root)
#
# Example - copy the host agent user's ~/.ssh to develop's ~/.ssh:
#   docker_cp xuanji-ai-sre-dev-xuanji-skills-1 \
#     --src-user agent --dest-user develop --src-dir '~/.ssh'
function docker_cp() {
  local container=${1:-}
  local src_user=root src_dir="" dest_user=root dest_dir=""
  local src_home dest_home src_name dest_parent dest_name

  if [ $# -gt 0 ]; then shift; fi
  while [ $# -gt 0 ]; do
    case "$1" in
      --src-dir) shift; src_dir=${1:-} ;;
      --src-user) shift; src_user=${1:-root} ;;
      --dest-dir) shift; dest_dir=${1:-} ;;
      --dest-user) shift; dest_user=${1:-root} ;;
      -h | --help)
        log error "Usage: docker_cp <container> --src-dir DIR [--src-user USER] [--dest-dir DIR] [--dest-user USER]"
        return ${RETURN_FAILURE}
        ;;
      *)
        log error "docker_cp: unknown option: $1"
        return ${RETURN_FAILURE}
        ;;
    esac
    if [ $# -gt 0 ]; then shift; fi
  done

  if [ -z "${container}" ] || [ -z "${src_dir}" ]; then
    log error "Usage: docker_cp <container> --src-dir DIR [--src-user USER] [--dest-dir DIR] [--dest-user USER]"
    return ${RETURN_FAILURE}
  fi

  # --dest-dir defaults to the same literal value as --src-dir, so a "~" in it
  # re-resolves against --dest-user's home instead of --src-user's.
  dest_dir=${dest_dir:-${src_dir}}

  case "${src_dir}" in
    '~' | '~/'*)
      src_home=$(_docker_cp_host_home "${src_user}")
      if [ -z "${src_home}" ]; then
        log error "docker_cp: host user not found: ${src_user}"
        return ${RETURN_FAILURE}
      fi
      src_dir=$(_docker_cp_expand_home "${src_dir}" "${src_home}")
      ;;
  esac
  if [ ! -e "${src_dir}" ]; then
    log error "docker_cp: source does not exist: ${src_dir}"
    return ${RETURN_FAILURE}
  fi

  # dest_user must exist in the container: it resolves "~" in --dest-dir and
  # owns the result. This call also fails early on a wrong container name.
  dest_home=$(docker exec "${container}" getent passwd "${dest_user}" 2>/dev/null | cut -d: -f6)
  if [ -z "${dest_home}" ]; then
    log error "docker_cp: cannot resolve dest user '${dest_user}' in container '${container}' (unknown user or container not running)"
    return ${RETURN_FAILURE}
  fi
  dest_dir=$(_docker_cp_expand_home "${dest_dir}" "${dest_home}")

  src_name=$(basename "${src_dir}")
  if [ -d "${src_dir}" ]; then
    # directory: stream its contents into dest_dir
    {
      echo "set -e; mkdir -p ${dest_dir}; cd ${dest_dir}"
      (cd "${src_dir}" && encode_files .)
      echo "chown -R ${dest_user}:${dest_user} . 2>/dev/null || chown -R ${dest_user} ."
    } | docker_exec "${container}" bash
  else
    # single file: land it at dest_dir, renaming when the basenames differ
    dest_parent=$(dirname "${dest_dir}")
    dest_name=$(basename "${dest_dir}")
    {
      echo "set -e; mkdir -p ${dest_parent}; cd ${dest_parent}"
      (cd "$(dirname "${src_dir}")" && encode_files "${src_name}")
      if [ "${src_name}" != "${dest_name}" ]; then
        echo "mv ${src_name} ${dest_name}"
      fi
      echo "chown -R ${dest_user}:${dest_user} ${dest_name} 2>/dev/null || chown -R ${dest_user} ${dest_name}"
    } | docker_exec "${container}" bash
  fi

  local rc=$?
  if [ ${rc} -ne 0 ]; then
    log error "docker_cp: failed (rc=${rc}): ${src_dir} -> ${container}:${dest_dir}"
    return ${RETURN_FAILURE}
  fi

  log notice "docker_cp: ${src_dir} (${src_user}) -> ${container}:${dest_dir} (${dest_user})"
  return ${RETURN_SUCCESS}
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
  docker_logs ${cid} $@ | grep '{"resourceLogs"' | docker_parse_otlp_logs
}

# Parses OpenTelemetry logs into a human-readable format
function docker_parse_otlp_logs() {
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

# Reloads Docker daemon configuration without restarting service or containers
function docker_reload() {
  local config_file=${1:-"/etc/docker/daemon.json"}
  local show_info=${2:-"true"}

  # Check if configuration file exists
  if [ ! -f "${config_file}" ]; then
    log error "Docker configuration file not found: ${config_file}"
    return ${RETURN_FAILURE:-1}
  fi

  # Validate JSON syntax
  if ! python3 -m json.tool "${config_file}" >/dev/null 2>&1; then
    log error "Invalid JSON syntax in configuration file: ${config_file}"
    return ${RETURN_FAILURE:-1}
  fi

  # Get Docker daemon PID
  local docker_pid=$(pgrep dockerd)
  if [ -z "${docker_pid}" ]; then
    log error "Docker daemon is not running"
    return ${RETURN_FAILURE:-1}
  fi

  log info "Reloading Docker daemon configuration..."
  log info "Configuration file: ${config_file}"
  log info "Docker daemon PID: ${docker_pid}"

  # Send SIGHUP signal to reload configuration
  if sudo kill -SIGHUP ${docker_pid}; then
    log info "SIGHUP signal sent successfully to Docker daemon"

    # Wait a moment for configuration to take effect
    sleep 2

    # Show configuration status if requested
    if [ "${show_info}" = "true" ]; then
      log info "Current Docker configuration:"
      echo "----------------------------------------"
      docker system info | grep -A 10 -E "Registry Mirrors|Insecure Registries|Experimental|Docker Root Dir" || true
      echo "----------------------------------------"
    fi

    log info "Docker configuration reloaded successfully"
    log warn "Note: Only certain configuration options support dynamic reload"
    log warn "Options like data-root, storage-driver require service restart"

    return ${RETURN_SUCCESS:-0}
  else
    log error "Failed to send SIGHUP signal to Docker daemon"
    log error "You may need sudo privileges to reload Docker configuration"
    return ${RETURN_FAILURE:-1}
  fi
}

function docker_get_host_mem_bytes() {
  local proc_meminfo_file=${1:-${CWS_DOCKER_PROC_MEMINFO_FILE:-/proc/meminfo}}
  local mem_kb=""

  mem_kb=$(awk '/MemAvailable/ {print $2; exit}' "${proc_meminfo_file}" 2>/dev/null)
  if [ -z "${mem_kb}" ] || [ "${mem_kb}" -le 0 ] 2>/dev/null; then
    mem_kb=$(awk '/MemTotal/ {print $2; exit}' "${proc_meminfo_file}" 2>/dev/null)
  fi

  if [ -n "${mem_kb}" ] && [ "${mem_kb}" -gt 0 ] 2>/dev/null; then
    echo $((mem_kb * 1024))
    return 0
  fi

  return 1
}

function docker_is_valid_mem_limit() {
  local value="${1:-}"
  local unlimited_threshold=${2:-9223372036850000000}

  if ! [[ "${value}" =~ ^[0-9]+$ ]]; then
    return 1
  fi

  if [ "${value}" -le 0 ] || [ "${value}" -ge "${unlimited_threshold}" ]; then
    return 1
  fi

  return 0
}

function docker_get_mem_limit_bytes() {
  local mem_limit=""
  local unlimited_threshold=9223372036850000000
  local cgroup_v2_mem_max_file=${CWS_DOCKER_CGROUP_V2_MEM_MAX_FILE:-/sys/fs/cgroup/memory.max}
  local cgroup_v1_mem_limit_file=${CWS_DOCKER_CGROUP_V1_MEM_LIMIT_FILE:-/sys/fs/cgroup/memory/memory.limit_in_bytes}
  local proc_meminfo_file=${CWS_DOCKER_PROC_MEMINFO_FILE:-/proc/meminfo}

  if [ -r "${cgroup_v2_mem_max_file}" ]; then
    mem_limit=$(cat "${cgroup_v2_mem_max_file}" 2>/dev/null)
    if [ "${mem_limit}" != "max" ] && docker_is_valid_mem_limit "${mem_limit}" "${unlimited_threshold}"; then
      echo "${mem_limit}"
      return
    fi
  fi

  if [ -r "${cgroup_v1_mem_limit_file}" ]; then
    mem_limit=$(cat "${cgroup_v1_mem_limit_file}" 2>/dev/null)
    if docker_is_valid_mem_limit "${mem_limit}" "${unlimited_threshold}"; then
      echo "${mem_limit}"
      return
    fi
  fi

  docker_get_host_mem_bytes "${proc_meminfo_file}" || awk '/MemTotal/ {print $2 * 1024}' "${proc_meminfo_file}"
}

function docker_get_cpu_limit_cores() {
  local cpu_quota=""
  local cpu_period=""
  local cpu_cores=""

  if [ -r /sys/fs/cgroup/cpu.max ]; then
    read -r cpu_quota cpu_period </sys/fs/cgroup/cpu.max
    if [ "${cpu_quota}" != "max" ] && [ -n "${cpu_quota}" ] && [ -n "${cpu_period}" ]; then
      cpu_cores=$(((cpu_quota + cpu_period - 1) / cpu_period))
      if [ "${cpu_cores}" -lt 1 ]; then
        cpu_cores=1
      fi
      echo "${cpu_cores}"
      return
    fi
  fi

  if [ -r /sys/fs/cgroup/cpu/cpu.cfs_quota_us ] && [ -r /sys/fs/cgroup/cpu/cpu.cfs_period_us ]; then
    cpu_quota=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null)
    cpu_period=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us 2>/dev/null)
    if [ -n "${cpu_quota}" ] && [ -n "${cpu_period}" ] && [ "${cpu_quota}" -gt 0 ] && [ "${cpu_period}" -gt 0 ]; then
      cpu_cores=$(((cpu_quota + cpu_period - 1) / cpu_period))
      if [ "${cpu_cores}" -lt 1 ]; then
        cpu_cores=1
      fi
      echo "${cpu_cores}"
      return
    fi
  fi

  nproc 2>/dev/null || echo 1
}

function docker_get_java_opts() {
  local mem_limit_bytes=$(docker_get_mem_limit_bytes)
  local cpu_limit_cores=$(docker_get_cpu_limit_cores)

  if [ -z "${mem_limit_bytes}" ] || [ "${mem_limit_bytes}" -le 0 ]; then
    mem_limit_bytes=$((1024 * 1024 * 1024))
  fi

  mem_limit_mb=$((mem_limit_bytes / 1024 / 1024))
  if [ "${mem_limit_mb}" -lt 512 ]; then
    mem_limit_mb=512
  fi

  heap_xmx_mb=$((mem_limit_mb * 70 / 100))
  if [ "${heap_xmx_mb}" -lt 256 ]; then
    heap_xmx_mb=256
  fi

  heap_xms_mb=$((heap_xmx_mb / 2))
  if [ "${heap_xms_mb}" -lt 128 ]; then
    heap_xms_mb=128
  fi

  gc_threads=${cpu_limit_cores}
  if [ "${gc_threads}" -gt 8 ]; then
    gc_threads=8
  fi

  conc_gc_threads=$((cpu_limit_cores / 4))
  if [ "${conc_gc_threads}" -lt 1 ]; then
    conc_gc_threads=1
  fi

  echo "-Xms${heap_xms_mb}m \
        -Xmx${heap_xmx_mb}m \
        -XX:ActiveProcessorCount=${cpu_limit_cores} \
        -XX:ParallelGCThreads=${gc_threads} \
        -XX:ConcGCThreads=${conc_gc_threads}"
}
