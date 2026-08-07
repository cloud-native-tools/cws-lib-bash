export CURL_VERBOSE_OPTS="--progress-bar --show-error"

if [ "${BASH_OS}" = "darwin" ]; then
  export CURL_DOWNLOAD_OPTS="--compressed --insecure"
else
  export CURL_DOWNLOAD_OPTS="--location --compressed --insecure"
fi
export CURL_RETRY_OPTS="--retry 5 --retry-delay 1"
export CURL_FAILED_OPTS="--fail --continue-at -"
export CURL_FETCH_OPTS="--silent --insecure --connect-timeout 1"

function curl_download() {
  curl ${CURL_VERBOSE_OPTS} ${CURL_DOWNLOAD_OPTS} ${CURL_RETRY_OPTS} ${CURL_FAILED_OPTS} $@
}

function curl_download_to_file() {
  local file=${1}
  local url=${2}
  if [ -z "${file}" ] || [ -z "${url}" ]; then
    log warn "Usage: curl_download_to_file <file> <url>"
  else
    curl_download -o "${file}" "${url}"
  fi
}

function curl_download_to_dir() {
  local dir=${1}
  local url=${2}
  local rename=${3}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log warn "Usage: curl_download_to_dir <dir> <url> [rename]"
  else
    if [ -z "${rename}" ]; then
      curl_download -O --output-dir "${dir}" "${url}"
    else
      curl_download -o "${rename}" --output-dir "${dir}" "${url}"
    fi
  fi
}

function curl_run_shell() {
  local url=${1}
  if [ -z "${url}" ]; then
    log warn "Usage: curl_run_shell <url>"
  else
    curl -o- ${url} | bash
  fi
}

function curl_fetch() {
  curl ${CURL_FETCH_OPTS} $@
}

function curl_detect() {
  curl -s -o /dev/null -w "%{http_code}" $@
}

function curl_available() {
  local http_status=$(curl_detect ${1})
  if [ "${http_status}" = "200" ]; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

function curl_mirror_file() {
  local url=${1}
  local dir=${2:-${REPO_DIR:-/oss_code/repo}}
  local path=$(dirname $(echo ${url} | sed 's@https\?://[^/]*/@@g'))
  if [ -z "${url}" ]; then
    log warn "Usage: download_file [url] "
    return ${RETURN_FAILURE:-1}
  else
    local status=${RETURN_SUCCESS:-0}
    mkdir -p ${dir}/${path}
    pushd ${dir}/${path} >/dev/null 2>&1
    # ${CURL_FAILED_OPTS} carries --continue-at -, so an already-complete file makes
    # curl request a range past EOF: the server answers 416 and --fail exits 22 even
    # though nothing is wrong. Capture the status code and treat 416 as already-mirrored.
    local http_code
    http_code=$(curl_download -O --write-out '%{http_code}' ${url})
    local rc=$?
    if [ "${rc}" -eq 0 ]; then
      log notice "download [${url}] into [${dir}/${path}] success"
    elif [ "${http_code}" = "416" ]; then
      log notice "download [${url}] into [${dir}/${path}] already complete (http 416)"
    else
      log error "download [${url}] into [${dir}/${path}] failed (exit ${rc}, http ${http_code})"
      status=${RETURN_FAILURE:-1}
    fi
    popd >/dev/null 2>&1
    echo "${url} -> ${dir}/${path}"
    return ${status}
  fi
}

function curl_test_server() {
  local url=${1}
  if [ -z "${url}" ]; then
    log error "Usage: curl_test_server <url>"
    return ${RETURN_FAILURE}
  fi
  if curl -o /dev/null -s ${url}; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}
