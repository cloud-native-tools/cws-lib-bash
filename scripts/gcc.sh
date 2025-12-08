function gcc_std() {
  local cc=${1:-gcc}
  ${cc} -v --help 2>/dev/null | sed -n '/^ *-std=\([^<][^ ]\+\).*/ {s//\1/p}'
}
