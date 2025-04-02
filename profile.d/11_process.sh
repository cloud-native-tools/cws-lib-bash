function ps_user() {
  ps -ef | grep -v '\[' | sort -k 8
}

# pstree
# Usage: pstree [ -a ] [ -c ] [ -h | -H PID ] [ -l ] [ -n ] [ -p ] [ -g ] [ -u ]
#               [ -A | -G | -U ] [ PID | USER ]
#        pstree -V
# Display a tree of processes.

#   -a, --arguments     show command line arguments
#   -A, --ascii         use ASCII line drawing characters
#   -c, --compact       don't compact identical subtrees
#   -h, --highlight-all highlight current process and its ancestors
#   -H PID,
#   --highlight-pid=PID highlight this process and its ancestors
#   -g, --show-pgids    show process group ids; implies -c
#   -G, --vt100         use VT100 line drawing characters
#   -l, --long          don't truncate long lines
#   -n, --numeric-sort  sort output by PID
#   -N type,
#   --ns-sort=type      sort by namespace type (ipc, mnt, net, pid, user, uts)
#   -p, --show-pids     show PIDs; implies -c
#   -s, --show-parents  show parents of the selected process
#   -S, --ns-changes    show namespace transitions
#   -u, --uid-changes   show uid transitions
#   -U, --unicode       use UTF-8 (Unicode) line drawing characters
#   -V, --version       display version information
#   -Z,
#   --security-context   show SELinux security contexts
#   PID    start at this PID; default is 1 (init)
#   USER   show only trees rooted at processes of this user

function ps_tree() {
  local pid=${1:-$$}
  pstree -asl -H ${pid} ${pid}
}

function ps_tree_ns() {
  local pid=${1:-$$}
  pstree -asnl -N net -H ${pid} ${pid}
}

function ps_inotify() {
  find /proc/*/fd \
    -lname anon_inode:inotify \
    -printf '%hinfo/%f\n' 2>/dev/null |
    xargs grep -c '^inotify' |
    sort -n -t: -k2 -r
}

function ps_ns() {
  ps -o pid,pidns,netns,mntns,ipcns,utsns,userns,args $@
}

function ps_top_mem() {
  local topN=${1:-10}
  ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n ${topN}
}

function search_bin_path() {
  local pattern=${1:-*}
  env | grep -E '^PATH=' | tr ':' '\n' | xargs -I{} find "{}" -name "${pattern}" 2>&1 | grep -v 'No such file or directory' | sort | uniq
}
