function vscode_workspace_setup() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local project_root=${2:-${PROJECTS_ROOT:-${WORK_DIR}}}
  if [ -z "${workspace_file}" ]; then
    log warn "skip setup vscode workspace when workspace_file is empty" >&2
    return ${RETURN_SUCCESS}
  fi
  if [ ! -f ${workspace_file} ] || [ ! -s ${workspace_file} ]; then
    echo '{}' | jq ".folders = []" >${workspace_file}
  fi

  main_projects=$(find ${project_root} -maxdepth 1 -mindepth 1 -type d ${PROJECTS_CONDITION})
  main_projects_json=$({
    if [ -n "${main_projects}" ]; then
      ls -1d ${main_projects} |
        xargs realpath |
        grep -vE '^$' |
        sort |
        uniq |
        jq -R '{"path":.}' |
        jq -s .
    else
      echo '[]'
    fi
  } || true)
  cat ${workspace_file} | jq ".folders |= . + ${main_projects_json}" >${workspace_file}.new
  mv -fv ${workspace_file}.new ${workspace_file}
}

function vscode_workspace_add_folder() {
  local folder_path=${1}
  local workspace_file=${2:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}

  if [ -z "${folder_path}" ] || [ ! -d ${folder_path} ]; then
    log error "${folder_path} is not a directory"
    return ${RETURN_FAILURE}
  fi

  if [ ! -f ${workspace_file} ]; then
    echo '{}' | jq ".folders = []" >${workspace_file}
  fi
  cat ${workspace_file} | jq ".folders |= . + $(realpath ${folder_path} | jq -R '{"path":.}' | jq -s .)" >${workspace_file}.tmp
  mv -fv ${workspace_file}.tmp ${workspace_file}
}

function vscode_workspace_add_python_search_paths() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}

  if [ ! -f ${workspace_file} ]; then
    echo '{}' | jq ".folders = []" >${workspace_file}
  fi

  python_src_folders_json=$({
    find . -name '*.py' -type f |
      xargs dirname |
      sort |
      uniq |
      grep -vE '^$' |
      jq -R . |
      jq -s .
  } || true)

  cat ${workspace_file} | jq ".settings |= (. // {}) | .settings.\"python.analysis.extraPaths\" = ${python_src_folders_json}" >${workspace_file}.tmp
  mv -fv ${workspace_file}.tmp ${workspace_file}
}

function vscode_workspace_add_rust_search_paths() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}

  if [ ! -f ${workspace_file} ]; then
    echo '{}' | jq ".folders = []" >${workspace_file}
  fi

  rust_src_folders_json=$({
    find . -name 'Cargo.toml' -type f |
      sort |
      uniq |
      grep -vE '^$' |
      jq -R . |
      jq -s .
  } || true)

  cat ${workspace_file} | jq ".settings |= (. // {}) | .settings.\"rust-analyzer.linkedProjects\" = ${rust_src_folders_json}" >${workspace_file}.tmp
  mv -fv ${workspace_file}.tmp ${workspace_file}
}

