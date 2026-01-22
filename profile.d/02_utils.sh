function is_bash() { test "$(basename $SHELL)" = "bash" -a -n "$BASH_VERSION"; }
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

function date_tag() {
  date "+%Y-%m"
}

function date_id() {
  date "+%Y-%m-%d"
}

function date_tag_with_seconds() {
  date "+%Y%m%d%H%M%S"
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
    DEBUG | debug)
      shift
      # only print debug messages when CWS_DEBUG is enabled
      # WARNING: enabling debug will generate excessive output, which may affect logic that depends on clean output
      if cws_debug_enabled; then
        printf "%b\n" "${CYAN}[${now}][$$][DEBUG]$@${CLEAR}" >&2
      fi
      ;;
    INFO | info)
      shift
      printf "%b\n" "[${now}][$$][INFO]$@"
      ;;
    NOTICE | notice)
      shift
      printf "%b\n" "${GREEN}[${now}][$$][NOTICE]$@${CLEAR}"
      ;;
    WARN | warn)
      shift
      # use yellow color for warning
      printf "%b\n" "${YELLOW}[${now}][$$][WARN]$@${CLEAR}" >&2
      ;;
    ERROR | error)
      shift
      # use red color for error
      printf "%b\n" "${RED}[${now}][$$][ERROR]$@${CLEAR}" >&2
      ;;
    FATAL | fatal)
      shift
      # use red color for fatal error, NOTICE: this will exit the script
      printf "%b\n" "${RED}[${now}][$$][FATAL]$@${CLEAR}" >&2
      exit ${EXIT_FAILURE}
      ;;
    *)
      log plain $@
      ;;
  esac
}

function log_with_context() {
  local level=$1
  local context=$2

  if [ -z "${level}" ] || [ -z "${context}" ]; then
    log error "Usage: log_with_context <level> <context> <message...>"
    return ${RETURN_FAILURE:-1}
  fi

  shift 2
  log "${level}" "[${context}] $@"
}

function die() {
  local msg="$*"
  log error "FATAL: ${msg}"
  log error "Context: User=${USER}, PWD=${PWD}, SHLVL=${SHLVL}"

  log error "Stack trace:"
  local i
  for ((i = 0; i < ${#FUNCNAME[@]} - 1; i++)); do
    local func="${FUNCNAME[i + 1]}"
    local source="${BASH_SOURCE[i + 1]}"
    local lineno="${BASH_LINENO[i]}"
    log error "  at ${func} (${source}:${lineno})"
  done

  exit ${EXIT_FAIL:-1}
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
  if [[ -n ${script_home} && -d ${script_home} ]]; then
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

# Define core count function for cross-platform compatibility
function get_core_count() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  elif command -v sysctl >/dev/null 2>&1 && [[ "$(uname)" == "Darwin" ]]; then
    sysctl -n hw.ncpu
  else
    echo "1" # Default to 1 if can't determine
  fi
}

# Utility helper functions
function safe_pushd() {
  local dir=$1
  pushd "${dir}" >/dev/null 2>&1 || return ${RETURN_FAILURE:-1}
}

function safe_popd() {
  popd >/dev/null 2>&1 || return ${RETURN_FAILURE:-1}
}

function ensure_dir() {
  local dir=$1
  [ -d "${dir}" ] || mkdir -p "${dir}"
}

function env_append() {
  local env_name=$1
  local new_value=$2
  local separator=${3:-:}

  # Validate required parameters
  if [ -z "${env_name}" ] || [ -z "${new_value}" ]; then
    log error "Usage: env_append <env_name> <new_value> [separator]"
    return ${RETURN_FAILURE:-1}
  fi

  # Get current environment variable value
  local current_value
  eval "current_value=\$${env_name}"

  # If environment variable is empty, just set the new value
  if [ -z "${current_value}" ]; then
    export "${env_name}=${new_value}"
    return ${RETURN_SUCCESS:-0}
  fi

  # Check if new_value already exists in current_value
  local temp_string="${separator}${current_value}${separator}"
  local search_string="${separator}${new_value}${separator}"

  if [[ ${temp_string} == *"${search_string}"* ]]; then
    # Value already exists, no need to add
    log debug "Value '${new_value}' already exists in ${env_name}"
    return ${RETURN_SUCCESS:-0}
  fi

  # Append new value to the environment variable
  export "${env_name}=${new_value}${separator}${current_value}"

  # Automatically prune duplicates after appending
  env_prune "${env_name}" "${separator}"

  return ${RETURN_SUCCESS:-0}
}

function env_prune() {
  local env_name=$1
  local separator=${2:-:}

  # Validate required parameters
  if [ -z "${env_name}" ]; then
    log error "Usage: env_prune <env_name> [separator]"
    return ${RETURN_FAILURE:-1}
  fi

  # Get current environment variable value
  local current_value
  eval "current_value=\$${env_name}"

  # If environment variable is empty, nothing to do
  if [ -z "${current_value}" ]; then
    log debug "Environment variable '${env_name}' is empty, nothing to prune"
    return ${RETURN_SUCCESS:-0}
  fi

  # Split the value into array using the separator
  local IFS="${separator}"
  local -a items
  read -ra items <<<"${current_value}"

  # Remove duplicates while preserving order (first occurrence wins)
  local -a unique_items
  local item
  local seen_items=""

  for item in "${items[@]}"; do
    # Skip empty items
    if [ -n "${item}" ]; then
      # Check if item already seen using string matching (bash 3.x compatible)
      if [[ ${seen_items} != *":${item}:"* ]]; then
        unique_items+=("${item}")
        seen_items="${seen_items}:${item}:"
      fi
    fi
  done

  # Join the unique items back together
  local pruned_value
  if [ ${#unique_items[@]} -gt 0 ]; then
    # Join array elements with separator
    local IFS="${separator}"
    pruned_value="${unique_items[*]}"
  else
    pruned_value=""
  fi

  # Update the environment variable
  export "${env_name}=${pruned_value}"

  log debug "Pruned '${env_name}' from ${#items[@]} to ${#unique_items[@]} items"
  return ${RETURN_SUCCESS:-0}
}

function load_map() {
  local map_name=$1
  local file_path=$2

  if [ -z "${file_path}" ]; then
    log error "Usage: load_map <file_path> [map_name]"
    return ${RETURN_FAILURE:-1}
  fi

  if [ ! -f "${file_path}" ]; then
    log error "File not found: ${file_path}"
    return ${RETURN_FAILURE:-1}
  fi

  # If map name is not provided, derive it from the filename
  if [ -z "${map_name}" ]; then
    local filename=$(basename -- "${file_path}")
    map_name="${filename%%.*}"
    # Replace valid variable name chars (only alphanumeric and underscore allowed)
    map_name=${map_name//[^a-zA-Z0-9_]/_}
  fi

  # Create associative array if it doesn't exist
  if ! declare -p "${map_name}" >/dev/null 2>&1; then
    # Try global declaration (Bash 4.2+)
    if ! eval "declare -gA ${map_name}" 2>/dev/null; then
       eval "declare -A ${map_name}"
    fi
  fi

  while read -r key value; do
    # Skip comments and empty lines
    [[ "${key}" =~ ^#.*$ ]] && continue
    [[ -z "${key}" ]] && continue

    # Store in the associative array
    eval "${map_name}[\"${key}\"]=\"${value}\""
  done < "${file_path}"

  return ${RETURN_SUCCESS:-0}
}
