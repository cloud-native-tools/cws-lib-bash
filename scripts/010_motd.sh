#!/bin/bash

#Color variables
C='\033[0m'
R='\033[0;31m'
G='\033[0;32m'
Y='\033[0;33m'
B='\033[0;34m'
P='\033[0;35m'
W='\033[0;37m'
X='\033[0m'

# Optional environment identity overlay, rendered by motd_render.
#   CWS_MOTD_ENV_FILE  sourceable KEY=VALUE file carrying the identity,
#                      responsibility and policy pointers assigned to this
#                      environment. Missing/unreadable file only drops the
#                      IDENTITY section; the host facts still render.
#   CWS_MOTD_TARGET    file motd_generate writes. Default /etc/motd.
CWS_MOTD_ENV_FILE=${CWS_MOTD_ENV_FILE:-/etc/cws/motd.env}
CWS_MOTD_TARGET=${CWS_MOTD_TARGET:-/etc/motd}

function _motd_identity_rows() {
  # Ordered "KEY|Label" table. Keys absent from the identity file are skipped,
  # so a partially populated environment still renders a stable layout.
  cat <<'EOF'
ENV_ID|Environment
ENV_KIND|Kind
ENV_ROLE|Role
ENV_ROLE_LABEL|Role label
ENV_RESPONSIBILITY|Responsibility
ENV_CLASS|Env class
ENV_SITE|Site
ENV_REGION|Region
ENV_LEVEL|Level
ENV_OWNER|Owner
ENV_POLICY|Policy
ENV_SSH_PROFILE|SSH profile
ENV_PROFILE_ID|Profile ID
ENV_MANAGED_BY|Managed by
ENV_AS_OF|Fact as of
ENV_SOURCE_COMMIT|Source commit
EOF
}

function _motd_os_pretty() {
  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    printf '%s' "${PRETTY_NAME:-unknown}"
  else
    printf '%s' "$(uname -s 2>/dev/null || echo unknown)"
  fi
}

function _motd_cpu_model() {
  local model=""
  if [ -r /proc/cpuinfo ]; then
    model=$(awk -F ': ' '/^model name/ { print $2; exit }' /proc/cpuinfo 2>/dev/null)
    [ -n "${model}" ] || model=$(awk -F ': ' '/^(Model|Hardware)/ { print $2; exit }' /proc/cpuinfo 2>/dev/null)
  fi
  [ -n "${model}" ] || model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)
  printf '%s' "${model:-unknown}"
}

function _motd_cpu_count() {
  local count=""
  count=$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)
  [ -n "${count}" ] || count=$(nproc 2>/dev/null || true)
  printf '%s' "${count:-unknown}"
}

function _motd_mem_total() {
  if [ -r /proc/meminfo ]; then
    awk '/^MemTotal:/ { printf "%.1f GiB", $2 / 1048576 }' /proc/meminfo 2>/dev/null
    return 0
  fi
  local bytes
  bytes=$(sysctl -n hw.memsize 2>/dev/null || true)
  if [ -n "${bytes}" ]; then
    awk -v b="${bytes}" 'BEGIN { printf "%.1f GiB", b / 1073741824 }'
  fi
}

function _motd_disk_usage() {
  local mount out=""
  for mount in / /storage; do
    [ -d "${mount}" ] || continue
    out="${out}$(df -P -h "${mount}" 2>/dev/null | awk -v m="${mount}" 'NR == 2 { printf "%s %s/%s (%s)", m, $3, $2, $5 }') "
  done
  printf '%s' "${out% }"
}

function _motd_uptime() {
  if [ -r /proc/uptime ]; then
    awk '{
      s = int($1); d = int(s / 86400); h = int((s % 86400) / 3600); m = int((s % 3600) / 60)
      if (d > 0) printf "%dd ", d
      if (d > 0 || h > 0) printf "%dh ", h
      printf "%dm", m
    }' /proc/uptime 2>/dev/null
    return 0
  fi
  local boot
  boot=$(sysctl -n kern.boottime 2>/dev/null | awk -F '[=,]' '{ gsub(/ /, "", $2); print $2 }')
  if [ -n "${boot}" ]; then
    awk -v b="${boot}" -v n="$(date +%s)" 'BEGIN {
      s = n - b; d = int(s / 86400); h = int((s % 86400) / 3600); m = int((s % 3600) / 60)
      if (d > 0) printf "%dd ", d
      if (d > 0 || h > 0) printf "%dh ", h
      printf "%dm", m
    }'
    return 0
  fi
  uptime 2>/dev/null | sed 's/.*up //; s/,.*//'
}

function _motd_load() {
  if [ -r /proc/loadavg ]; then
    awk '{ print $1 ", " $2 ", " $3 }' /proc/loadavg 2>/dev/null
  else
    sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{ print $1 ", " $2 ", " $3 }'
  fi
}

function _motd_virt() {
  local virt=""
  virt=$(systemd-detect-virt 2>/dev/null || true)
  if [ -z "${virt}" ] || [ "${virt}" = "none" ]; then
    if [ -f /.dockerenv ]; then
      virt="docker"
    else
      virt="none (bare metal)"
    fi
  fi
  printf '%s' "${virt}"
}

function _motd_ip_addrs() {
  local ips=""
  ips=$(hostname -I 2>/dev/null | tr ' ' '\n' | awk 'NF && $1 !~ /^127\./' | paste -sd, - 2>/dev/null)
  [ -n "${ips}" ] || ips=$(ip -o -4 addr show scope global 2>/dev/null | awk '{ split($4, a, "/"); printf "%s,", a[1] }' | sed 's/,$//')
  [ -n "${ips}" ] || ips=$(ifconfig 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" { printf "%s,", $2 }' | sed 's/,$//')
  printf '%s' "${ips:-unknown}"
}

function _motd_runtime() {
  local docker_version="" containerd_version=""
  docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || true)
  containerd_version=$(containerd --version 2>/dev/null | awk '{ print $3 }' || true)
  printf '%s' "docker=${docker_version:-absent} containerd=${containerd_version:-absent}"
}