function vscode_bin() {
  local code_bin="code"

  # Check for VS Code Server (remote SSH scenario)
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # First check for VS Code Server remote-cli in user home directory
    local vscode_server_dir="${HOME}/.vscode-server"
    if [ -d "${vscode_server_dir}" ]; then
      local remote_cli_bin=$(find "${vscode_server_dir}" -path "*/remote-cli/code" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo ${code_bin}
        return
      fi
      # Fallback to any code-* executable in the server directory
      local server_bin=$(find "${vscode_server_dir}" -name "code-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo ${code_bin}
        return
      fi
    fi
    
    # Check for system-wide VS Code Server
    if [ -d "/root/.vscode-server" ]; then
      local remote_cli_bin=$(find "/root/.vscode-server" -path "*/remote-cli/code" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo ${code_bin}
        return
      fi
      # Fallback to any code-* executable in the server directory
      local server_bin=$(find "/root/.vscode-server" -name "code-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo ${code_bin}
        return
      fi
    fi
  fi

  if [ -f "${VSCODE_SERVER_HOME}/bin/code-server" ]; then
    code_bin="${VSCODE_SERVER_HOME}/bin/code-server"
  elif [ -f "${CODE_SERVER_HOME}/bin/code-server" ]; then
    code_bin="${CODE_SERVER_HOME}/bin/code-server"
  else
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
      code_bin="code"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
      code_bin="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
    elif [[ "$OSTYPE" == "cygwin" ]]; then
      code_bin="/cygdrive/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code/bin/code"
    elif [[ "$OSTYPE" == "msys" ]]; then
      code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code/bin/code"
    elif [[ "$OSTYPE" == "win32" ]]; then
      code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code/bin/code"
    fi
  fi
  echo ${code_bin}
}

function vscode_insiders_get_bin() {
  local code_bin="code-insiders"

  # Check for VS Code Insiders Server (remote SSH scenario)
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # First check for VS Code Insiders Server remote-cli in user home directory
    local vscode_server_dir="${HOME}/.vscode-server-insiders"
    if [ -d "${vscode_server_dir}" ]; then
      local remote_cli_bin=$(find "${vscode_server_dir}" -path "*/remote-cli/code-insiders" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo ${code_bin}
        return
      fi
      # Fallback to any code-insiders-* executable in the server directory
      local server_bin=$(find "${vscode_server_dir}" -name "code-insiders-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo ${code_bin}
        return
      fi
    fi
    
    # Check for system-wide VS Code Insiders Server
    if [ -d "/root/.vscode-server-insiders" ]; then
      local remote_cli_bin=$(find "/root/.vscode-server-insiders" -path "*/remote-cli/code-insiders" -type f -executable 2>/dev/null | head -1)
      if [ -n "${remote_cli_bin}" ]; then
        code_bin="${remote_cli_bin}"
        echo ${code_bin}
        return
      fi
      # Fallback to any code-insiders-* executable in the server directory
      local server_bin=$(find "/root/.vscode-server-insiders" -name "code-insiders-*" -type f -executable 2>/dev/null | head -1)
      if [ -n "${server_bin}" ]; then
        code_bin="${server_bin}"
        echo ${code_bin}
        return
      fi
    fi
    
    # Fallback to regular code-insiders command
    code_bin="code-insiders"
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    code_bin="/Applications/Visual Studio Code - Insiders.app/Contents/Resources/app/bin/code"
  elif [[ "$OSTYPE" == "cygwin" ]]; then
    code_bin="/cygdrive/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders"
  elif [[ "$OSTYPE" == "msys" ]]; then
    code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders"
  elif [[ "$OSTYPE" == "win32" ]]; then
    code_bin="/c/Users/$(whoami)/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders"
  fi
  echo ${code_bin}
}

function vscode_open() {
  local vscode_bin=$(vscode_bin)
  "${vscode_bin}" -r $@
}

function vscode_insiders_open() {
  local vscode_bin=$(vscode_insiders_get_bin)
  "${vscode_bin}" -r $@
}

function vscode_ext_list() {
  local vscode_bin=$(vscode_bin)
  local ext_list_file=$@
  if [ -z "${ext_list_file}" ]; then
    "${vscode_bin}" --list-extensions --show-versions
  else
    if [ -f ${ext_list_file} ]; then
      cat ${ext_list_file}
    else
      echo $@
    fi
  fi
}

function vscode_insiders_ext_list() {
  local vscode_bin=$(vscode_insiders_get_bin)
  local ext_list_file=$@
  if [ -z "${ext_list_file}" ]; then
    "${vscode_bin}" --list-extensions --show-versions
  else
    if [ -f ${ext_list_file} ]; then
      cat ${ext_list_file}
    else
      echo $@
    fi
  fi
}

function vscode_ext_install() {
  local vscode_bin=$(vscode_bin)
  for ext in ${@}; do
    "${vscode_bin}" --install-extension ${ext}
  done
}

function vscode_ext_update() {
  local vscode_bin=$(vscode_bin)
  "${vscode_bin}" --update-extensions
}

function vscode_insiders_ext_install() {
  local vscode_bin=$(vscode_insiders_get_bin)
  for ext in ${@}; do
    "${vscode_bin}" --install-extension ${ext} --ignore-certificate-errors
  done
}

function vscode_insiders_ext_update() {
  local vscode_bin=$(vscode_insiders_get_bin)
  "${vscode_bin}" --update-extensions --ignore-certificate-errors
}

function vscode_ext_url() {
  local ext=${1}
  local publisher=$(echo ${ext} | awk -F. '{print $1}')
  local name=$(echo ${ext} | awk -F. '{print $2}' | awk -F@ '{print $1}')
  local version=$(echo $ext | awk -F@ '{print $NF}')
  local vsix_url="https://marketplace.visualstudio.com/_apis/public/gallery/publishers/${publisher}/vsextensions/${name}/${version}/vspackage"
  echo ${vsix_url}
}

function vscode_ext_download_scripts() {
  for ext in $(vscode_ext_list $@); do
    echo "curl ${CURL_VERBOSE_OPTS} ${CURL_RETRY_OPTS} -o ${ext}.vsix $(vscode_ext_url ${ext})"
  done
}

function vscode_ext_download_all() {
  vscode_ext_download_scripts $@ | bash
}
