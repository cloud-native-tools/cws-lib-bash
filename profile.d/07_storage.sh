function du_top() {
  local topN=${1:-10}
  du -x -h -d1 | sort -hr | head -n ${topN}
}

function ls_top() {
  local topN=${1:-10}
  ls -lSh | sort -h | head -n ${topN}
}
