function is_bash() { test "$(basename $SHELL)" = "bash" -a -n "$BASH_VERSION"; }
function is_zsh() { test "$(basename $SHELL)" = "zsh"; }
function is_ash() { test "$(basename $SHELL)" = "ash"; }
function is_dash() { test "$(basename $SHELL)" = "dash"; }

is_bash && alias sh="bash"
is_zsh && alias sh="zsh"
is_ash && alias sh="ash"
is_dash && alias sh="dash"

if is_bash; then
  # source .bashrc if exists in working directory
  if [ -f .bashrc ]; then
    . .bashrc
  fi
fi

function debug_on() {
  local log=$1
  if [ -n "${log}" ]; then
    exec 2 >${log}
  fi
  if is_bash; then
    export PS4='+$? ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
  fi
  if is_zsh; then
    setopt prompt_subst
    export PS4='+$? ${(%):-%N}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
  fi

  set -x
}

function debug_off() {
  set +x
}

function is_interactive() { test -t 0; }

function date_now() {
  date "+${DATE_TIME_FORMAT:-%Y-%m-%d %H:%M:%S}"
}

function date_tag() {
  date "+%Y-%m"
}

function date_id() {
  date "+%Y-%m-%d"
}

function date_time_id() {
  date "+%Y-%m-%d-%H-%M-%S"
}

function date_utc_to_cst() {
  local utc_time=${1}

  if is_macos; then
    TZ='Asia/Shanghai' date -j -f "%Y-%m-%dT%H:%M:%SZ" "${utc_time}" "+%Y-%m-%d %H:%M:%S"
  else
    TZ='Asia/Shanghai' date -d "${utc_time}" '+%Y-%m-%d %H:%M:%S'
  fi
}

function log() {
  local level=$1
  local now=$(date_now)

  case ${level} in
  PLAIN | plain)
    shift
    # print what as-is, no color
    printf "%s\n" "$*"
    ;;
  COLOR | color)
    shift
    # like plain, but with color
    printf "%b\n" "$@"
    ;;
  INFO | info)
    shift
    printf "%b\n" "[${now}][$$][INFO] $@"
    ;;
  NOTICE | notice)
    shift
    printf "%b\n" "${GREEN}[${now}][$$][NOTICE] $@${CLEAR}"
    ;;
  WARN | warn)
    shift
    # use yellow color for warning
    printf "%b\n" "${YELLOW}[${now}][$$][WARN] $@${CLEAR}" >&2
    ;;
  ERROR | error)
    shift
    # use red color for error
    printf "%b\n" "${RED}[${now}][$$][ERROR] $@${CLEAR}" >&2
    ;;
  FATAL | fatal)
    shift
    # use red color for fatal error, NOTICE: this will exit the script
    printf "%b\n" "${RED}[${now}][$$][FATAL] $@${CLEAR}" >&2
    exit ${EXIT_FAILURE}
    ;;
  *)
    log plain $@
    ;;
  esac
}

function die() {
  log plain "${RED}${@}${CLEAR}"
  exit ${EXIT_FAIL}
}

function matches() {
  local pat=$1
  shift
  log plain "$@" | grep -qEi "$pat" >/dev/null 2>&1
}

function success() {
  log plain "${SYMBOL_SUCCESS}"
}

function failed() {
  log plain "${SYMBOL_FAILURE}"
}

function trim() {
  log plain "$@" | awk '{ gsub(/^ +| +$/,"") }{ print $0 }'
}

function repeat() {
  log plain $(printf "%${2}s" | tr " " "$1")
}

function truncate() {
  local len=$1
  shift
  log plain "$*" | awk -v len=$len '{ if (length($0) > len) print substr($0, 1, len-3) "..."; else print; }'
}

function upper() {
  log plain $@ | tr '[:lower:]' '[:upper:]'
}

function lower() {
  log plain $@ | tr '[:upper:]' '[:lower:]'
}

function escape() {
  log plain "$@" | sed 's/\([\.\$\*]\)/\\\1/g'
}

function escape_slashes() {
  log plain "$@" | sed 's/\\/\\\\/g'
}

