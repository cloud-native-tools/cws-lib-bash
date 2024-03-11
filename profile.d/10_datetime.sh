function date_from_timestamp() {
  date '+%Y-%m-%d %T' --date @${1}
}

function date_adjust_seconds() {
  date '+%Y-%m-%d %T' --date="$1 CST $2 seconds"
}

function time_duration() {
  local from="${1:-"1970-01-01 00:00:00"}"
  local to="${2-$(date_now)}"
  if [ -z "${from}" ] || [ -z "${to}" ]; then
    echo "Usage: time_duration <from> <to>"
    return 1
  fi
  if is_macos; then
    from_seconds=$(date -j -f "%Y-%m-%d %H:%M:%S" "${from}" "+%s")
    to_seconds=$(date -j -f "%Y-%m-%d %H:%M:%S" "${to}" "+%s")
  else
    from_seconds=$(date -d"${from}" +%s)
    to_seconds=$(date -d"${to}" +%s)
  fi

  diff_seconds=$((to_seconds - from_seconds))
  echo "${diff_seconds}"
}

function uptime() {
  date -d "$(awk '{print $1}' /proc/uptime) seconds ago" "${DATE_TIME_FORMAT}"
}
