function terraform_alicloud_valid() {
  if [ -z "${ALICLOUD_ACCESS_KEY}" ] || [ -z "${ALICLOUD_SECRET_KEY}" ]; then
    log error "enviroment variable ALICLOUD_ACCESS_KEY or ALICLOUD_SECRET_KEY is not set."
    return ${RETURN_FAILURE}
  else
    return ${RETURN_SUCCESS}
  fi
}

function terraform_init() {
  local workdir=${1:-${PWD}}
  if [ -z "${TERRAFORM_PROVIDER_HOME}" ]; then
    terraform -chdir=${workdir} init
  else
    terraform -chdir=${workdir} init -plugin-dir=${TERRAFORM_PROVIDER_HOME}
  fi
}

function terraform_plan() {
  local workdir=${1:-${PWD}}
  if [ -z "${TERRAFORM_PROVIDER_HOME}" ]; then
    terraform -chdir=${workdir} plan
  else
    terraform -chdir=${workdir} plan -plugin-dir=${TERRAFORM_PROVIDER_HOME}
  fi
}

function terraform_apply() {
  local workdir=${1:-${PWD}}
  if [ -z "${TERRAFORM_PROVIDER_HOME}" ]; then
    terraform -chdir=${workdir} apply
  else
    terraform -chdir=${workdir} apply -plugin-dir=${TERRAFORM_PROVIDER_HOME}
  fi
}

function terraform_read_yaml() {
  local yaml_file=${1}
  if [ -z "${yaml_file}" ] || [ ! -f "${yaml_file}" ]; then
    log error "Usage: terraform_read_yaml <yaml_file>"
    return ${RETURN_FAILURE}
  fi
  echo "yamldecode(file(\"${yaml_file}\"))" | terraform console
}

function terraform_read_json() {
  local json_file=${1}
  if [ -z "${json_file}" ] || [ ! -f "${json_file}" ]; then
    log error "Usage: terraform_read_json <json_file>"
    return ${RETURN_FAILURE}
  fi
  echo "jsondecode(file(\"${json_file}\"))" | terraform console
}
