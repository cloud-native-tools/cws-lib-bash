function iptables_all() {
  iptables --line-numbers -vnL $@
}
