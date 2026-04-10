# shellcheck shell=bash

# NOTE:
# Functions consumed via command substitution (e.g. var=$(func ...)) MUST keep
# stdout clean and stable. Do not add verbose/debug output (such as mv -v, echo
# debug logs, etc.) in these functions, otherwise callers may capture corrupted
# values. If diagnostics are needed, write to stderr.

function _vscode_workspace_ensure_file() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local tmp_file

  if [ -z "${workspace_file}" ]; then
    log warn "skip setup vscode workspace when workspace_file is empty" >&2
    return "${RETURN_FAILURE}"
  fi

  if [ ! -f "${workspace_file}" ] || [ ! -s "${workspace_file}" ]; then
    echo '{}' >"${workspace_file}"
  fi

  tmp_file="${workspace_file}.tmp"
  cat "${workspace_file}" |
    jq ".folders |= (. // []) | .settings |= (. // {})" >"${tmp_file}"
  mv -f "${tmp_file}" "${workspace_file}"

  echo "${workspace_file}"
}

function _vscode_workspace_apply_jq() {
  local workspace_file=${1}
  local jq_expr=${2}
  local tmp_file="${workspace_file}.tmp"

  cat "${workspace_file}" | jq "${jq_expr}" >"${tmp_file}"
  mv -f "${tmp_file}" "${workspace_file}"
}

function _vscode_workspace_dirs_to_json() {
  sort |
    uniq |
    grep -vE '^$' |
    jq -R . |
    jq -s .
}

function vscode_workspace_setup() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local project_root=${2:-${VSCODE_PROJECT_ROOT:-${WORK_DIR:-${PWD}}}}
  local resolved_workspace_file
  local main_projects
  local main_projects_json

  resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}") || return "${RETURN_SUCCESS}"

  # shellcheck disable=SC2086
  main_projects=$(find "${project_root}" -maxdepth 1 -mindepth 1 -type d ${VSCODE_PROJECT_FILTER})
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

  _vscode_workspace_apply_jq "${resolved_workspace_file}" ".folders |= . + ${main_projects_json}"
}

function vscode_workspace_add_folder() {
  local workspace_file=${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}
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

  resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"
  folder_json=$(
    for folder_path in "$@"; do
      if [ -d "${folder_path}" ]; then
        realpath "${folder_path}"
      fi
    done |
      jq -R '{"path":.}' |
      jq -s .
  )
  _vscode_workspace_apply_jq "${resolved_workspace_file}" ".folders |= . + ${folder_json}"
}

function vscode_workspace_add_python_search_paths() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local python_src_folders_json

  resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  python_src_folders_json=$({
    find "${search_root}" -name '*.py' -type f |
      while IFS= read -r py_file; do
        dirname "${py_file}"
      done |
      _vscode_workspace_dirs_to_json
  } || true)

  _vscode_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"python.analysis.extraPaths\" = ${python_src_folders_json}"
}

function vscode_workspace_add_rust_search_paths() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local rust_src_folders_json

  resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  rust_src_folders_json=$({
    find "${search_root}" -name 'Cargo.toml' -type f |
      _vscode_workspace_dirs_to_json
  } || true)

  _vscode_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"rust-analyzer.linkedProjects\" = ${rust_src_folders_json}"
}

function vscode_workspace_add_golang_search_paths() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local golang_src_folders_json

  resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

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

  _vscode_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"gopls\" |= (. // {}) | .settings.\"gopls\".\"directoryFilters\" = ${golang_src_folders_json}"
}

function vscode_workspace_add_c_search_paths() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local search_root=${2:-.}
  local resolved_workspace_file
  local c_src_folders_json

  resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}") || return "${RETURN_FAILURE}"

  c_src_folders_json=$({
    find "${search_root}" -type f \( -name '*.h' -o -name '*.hh' -o -name '*.hpp' -o -name '*.hxx' -o -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.cxx' \) |
      while IFS= read -r c_file; do
        dirname "${c_file}"
      done |
      _vscode_workspace_dirs_to_json
  } || true)

  _vscode_workspace_apply_jq "${resolved_workspace_file}" ".settings |= (. // {}) | .settings.\"C_Cpp.default.includePath\" = ${c_src_folders_json}"
}

