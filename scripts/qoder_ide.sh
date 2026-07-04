# shellcheck shell=bash

# Qoder IDE - 基于 VSCode 的 IDE 程序
# 二进制命令：qoder（通过 .qoder-server 远程 CLI 或本地安装）
# 与 qoder_cli.sh 中的 qodercli 命令行 Agent 严格区分

# NOTE:
# Functions consumed via command substitution (e.g. var=$(func ...)) MUST keep
# stdout clean and stable. Do not add verbose/debug output (such as mv -v, echo
# debug logs, etc.) in these functions, otherwise callers may capture corrupted
# values. If diagnostics are needed, write to stderr.

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

function _qoder_ide_workspace_replace_file() {
  local src_file=${1}
  local dest_file=${2}

  command mv -f -- "${src_file}" "${dest_file}" >/dev/null
}

function _qoder_ide_workspace_ensure_file() {
  local workspace_file=${1:-${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local tmp_file

  if [ -z "${workspace_file}" ]; then
    log warn "skip setup qoder ide workspace when workspace_file is empty" >&2
    return "${RETURN_FAILURE}"
  fi

  if [ ! -f "${workspace_file}" ] || [ ! -s "${workspace_file}" ]; then
    echo '{}' >"${workspace_file}"
  fi

  tmp_file="${workspace_file}.tmp"
  jq ".folders |= (. // []) | .settings |= (. // {})" "${workspace_file}" >"${tmp_file}"
  _qoder_ide_workspace_replace_file "${tmp_file}" "${workspace_file}"

  echo "${workspace_file}"
}

function _qoder_ide_workspace_apply_jq() {
  local workspace_file=${1}
  local jq_expr=${2}
  local tmp_file="${workspace_file}.tmp"

  jq "${jq_expr}" "${workspace_file}" >"${tmp_file}"
  _qoder_ide_workspace_replace_file "${tmp_file}" "${workspace_file}"
}

function _qoder_ide_workspace_dirs_to_json() {
  sort |
    uniq |
    grep -vE '^$' |
    jq -R . |
    jq -s .
}

function qoder_ide_workspace_setup() {
  local workspace_file=${1:-${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local project_root=${2:-${QODER_IDE_PROJECT_ROOT:-${WORK_DIR:-${PWD}}}}
  local resolved_workspace_file
  local main_projects
  local main_projects_json

  resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}") || return "${RETURN_SUCCESS}"

  # shellcheck disable=SC2086
  main_projects=$(find "${project_root}" -maxdepth 1 -mindepth 1 -type d ${QODER_IDE_PROJECT_FILTER})
  main_projects_json=$({
    if [ -n "${main_projects}" ]; then
      while IFS= read -r project_dir; do
        [ -n "${project_dir}" ] && realpath "${project_dir}"
      done <<<"${main_projects}" |
        jq -R '{"path":.}' |
        jq -s .
    else
      echo '[]'
    fi
  } || true)

  _qoder_ide_workspace_apply_jq "${resolved_workspace_file}" ".folders |= . + ${main_projects_json}"
}

function qoder_ide_workspace_add_folder() {
  local workspace_file=${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}
  local resolved_workspace_file
  local folder_json
  local folder_path
  local valid_folder_count=0

  if [ $# -eq 0 ]; then
    log error "missing folder path"
    return "${RETURN_FAILURE}"
  fi

  if [ -f "${1}" ] || [[ "${1}" == *.code-workspace ]]; then
    workspace_file=${1}
    shift
  fi

  if [ $# -eq 0 ]; then
    log error "missing folder path"
    return "${RETURN_FAILURE}"
  fi

  for folder_path in "$@"; do
    if [ ! -d "${folder_path}" ]; then
      log warn "skip non-directory path: ${folder_path}"
      continue
    fi
    valid_folder_count=$((valid_folder_count + 1))
  done

  if [ "${valid_folder_count}" -eq 0 ]; then
    log warn "no valid directories to add"
    return "${RETURN_SUCCESS}"
  fi

  resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"
  folder_json=$(
    for folder_path in "$@"; do
      if [ -d "${folder_path}" ]; then
        realpath "${folder_path}"
      fi
    done |
      jq -R '{"path":.}' |
      jq -s .
  )
  _qoder_ide_workspace_apply_jq "${resolved_workspace_file}" ".folders |= . + ${folder_json}"
}

function qoder_ide_workspace_add_python_search_paths() {
  local workspace_file=${1:-${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local python_src_folders_json

  resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  python_src_folders_json=$({
    find "${search_root}" -name '*.py' -type f |
      while IFS= read -r py_file; do
        dirname "${py_file}"
      done |
      _qoder_ide_workspace_dirs_to_json
  } || true)

  _qoder_ide_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"python.analysis.extraPaths\" = ${python_src_folders_json}"
}

function qoder_ide_workspace_add_rust_search_paths() {
  local workspace_file=${1:-${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local rust_src_folders_json

  resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  rust_src_folders_json=$({
    find "${search_root}" -name 'Cargo.toml' -type f |
      _qoder_ide_workspace_dirs_to_json
  } || true)

  _qoder_ide_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"rust-analyzer.linkedProjects\" = ${rust_src_folders_json}"
}

function qoder_ide_workspace_add_golang_search_paths() {
  local workspace_file=${1:-${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local golang_src_folders_json

  resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  golang_src_folders_json=$({
    find "${search_root}" -name 'go.mod' -type f |
      while IFS= read -r go_mod_file; do
        dirname "${go_mod_file}"
      done |
      sort |
      uniq |
      grep -vE '^$' |
      jq -R '"+" + .' |
      jq -s .
  } || true)

  _qoder_ide_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"gopls\" |= (. // {}) | .settings.\"gopls\".\"directoryFilters\" = ${golang_src_folders_json}"
}

function qoder_ide_workspace_add_c_search_paths() {
  local workspace_file=${1:-${QODER_IDE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local c_src_folders_json

  resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  c_src_folders_json=$({
    find "${search_root}" -type f \( -name '*.h' -o -name '*.hh' -o -name '*.hpp' -o -name '*.hxx' -o -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.cxx' \) |
      while IFS= read -r c_file; do
        dirname "${c_file}"
      done |
      _qoder_ide_workspace_dirs_to_json
  } || true)

  _qoder_ide_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"C_Cpp.default.includePath\" = ${c_src_folders_json}"
}

# ---------------------------------------------------------------------------
# Binary discovery
# ---------------------------------------------------------------------------

function qoder_ide_bin() {
  local qoder_bin="qoder"

  # Check for Qoder IDE Server (remote SSH scenario)
  if [[ $OSTYPE == "linux-gnu"* ]]; then
    # First check for Qoder Server remote-cli in user home directory
    local qoder_server_dir="${HOME}/.qoder-server"
    if [ -d "${qoder_server_dir}" ]; then
      local remote_cli_bin=$(find "${qoder_server_dir}" -path "*/remote-cli/qoder" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        qoder_bin="${remote_cli_bin}"
        echo "${qoder_bin}"
        return
      fi
      # Fallback to any qoder-* executable in the server directory
      local server_bin=$(find "${qoder_server_dir}" -name "qoder-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        qoder_bin="${server_bin}"
        echo "${qoder_bin}"
        return
      fi
    fi

    # Check for system-wide Qoder Server
    if [ -d "/root/.qoder-server" ]; then
      local remote_cli_bin=$(find "/root/.qoder-server" -path "*/remote-cli/qoder" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        qoder_bin="${remote_cli_bin}"
        echo "${qoder_bin}"
        return
      fi
      # Fallback to any qoder-* executable in the server directory
      local server_bin=$(find "/root/.qoder-server" -name "qoder-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        qoder_bin="${server_bin}"
        echo "${qoder_bin}"
        return
      fi
    fi
  fi

  if [ -f "${QODER_IDE_SERVER_HOME}/bin/qoder-server" ]; then
    qoder_bin="${QODER_IDE_SERVER_HOME}/bin/qoder-server"
  elif [ -f "${QODER_SERVER_HOME}/bin/qoder-server" ]; then
    qoder_bin="${QODER_SERVER_HOME}/bin/qoder-server"
  else
    if [[ $OSTYPE == "linux-gnu"* ]]; then
      qoder_bin="qoder"
    elif [[ $OSTYPE == "darwin"* ]]; then
      qoder_bin="/Applications/Qoder.app/Contents/Resources/app/bin/qoder"
    elif [[ $OSTYPE == "cygwin" ]]; then
      qoder_bin="/cygdrive/c/Users/$(whoami)/AppData/Local/Programs/Qoder/bin/qoder"
    elif [[ $OSTYPE == "msys" ]]; then
      qoder_bin="/c/Users/$(whoami)/AppData/Local/Programs/Qoder/bin/qoder"
    elif [[ $OSTYPE == "win32" ]]; then
      qoder_bin="/c/Users/$(whoami)/AppData/Local/Programs/Qoder/bin/qoder"
    fi
  fi
  echo "${qoder_bin}"
}

# ---------------------------------------------------------------------------
# Open / launch
# ---------------------------------------------------------------------------

function qoder_ide_open() {
  local ide_bin=$(qoder_ide_bin)
  "${ide_bin}" -r "$@"
}

# ---------------------------------------------------------------------------
# Extension management
# ---------------------------------------------------------------------------

function qoder_ide_ext_list() {
  local ide_bin=$(qoder_ide_bin)
  local ext_list_file=${1:-}
  if [ -z "${ext_list_file}" ]; then
    "${ide_bin}" --list-extensions --show-versions
  else
    if [ -f "${ext_list_file}" ]; then
      cat "${ext_list_file}"
    else
      printf '%s\n' "$@"
    fi
  fi
}

function qoder_ide_ext_install() {
  local ide_bin=$(qoder_ide_bin)
  local ext
  for ext in "$@"; do
    "${ide_bin}" --install-extension "${ext}"
  done
}

function qoder_ide_ext_update() {
  local ide_bin=$(qoder_ide_bin)
  "${ide_bin}" --update-extensions
}

function qoder_ide_ext_url() {
  local ext=${1}
  local publisher=$(echo "${ext}" | awk -F. '{print $1}')
  local name=$(echo "${ext}" | awk -F. '{print $2}' | awk -F@ '{print $1}')
  local version=$(echo "${ext}" | awk -F@ '{print $NF}')
  local vsix_url="https://marketplace.visualstudio.com/_apis/public/gallery/publishers/${publisher}/vsextensions/${name}/${version}/vspackage"
  echo "${vsix_url}"
}

function qoder_ide_ext_download_scripts() {
  local ext
  qoder_ide_ext_list "$@" |
    while IFS= read -r ext; do
      [ -n "${ext}" ] || continue
      echo "curl ${CURL_VERBOSE_OPTS} ${CURL_RETRY_OPTS} -o ${ext}.vsix $(qoder_ide_ext_url "${ext}")"
    done
}

function qoder_ide_ext_download_all() {
  qoder_ide_ext_download_scripts "$@" | bash
}
