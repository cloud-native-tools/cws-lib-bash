function cgroup_is_v2() {
    test -e /sys/fs/cgroup/cgroup.controllers
}

function cgroup_remove_all() {
    find /sys/fs/cgroup -depth -type d -print -exec rmdir {} \;
}

function cgroup_path_of() {
    local cgroup_root=${1:-/sys/fs/cgroup}
    local pid_list=${@:-$$}
    find ${cgroup_root} -name "*.procs" -exec grep -E "${pid_list}" {} /dev/null \; 2>/dev/null
}
