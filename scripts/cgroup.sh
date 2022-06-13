function cgroup_is_v2() {
    test -e /sys/fs/cgroup/cgroup.controllers
}

function cgroup_remove_all() {
    find /sys/fs/cgroup -depth -type d -print -exec rmdir {} \;
}
