function cgroup_remove_all() {
  find /sys/fs/cgroup -depth -type d -print -exec rmdir {} \;
}

function cgroup_path_of_pid() {
  local cgroup_root=$(dirname $(mount | grep 'cgroup on ' | grep cpuset | awk '{print $3}'))
  local pid=${1}
  find ${cgroup_root} -name "*.procs" -exec grep -w "${pid}" {} /dev/null \; 2>/dev/null
}

function cgroup2_enabled() {
  test -e /sys/fs/cgroup/cgroup.controllers
}

function cgroup2_supported() {
  grep -w cgroup2 /proc/filesystems >/dev/null 2>&1
}
