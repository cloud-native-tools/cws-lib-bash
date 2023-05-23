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

function net_my() {
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
