function timestamp2date() {
  date '+%Y-%m-%d %T' --date @${1}
}

function date_adjust_seconds() {
  date '+%Y-%m-%d %T' --date="$1 CST $2 seconds"
}

