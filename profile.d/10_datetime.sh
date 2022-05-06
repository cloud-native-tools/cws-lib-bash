function timestamp2date() {
  date '+%Y-%m-%d %T' --date @${1}
}

function date_adjust_seconds() {
  date '+%Y-%m-%d %T' --date="$1 CST $2 seconds"
}

function date_now() {
  date "+${DATE_TIME_FORMAT:-%Y-%m-%d %H:%M:%S}"
}