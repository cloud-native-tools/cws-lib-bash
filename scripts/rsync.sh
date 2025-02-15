function rsync_current_to_remote(){
  # shellcheck disable=SC2155
  local source=${PWD}
  local target=${1}
  rsync -rlptzv --progress --delete --exclude=.git "${source}" "${target}"
}

