function virsh_dhcp() {
  local network=${1:-default}
  virsh net-dhcp-leases ${network}
}

function virsh_net_update() {
  local network=$1
  local vmname=$2
  local mac=$3
  local ip=$4
  if [ -z "${network}" -o -z "${vmname}" -o -z "${mac}" -o -z "${ip}" ]; then
    echo "Usage: virsh_net_update network=${network} vmname=${vmname} mac=${mac} ip=${ip}"
  else
    virsh net-update ${network} add ip-dhcp-host "<host mac='${mac}' name='${vmname}' ip='${ip}'/>" --live --config
  fi
}
