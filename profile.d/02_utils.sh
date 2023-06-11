function is_bash() { test -n "${BASH_VERSION}"; }
function is_zsh() { test -n "${ZSH_VERSION}"; }

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
  local color=""
  local clear=""
  case ${level} in
  COLOR | color)
    shift
    printf "%b\n" "$@"
    return
    ;;
  PLAIN | plain)
    shift
    printf "%s\n" "$*"
    return
    ;;
  WARN | warn)
    color=${YELLOW}
    clear=${CLEAR}
    level="WARN"
    shift
    ;;
  ERROR | error)
    color=${RED}
    clear=${CLEAR}
    level="ERROR"
    shift
    ;;
  INFO | info)
    level="INFO"
    shift
    ;;
  *)
    level="INFO"
    ;;
  esac
  printf "%b\n" "${color}[${now}][$$][${level}] $@${clear}"
}

function die() {
  log plain "${RED}${@}${CLEAR}"
  exit 1
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
