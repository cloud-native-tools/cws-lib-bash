function net_hosts_resolve_sed_script() {
  cat /etc/hosts | grep -Ev '^ *#' | grep -Ev '^ *$' | awk '{print "s/"$2"/"$1"/g"}'
}
