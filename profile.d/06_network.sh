TCP_STATE=(INVALID TCP_ESTABLISHED TCP_SYN_SENT TCP_SYN_RECV TCP_FIN_WAIT1 TCP_FIN_WAIT2 TCP_TIME_WAIT TCP_CLOSE TCP_CLOSE_WAIT TCP_LAST_ACK TCP_LISTEN TCP_CLOSING)

function net_info() {
  local pid=$1
  cat /proc/${pid}/net/tcp | sed 's/:/ /g' | grep -v local_address | while IFS= read -r line; do
    fields=($line)
    local_ip=$(echo ${fields[1]} | sed -e 's/\(..\)\(..\)\(..\)\(..\)/0x\4 0x\3 0x\2 0x\1/g')
    remote_ip=$(echo ${fields[3]} | sed -e 's/\(..\)\(..\)\(..\)\(..\)/0x\4 0x\3 0x\2 0x\1/g')
    printf "%-20s " ${TCP_STATE[$(printf %d 0x${fields[5]})]} # connection state
    printf "%d.%d.%d.%d" ${local_ip[@]}                       # local IPv4 address
    printf ":%d  ->  " 0x${fields[2]}                         # local TCP port number
    printf "%d.%d.%d.%d" ${remote_ip[@]}                      # remote IPv4 address
    printf ":%d  \n" 0x${fields[4]}                           # remote TCP port number
  done
}

function net_route_add() {
  local target=$1
  local gateway=$2
  local interface=$3
  ip route add ${target} via ${gateway} dev ${interface}
}

function net_route_get() {
  local target=$1
  ip route get ${target}
}

function net_income_conn() {
  local port=$1
  netstat -apnt4 | grep -w ESTABLISHED | awk "(\$4 ~ /.*:${port}/){print \$5}" | awk 'BEGIN{FS=":"}{print $1}' | sort | uniq -c
}

function net_outcome_conn() {
  local port=$1
  netstat -apnt4 | grep -w ESTABLISHED | awk "(\$5 ~ /.*:${port}/){print \$5}" | awk 'BEGIN{FS=":"}{print $1}' | sort | uniq -c
}

function net_add_delay_in_ms() {
  tc qdisc add dev $1 root netem delay ${2}ms
}

function net_del_delay_in_ms() {
  tc qdisc del dev $1 root netem
}

function net_namespaces() {
  cd /var/run/netns
  for n in *; do
    ss -tpn -l -N $n
  done
}

function net_my_login_ip() {
  ip route get $(who | awk '{print $NF}' | tr -d '(' | tr -d ')') | grep src | awk '{print $7}'
}

function net_ping() {
  ping -c 4 -i 0.1 -W 1 $@ >/dev/null 2>&1
}

function net_is_ip() {
  local ip=${1}
  if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log plain "true"
  else
    log plain "false"
  fi
}

function net_my_ip() {
  local timeout=${1:-3}
  
  # Quick fallback for when speed is critical (ordered by current environment performance)
  local -a quick_services=(
    "https://cip.cc"
    "https://ipv4.seeip.org"
    "https://myip.ipip.net/"
    "https://api.ipify.org"
  )
  
  for url in "${quick_services[@]}"; do
    case "${url}" in
      *cip.cc*)
        local my_ip=$(curl -s --connect-timeout ${timeout} --max-time ${timeout} "${url}" 2>/dev/null | grep -E '^IP' | awk '{print $NF}' 2>/dev/null)
        ;;
      *myip.ipip.net*)
        local my_ip=$(curl -s --connect-timeout ${timeout} --max-time ${timeout} "${url}" 2>/dev/null | grep -E '当前 IP：' | awk '{print $3}' 2>/dev/null)
        ;;
      *)
        local my_ip=$(curl -s --connect-timeout ${timeout} --max-time ${timeout} "${url}" 2>/dev/null)
        ;;
    esac
    
    if net_valid_ipv4 "${my_ip}"; then
      echo "${my_ip}"
      return ${RETURN_SUCCESS}
    fi
  done
  
  return ${RETURN_FAILURE}
}

function net_trace_route() {
  local target_host=${1}
  traceroute -q 5 -w 2 ${target_host}
}

function net_valid_ipv4() {
  local ip="$1"
  
  # Check if IP parameter is provided
  if [ -z "${ip}" ]; then
    log debug "IP address parameter is required"
    return ${RETURN_FAILURE}
  fi
  
  # Basic format validation: four groups of 1-3 digits separated by dots
  if ! [[ "${ip}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    log debug "[${ip}] address format is invalid"
    return ${RETURN_FAILURE}
  fi
  
  # Validate each octet is in range 0-255
  local IFS='.'
  local -a octets=($ip)
  
  for octet in "${octets[@]}"; do
    # Remove leading zeros to avoid octal interpretation
    octet=$(echo "$octet" | sed 's/^0*//')
    [ -z "$octet" ] && octet=0
    
    if [ "$octet" -gt 255 ] || [ "$octet" -lt 0 ]; then
      log debug "[${ip}] contains invalid octet: $octet (must be 0-255)"
      return ${RETURN_FAILURE}
    fi
  done
  
  return ${RETURN_SUCCESS}
}

function net_default_ip() {
  for ip in $(ifconfig | grep -w inet | awk '{print $2}'); do
    if net_valid_ipv4 ${ip}; then
      echo ${ip}
      return ${RETURN_SUCCESS}
    fi
  done
  return ${RETURN_FAILURE}
}


function net_wait_tcp_port {
    local host=${1}
    local port=${2}
    local max_tries=${3:-60} 
    local tries=1

    while ! exec 6<>/dev/tcp/${host}/${port} && [[ ${tries} -lt ${max_tries} ]]; do
        sleep 1s
        tries=$(( tries + 1 ))
        echo "$(date) retrying to connect to ${host}:${port} (${tries}/${max_tries})"
    done
    exec 6>&-
}