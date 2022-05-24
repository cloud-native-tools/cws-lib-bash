function is_cgroup_v2() {
    test -e /sys/fs/cgroup/cgroup.controllers
}
