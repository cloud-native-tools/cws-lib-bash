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

function terraform_format() {
  for d in $(find . -name '*.tf' -type f | xargs dirname | sort | uniq); do
    pushd ${d} >/dev/null 2>&1
    log info "Formatting terraform files in ${PWD}"
    terraform fmt
    popd >/dev/null 2>&1
  done
}

function terraform_cut_tf_file() {
  local tf_file="${1}"
  local tf_resource_pattern="${2:-alicloud_.*}"

  cat <<'EOF' >cut.awk
#!/usr/bin/awk

BEGIN {
  SELECTED = "false";
  OUTPUT = "NONE";
}

($1 == TYPE && $2 ~ "\""RESOURCE"\"") {
  SELECTED = "true";
  system("mkdir -pv "$2);
  OUTPUT = $2"/"$3".tf";
  gsub("\"", "", OUTPUT)
  print "output "$2" to "OUTPUT;
}

/^}/ {
  if (OUTPUT != "NONE" && SELECTED == "true") {
    print > OUTPUT;
  }
  SELECTED = "false";
}

(SELECTED == "true") {
  print > OUTPUT;
}
EOF

  for type in locals resource data; do
    awk -f cut.awk -v TYPE=${type} -v RESOURCE="${tf_resource_pattern}" ${tf_file}
  done
}