function vscode_bin() {
  local code_bin="code"

  # Check for VS Code Server (remote SSH scenario)
  if [[ $OSTYPE == "linux-gnu"* ]]; then
    # First check for VS Code Server remote-cli in user home directory
    local vscode_server_dir="${HOME}/.vscode-server"
    if [ -d "${vscode_server_dir}" ]; then
      local remote_cli_bin=$(find "${vscode_server_dir}" -path "*/remote-cli/code" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo "${code_bin}"
        return
      fi
      # Fallback to any code-* executable in the server directory
      local server_bin=$(find "${vscode_server_dir}" -name "code-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo "${code_bin}"
        return
      fi
    fi

    # Check for system-wide VS Code Server
    if [ -d "/root/.vscode-server" ]; then
      local remote_cli_bin=$(find "/root/.vscode-server" -path "*/remote-cli/code" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo "${code_bin}"
        return
      fi
      # Fallback to any code-* executable in the server directory
      local server_bin=$(find "/root/.vscode-server" -name "code-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo "${code_bin}"
        return
      fi
    fi
  fi

  if [ -f "${VSCODE_SERVER_HOME}/bin/code-server" ]; then
    code_bin="${VSCODE_SERVER_HOME}/bin/code-server"
  elif [ -f "${CODE_SERVER_HOME}/bin/code-server" ]; then
    code_bin="${CODE_SERVER_HOME}/bin/code-server"
  else
    if [[ $OSTYPE == "linux-gnu"* ]]; then
      code_bin="code"
    elif [[ $OSTYPE == "darwin"* ]]; then
      code_bin="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
    elif [[ $OSTYPE == "cygwin" ]]; then
      code_bin="/cygdrive/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code/bin/code"
    elif [[ $OSTYPE == "msys" ]]; then
      code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code/bin/code"
    elif [[ $OSTYPE == "win32" ]]; then
      code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code/bin/code"
    fi
  fi
  echo "${code_bin}"
}

function vscode_insiders_get_bin() {
  local code_bin="code-insiders"

  # Check for VS Code Insiders Server (remote SSH scenario)
  if [[ $OSTYPE == "linux-gnu"* ]]; then
    # First check for VS Code Insiders Server remote-cli in user home directory
    local vscode_server_dir="${HOME}/.vscode-server-insiders"
    if [ -d "${vscode_server_dir}" ]; then
      local remote_cli_bin=$(find "${vscode_server_dir}" -path "*/remote-cli/code-insiders" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo "${code_bin}"
        return
      fi
      # Fallback to any code-insiders-* executable in the server directory
      local server_bin=$(find "${vscode_server_dir}" -name "code-insiders-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo "${code_bin}"
        return
      fi
    fi

    # Check for system-wide VS Code Insiders Server
    if [ -d "/root/.vscode-server-insiders" ]; then
      local remote_cli_bin=$(find "/root/.vscode-server-insiders" -path "*/remote-cli/code-insiders" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo "${code_bin}"
        return
      fi
      # Fallback to any code-insiders-* executable in the server directory
      local server_bin=$(find "/root/.vscode-server-insiders" -name "code-insiders-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo "${code_bin}"
        return
      fi
    fi

    # Fallback to regular code-insiders command
    code_bin="code-insiders"
  elif [[ $OSTYPE == "darwin"* ]]; then
    code_bin="/Applications/Visual Studio Code - Insiders.app/Contents/Resources/app/bin/code"
  elif [[ $OSTYPE == "cygwin" ]]; then
    code_bin="/cygdrive/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders"
  elif [[ $OSTYPE == "msys" ]]; then
    code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders"
  elif [[ $OSTYPE == "win32" ]]; then
    code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders"
  fi
  echo "${code_bin}"
}

function vscode_open() {
  local vscode_bin=$(vscode_bin)
  "${vscode_bin}" -r "$@"
}

function vscode_insiders_open() {
  local vscode_bin=$(vscode_insiders_get_bin)
  "${vscode_bin}" -r "$@"
}

function vscode_ext_list() {
  local vscode_bin=$(vscode_bin)
  local ext_list_file=${1:-}
  if [ -z "${ext_list_file}" ]; then
    "${vscode_bin}" --list-extensions --show-versions
  else
    if [ -f "${ext_list_file}" ]; then
      cat "${ext_list_file}"
    else
      printf '%s\n' "$@"
    fi
  fi
}

function vscode_insiders_ext_list() {
  local vscode_bin=$(vscode_insiders_get_bin)
  local ext_list_file=${1:-}
  if [ -z "${ext_list_file}" ]; then
    "${vscode_bin}" --list-extensions --show-versions
  else
    if [ -f "${ext_list_file}" ]; then
      cat "${ext_list_file}"
    else
      printf '%s\n' "$@"
    fi
  fi
}

function vscode_ext_install() {
  local vscode_bin=$(vscode_bin)
  local ext
  for ext in "$@"; do
    "${vscode_bin}" --install-extension "${ext}"
  done
}

function vscode_ext_update() {
  local vscode_bin=$(vscode_bin)
  "${vscode_bin}" --update-extensions
}

function vscode_insiders_ext_install() {
  local vscode_bin=$(vscode_insiders_get_bin)
  local ext
  for ext in "$@"; do
    "${vscode_bin}" --install-extension "${ext}" --ignore-certificate-errors
  done
}

function vscode_insiders_ext_update() {
  local vscode_bin=$(vscode_insiders_get_bin)
  "${vscode_bin}" --update-extensions --ignore-certificate-errors
}

function vscode_ext_url() {
  local ext=${1}
  local publisher=$(echo "${ext}" | awk -F. '{print $1}')
  local name=$(echo "${ext}" | awk -F. '{print $2}' | awk -F@ '{print $1}')
  local version=$(echo "${ext}" | awk -F@ '{print $NF}')
  local vsix_url="https://marketplace.visualstudio.com/_apis/public/gallery/publishers/${publisher}/vsextensions/${name}/${version}/vspackage"
  echo "${vsix_url}"
}

function vscode_ext_download_scripts() {
  local ext
  vscode_ext_list "$@" |
    while IFS= read -r ext; do
      [ -n "${ext}" ] || continue
      echo "curl ${CURL_VERBOSE_OPTS} ${CURL_RETRY_OPTS} -o ${ext}.vsix $(vscode_ext_url "${ext}")"
    done
}

function vscode_ext_download_all() {
  vscode_ext_download_scripts "$@" | bash
}
