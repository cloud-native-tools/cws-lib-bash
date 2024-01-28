function vscode_workspace_setup() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE}}
  local project_root=${2:-${PROJECTS_ROOT:-${WORK_DIR}}}
  if [ -z "${workspace_file}" ]; then
    log warn "skip setup vscode workspace when workspace_file is empty" >&2
    return ${RETURN_FAILURE}
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
  local workspace_file=${2:-${VSCODE_DEFAULT_WORKSPACE}}
  if [ ! -f ${workspace_file} ]; then
    echo '{}' | jq ".folders = []" >${workspace_file}
  fi
  cat ${workspace_file} | jq ".folders |= . + $(realpath ${folder_path} | jq -R '{"path":.}' | jq -s .)" >${workspace_file}.tmp
  mv -fv ${workspace_file}.tmp ${workspace_file}
}
