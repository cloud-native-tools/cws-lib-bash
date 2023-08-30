function vscode_workspace_setup() {
  local workspace_file=${1:-${VSCODE_DEFAULT_WORKSPACE}}
  local project_root=${2:-${PROJECTS_ROOT:-${WORK_DIR}}}
  if [ ! -f ${workspace_file} ]; then
    echo '{}' | jq ".folders = [{\"path\": \"${DOCKER_DIR}\"}]" >${workspace_file}
  fi

  main_projects=$(find ${project_root} -maxdepth 1 -mindepth 1 -type d ${PROJECTS_CONDITION})
  sub_projects=$({
    for module in $(find ${main_projects} -name .gitmodules); do
      module_dir=$(dirname ${module})
      pushd ${module_dir} >/dev/null 2>&1
      cat .gitmodules | grep -E '^\s*path\s*=' | awk '{print "'${module_dir}'/"$NF}'
      popd >/dev/null 2>&1
    done
  } || true)
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
  sub_projects_json=$({
    if [ -n "${sub_projects}" ]; then
      ls -1d ${sub_projects} |
        xargs realpath |
        grep -E "${PROJECTS_INCLUDE:-.*}" |
        grep -vE "${PROJECTS_EXCLUDE:-.*}" |
        grep -vE '^$' |
        sort |
        uniq |
        jq -R '{"path":.}' |
        jq -s .
    else
      echo '[]'
    fi
  } || true)
  cat ${workspace_file} | jq ".folders |= . + ${main_projects_json}" | jq ".folders |= . + ${sub_projects_json}" >${workspace_file}.new
  mv -fv ${workspace_file}.new ${workspace_file}
}
