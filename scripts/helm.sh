function helm_untar() {
  local name="$1"
  helm pull "$name" --untar
}

function helm_export_values() {
  local chart_name=$1
  local values_file=$2
  if [ -z "${values_file}" ]; then
    helm show values ${chart_name}
  else
    if [ ! -f ${values_file} ]; then
      helm show values ${chart_name} >${values_file}
    else
      echo "${values_file} exists, skipping"
    fi
  fi
}

function helm_generate() {
  local helm_repo_url="${1}"
  local helm_chart_name="${2}"
  local helm_repo_name="${3}"
  local helm_deploy_name="${4}"
  local namespace_prefix="${5}"
  local context_name="${6:-workspace}"

  local values_dir="src/helm/values"
  local chart_dir="src/helm/chart"
  local manifest_dir="dist/manifest"
  if [ -n "${context_name}" ]; then
    manifest_dir=${manifest_dir}/${context_name}
    values_dir=${values_dir}/${context_name}
  fi
  mkdir -pv ${manifest_dir} ${chart_dir} ${values_dir}

  local chart_name=${helm_repo_name}/${helm_chart_name}
  local values_file=${values_dir}/${helm_deploy_name}.yaml
  local manifest_file=${manifest_dir}/${helm_deploy_name}.yaml

  helm repo add ${helm_repo_name} ${helm_repo_url}
  if [ ! -f ${helm_repo_url} ]; then
    if [ ! -d ${chart_dir}/$(basename ${chart_name}) ]; then
      helm pull --untar --untardir ${chart_dir} ${chart_name}
    fi
    local_chart_path="$(realpath ${chart_dir}/$(basename ${chart_name}))"
  else
    local_chart_path="${helm_repo_url}"
  fi

  helm_export_values ${local_chart_path} ${values_file}
  local helm_template_cmd="helm template \
    --debug \
    --include-crds ${helm_deploy_name} \
    --namespace ${namespace_prefix}-${helm_deploy_name} \
    --values ${values_file} \
    ${local_chart_path}"

  eval ${helm_template_cmd} >${manifest_file}
  cws_cmdline kubernetes-break-manifest ${manifest_file} ${manifest_dir}/${helm_deploy_name}
  local crds_manifest_file=${manifest_dir}/${deploy_name}-crds.yaml
  if [ -d ${local_chart_path}/crds ]; then
    cws_cmdline kubernetes-merge-manifest -o ${crds_manifest_file} ${local_chart_path}/crds
    cws_cmdline kubernetes-break-manifest ${crds_manifest_file} ${manifest_dir}/${helm_deploy_name}
  fi
}
