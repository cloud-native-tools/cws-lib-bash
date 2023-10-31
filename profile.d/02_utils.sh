function is_bash() { test "$(basename $SHELL)" = "bash"; }
function is_zsh() { test "$(basename $SHELL)" = "zsh"; }
function is_ash() { test "$(basename $SHELL)" = "ash"; }
function is_dash() { test "$(basename $SHELL)" = "dash"; }

is_bash && alias sh="bash"
is_zsh && alias sh="zsh"
is_ash && alias sh="ash"
is_dash && alias sh="dash"

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

function source_scripts() {
  local script_home=$1
  if [[ -n "${script_home}" && -d ${script_home} ]]; then
    for script in $(find "${script_home}" -name '*.sh'); do
      log INFO "Run script ${script} in ${script_home}"
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

function read_line() {
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
