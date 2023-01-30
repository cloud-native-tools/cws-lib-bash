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
  if [ ! -d ${helm_repo_url} ]; then
    log info "[${helm_repo_url}] is not a local directory, assuming it's a remote repo "
    local helm_chart_name="${2}"
    local helm_repo_name="${3}"
    local helm_deploy_name="${4}"
    local namespace_prefix="${5:-${helm_deploy_name}}"
    local context_name="${6:-workspace}"
    if ! helm repo add ${helm_repo_name} ${helm_repo_url}; then
      log error "add remote helm repo [${helm_repo_name}] failed from [${helm_repo_url}]"
      return
    fi
    log info "use remote helm chart [${helm_chart_name}@${helm_repo_url}] as [${helm_deploy_name}@${helm_repo_name}]"
  else
    local helm_deploy_name="${2}"
    local namespace_prefix="${3:-${helm_deploy_name}}"
    local context_name="${4:-workspace}"
    log info "use local helm chart [${helm_deploy_name}@${helm_repo_url}]"
  fi

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

  if [ ! -d ${helm_repo_url} ]; then
    if [ ! -d ${chart_dir}/${helm_chart_name} ]; then
      helm pull --untar --untardir ${chart_dir} ${chart_name}
    fi
    local_chart_path="$(realpath ${chart_dir}/$(basename ${chart_name}))"
  else
    if [ -d ${chart_dir}/${helm_chart_name} ]; then
      cp -rf ${helm_repo_url} ${chart_dir}/${helm_chart_name}/${helm_deploy_name}
    fi
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
  if [ -f ${manifest_file} ]; then
    cws_cmdline kubernetes-break-manifest ${manifest_file} ${manifest_dir}/${helm_deploy_name}
    local crds_manifest_file=${manifest_dir}/${helm_deploy_name}-crds.yaml
    if [ -d ${local_chart_path}/crds ]; then
      cws_cmdline kubernetes-merge-manifest -o ${crds_manifest_file} ${local_chart_path}/crds
      cws_cmdline kubernetes-break-manifest ${crds_manifest_file} ${manifest_dir}/${helm_deploy_name}
    fi
  else
    log error "helm template failed @ ${manifest_file}"
  fi

  local namespace_dir="${manifest_dir}/${helm_deploy_name}/011_Namespace"
  if [ ! -d "${namespace_dir}" ]; then
    log info "no namespace @ ${namespace_dir}, generate it."
    mkdir -p ${namespace_dir}
    kubectl create namespace --dry-run=client -o yaml "${namespace_prefix}-${helm_deploy_name}" > ${namespace_dir}/${namespace_prefix}-${helm_deploy_name}.yaml
  fi
}
