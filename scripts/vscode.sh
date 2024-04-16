function vscode_workspace_setup() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE:-work.code-workspace}}
  local project_root=${2:-${PROJECTS_ROOT:-${WORK_DIR}}}
  if [ -z "${workspace_file}" ]; then
    log warn "skip setup vscode workspace when workspace_file is empty" >&2
    return ${RETURN_SUCCESS}
  fi
  if [ ! -f ${workspace_file} ]; then
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

function vscode_ext_list() {
  local ext_list_file=$@
  if [ -z "${ext_list_file}" ]; then
    code --list-extensions --show-versions
  else
    if [ -f ${ext_list_file} ]; then
      cat ${ext_list_file}
    else
      echo $@
    fi
  fi
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
