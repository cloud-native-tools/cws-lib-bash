function date_from_timestamp() {
  date '+%Y-%m-%d %T' --date @${1}
}

function date_adjust_seconds() {
  date '+%Y-%m-%d %T' --date="$1 CST $2 seconds"
}
