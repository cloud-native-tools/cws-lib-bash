function jq_vscode_workspace_setup() {
  local workdir=${1:-${PWD}}
  local vscode_workspace='{"folders":[],"settings":{"build.experimentalWorkspaceModule":true}}'
  local folders=$(ls -d ${workdir}/*/|xargs realpath|jq -R '{"path":.}' | jq -s .)
  echo ${vscode_workspace} | jq ".folders |= . + ${folders}"
}
