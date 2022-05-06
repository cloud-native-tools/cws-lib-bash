function virsh_dhcp() {
  local network=${1:-default}
  virsh net-dhcp-leases ${network}
}