function _motd_cmdline() {
  [ -r /proc/cmdline ] || return 0
  tr -s ' ' < /proc/cmdline 2>/dev/null | cut -c1-160
}

##############################################################################
# motd_render
#
# Print the motd to stdout and never touch the filesystem. The identity
# section is driven by CWS_MOTD_ENV_FILE; host facts are discovered from the
# running OS so a fresh machine needs no per-host configuration.
##############################################################################
function motd_render() {
  (
    local hostname kernel arch os cpu_model cpu_count mem disk uptime_now load
    local virt ips runtime cmdline login_user runtime_profile

    hostname=$(uname -n 2>/dev/null || hostname 2>/dev/null || echo unknown)
    kernel=$(uname -r 2>/dev/null || echo unknown)
    arch=$(uname -m 2>/dev/null || echo unknown)
    os=$(_motd_os_pretty)
    cpu_model=$(_motd_cpu_model)
    cpu_count=$(_motd_cpu_count)
    mem=$(_motd_mem_total)
    disk=$(_motd_disk_usage)
    uptime_now=$(_motd_uptime)
    load=$(_motd_load)
    virt=$(_motd_virt)
    ips=$(_motd_ip_addrs)
    runtime=$(_motd_runtime)
    cmdline=$(_motd_cmdline)
    login_user=$(id -un 2>/dev/null || whoami 2>/dev/null || echo unknown)
    runtime_profile=${PROFILES_ACTIVED:-"${login_user}@${hostname}"}

    printf '\033[2J\033[H'
    printf '%b\n' "${Y}"
    cat <<'EOF'
    _     _  _  _             _
   / \   | |(_)| |__    __ _ | |__    __ _
  / _ \  | || || '_ \  / _` || '_ \  / _` |
 / ___ \ | || || |_) || (_| || |_) || (_| |
/_/   \_\|_||_||_.__/  \__,_||_.__/  \__,_|
EOF
    printf '%b\n' "${C}"
    printf '%b\n' "${R}==============================================================================${C}"
    printf '%b\n' "  ${R}Welcome to${C} ${Y}${hostname}${C}  ${W}${ips}${C}"
    printf '%b\n' "${R}==============================================================================${C}"

    printf '%b\n' " ${G}[ IDENTITY ]${C}  ${W}${CWS_MOTD_ENV_FILE}${C}"
    if [ -r "${CWS_MOTD_ENV_FILE}" ]; then
      # shellcheck disable=SC1090
      . "${CWS_MOTD_ENV_FILE}"
      _motd_identity_rows | while IFS='|' read -r key label; do
        value=${!key}
        [ -n "${value}" ] || continue
        printf '   %-16s = %s\n' "${label}" "${value}"
      done
    else
      printf '   %-16s = %s\n' "Status" "not configured (${CWS_MOTD_ENV_FILE} missing)"
    fi
    printf '   %-16s = %s\n' "Runtime user" "${login_user}"
    printf '   %-16s = %s\n' "Runtime profile" "${runtime_profile}"

    printf '%b\n' " ${G}[ HOST ]${C}"
    printf '   %-16s = %s\n' "OS" "${os}"
    printf '   %-16s = %s\n' "Kernel" "${kernel}"
    printf '   %-16s = %s\n' "Arch" "${arch}"
    printf '   %-16s = %s\n' "CPU" "${cpu_model} (${cpu_count} cores)"
    [ -n "${mem}" ] && printf '   %-16s = %s\n' "Memory" "${mem}"
    [ -n "${disk}" ] && printf '   %-16s = %s\n' "Disk" "${disk}"
    printf '   %-16s = %s\n' "Virt" "${virt}"
    printf '   %-16s = %s\n' "Uptime" "${uptime_now}"
    printf '   %-16s = %s\n' "Load (1/5/15)" "${load}"

    printf '%b\n' " ${G}[ NET ]${C}"
    printf '   %-16s = %s\n' "Addresses" "${ips}"
    printf '%b\n' " ${G}[ RUNTIME ]${C}"
    printf '   %-16s = %s\n' "Containers" "${runtime}"
    [ -n "${cmdline}" ] && printf '   %-16s = %s\n' "Kernel cmdline" "${cmdline}"

    printf '%b\n' "${R}==============================================================================${C}"
  )
}

##############################################################################
# motd_generate [target]
#
# Render motd_render into CWS_MOTD_TARGET (default /etc/motd). Requires the
# target directory to be writable; never fails the caller's shell.
##############################################################################
function motd_generate() {
  local target=${1:-${CWS_MOTD_TARGET}}
  local dir
  dir=$(dirname "${target}")

  if [ ! -d "${dir}" ]; then
    log error "motd target directory missing: ${dir}"
    return ${RETURN_FAILURE:-1}
  fi
  if [ ! -w "${target}" ] && [ ! -w "${dir}" ]; then
    log error "motd target not writable: ${target} (run as root?)"
    return ${RETURN_FAILURE:-1}
  fi

  if ! motd_render >"${target}"; then
    log error "failed to render motd into ${target}"
    return ${RETURN_FAILURE:-1}
  fi

  log notice "generated motd: ${target}"
  return ${RETURN_SUCCESS:-0}
}

function motd() {
  cat "${CWS_MOTD_TARGET}"
}
