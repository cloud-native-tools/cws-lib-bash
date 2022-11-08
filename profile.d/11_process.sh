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
  local pid=${1}
  pstree -apsnl -N net -H ${pid} ${pid}
}