function url_decode() {
  echo ${1} | sed -E 's/%3F/?/g;s/%3D/=/g;s/%26/\&/g'
}

function source_scripts() {
  local script_home=$1
  local script_suffix=${2:-'*.sh'}
  if [[ -n "${script_home}" && -d ${script_home} ]]; then
    for script in $(find "${script_home}" -name ${script_suffix}); do
      log INFO "source script ${script} in ${script_home}"
      source ${script}
    done
    unset script
  fi
}

function script_entry() {
  if [ $# -gt 0 ]; then
    if typeset -f $1 >/dev/null 2>&1; then
      fn=$1
      shift
      log INFO "call function [${fn}]: $@"
      ${fn} $@
    else
      var=$1
      shift
      log INFO "show variables [${var}]:"
      eval "echo ${var}=\${var}"
    fi
  else
    log info "$0 sourced"
  fi
}

function count_line() {
  local lineno=${1}
  while read -r line; do
    log plain "${lineno} ${line}"
    if [ -n "${line}" ]; then
      ((lineno += 1))
    fi
  done
}

function urlencode() {
  local url="${1}"
  local length="${#url}"
  local encoded=""
  local i

  for ((i = 0; i < length; i++)); do
    local char="${url:i:1}"
    case "${char}" in
    [a-zA-Z0-9.~_-:/])
      encoded="${encoded}${char}"
      ;;
    *)
      encoded="${encoded}$(printf '%%%02X' "'${char}")"
      ;;
    esac
  done

  echo "${encoded}"
}

function have() {
  local cmd=${1}
  if ! command -v ${cmd} >/dev/null 2>&1; then
    log error "command [${cmd}] not found"
    return ${RETURN_FAILURE}
  fi
  return ${RETURN_SUCCESS}
}

function lesser() {
  cat - | less -F -S -X -K
}

function dump_stack() {
  local current=$$
  local indent=""
  local count=50

  local cmdline="$(cat /proc/${current}/cmdline | tr '\000' ' ')"
  local parent="$(grep PPid /proc/${current}/status | awk '{ print $2; }')"
  local frame="${indent}${BOLD_RED}[${current}]:${cmdline}${CLEAR}\n"

  while [ ${count} -gt 0 ]; do
    current=${parent}
    indent="  ${indent}"
    count=$((count - 1))

    cmdline=$(cat /proc/${current}/cmdline | tr '\000' ' ')
    parent=$(grep PPid /proc/${current}/status | awk '{ print $2; }')
    frame="${frame}${indent}[${current}]:${cmdline}\n"
    if [ "${current}" == "1" ]; then
      break
    fi
  done
  log color "${frame}"
}

function spin() {
  if [ $# -eq 0 ]; then
    log error "Usage: spin <command>"
    return ${RETURN_FAILURE}
  fi
  $@ &
  local pid=$!
  local i=1
  local sp="\|/-"
  while kill -0 ${pid} >/dev/null 2>&1; do
    printf "\b%c" "${sp:i++%4:1}"
    sleep 0.1
  done
}

function is_macos() {
  if [ "${BASH_OS}" = "darwin" ]; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

function is_linux() {
  if [ "${BASH_OS}" = "linux" ]; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

function set_default() {
  if [ -z "${!1}" ]; then
    export $1=$2
  fi
}

function is_sourced() {
  # https://unix.stackexchange.com/a/215279
  [ "${#FUNCNAME[@]}" -ge 2 ] &&
    [ "${FUNCNAME[0]}" = '_is_sourced' ] &&
    [ "${FUNCNAME[1]}" = 'source' ]
}

function add_line_if_not_exit() {
  local file=$1
  local line=$2
  if ! test -f ${file} || ! grep -Fxq "${line}" ${file}; then
    echo ${line} >>${file}
    chmod a+rx ${file}
  fi
}

function random_string() {
  local length=${1:-8}
  head /dev/urandom | sha256sum | head -c "${length}"
}

function highlight() {
  local pattern="${@}"
  grep --color=always -Ew "${pattern}|\$"
}
