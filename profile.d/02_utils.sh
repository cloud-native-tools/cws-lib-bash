
function is_bash() { test -n "${BASH_VERSION}"; }
function is_zsh() { test -n "${ZSH_VERSION}"; }

function debug_on() {
  local log=$1
  if [ -n "${log}" ]; then
    exec 2 >${log}
  fi
  export PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
  set -x
}

function debug_off() {
  set +x
}

function is_interactive() { test -t 0; }

function log() {
  local level=$1
  local now=$(date_now)
  local color
  case ${level} in
  WARN)
    color=${YELLOW}
    ;;
  ERROR)
    color=${RED}
    ;;
  esac
  echo -en "${color}[${now}] $@${CLEAR}\n"
}

function die() {
  echo -e "${RED}${@}${CLEAR}"
  exit 1
}

function get_script_root() {
  if test -t; then
    pwd || echo ${PWD}
  else
    is_bash && echo $(readlink -f $(dirname ${BASH_SOURCE[0]}))
    is_zsh && echo $(dirname ${(%):-%N})
  fi
}

function matches() {
  local pat=$1
  shift
  echo "$@" | grep -qEi "$pat" >/dev/null 2>&1
}

function success() {
  echo -e "${SYMBOL_SUCCESS}"
}

function failed() {
  echo -e "${SYMBOL_FAILURE}"
}

function trim() {
  echo "$@" | awk '{ gsub(/^ +| +$/,"") }{ print $0 }'
}

function repeat() {
  echo $(printf "%${2}s" | tr " " "$1")
}

function truncate() {
  local len=$1
  shift
  echo "$*" | awk -v len=$len '{ if (length($0) > len) print substr($0, 1, len-3) "..."; else print; }'
}

function escape() {
  echo "$1" | sed 's/\([\.\$\*]\)/\\\1/g'
}

function escape_slashes() {
  echo "$@" | sed 's/\\/\\\\/g'
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
