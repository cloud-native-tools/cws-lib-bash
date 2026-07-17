function tcpdump_cap() {
  local interface=${1}
  if [ -z "${interface}" ]; then
    tcpdump -A -s 65535 -X -q -tttt -w all.cap
  else
    tcpdump -i ${interface} -s 65535 -X -q -tttt -w ${interface}.cap
  fi
}
