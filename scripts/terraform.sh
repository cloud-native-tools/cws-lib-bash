TF_PLAN_OUT="plan.out"
TF_INIT_ANSI="init.ansi"
TF_PLAN_ANSI="plan.ansi"
TF_APPLY_ANSI="apply.ansi"
TF_DESTROY_ANSI="destroy.ansi"

function tf_read_yaml() {
  local yaml_file=${1}
  if [ -z "${yaml_file}" ] || [ ! -f "${yaml_file}" ]; then
    log error "Usage: terraform_read_yaml <yaml_file>"
    return ${RETURN_FAILURE}
  fi
  echo "yamldecode(file(\"${yaml_file}\"))" | terraform console
}

function tf_read_json() {
  local json_file=${1}
  if [ -z "${json_file}" ] || [ ! -f "${json_file}" ]; then
    log error "Usage: terraform_read_json <json_file>"
    return ${RETURN_FAILURE}
  fi
  echo "jsondecode(file(\"${json_file}\"))" | terraform console
}

function tf_format() {
  local target=${1:-${PWD}}
  for d in $(find ${target} -name '*.tf' -type f | grep -vE "/\.terraform" | xargs dirname | sort | uniq); do
    pushd ${d} >/dev/null 2>&1
    log info "Formatting terraform files in ${PWD}"
    terraform fmt
    popd >/dev/null 2>&1
  done
}

function tf_cut_tf_file() {
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
  rm -rfv cut.awk
}

function tf_clean_unused_tf_files() {
  local tf_dir="${1:-${PWD}}"
  for p_dir in $(find ${tf_dir} -name '*.tf' | xargs dirname | sort | uniq); do
    if [ -f "${p_dir}/provider.tf" ]; then
      if [ -f "${p_dir}/variable.tf" ] || [ -f "${p_dir}/data.tf" ] || [ -f "${p_dir}/resource.tf" ] || [ -f "${p_dir}/output.tf" ]; then
        pushd ${p_dir} >/dev/null 2>&1
        for t in *.tf; do
          case $t in
          variable.tf | provider.tf | data.tf | resource.tf | output.tf) ;;
          *)
            rm -fv $t
            ;;
          esac
        done
        popd >/dev/null 2>&1
      fi
    else
      rm -rfv ${p_dir}
    fi
  done
}

function tf_clean_plan_files() {
  log notice "clean terraform plan files in ${PWD}"
  find . -type f \
    -name "${TF_PLAN_OUT}" \
    -or \
    -name "${TF_INIT_ANSI}" \
    -or \
    -name "${TF_PLAN_ANSI}" \
    -or \
    -name "${TF_APPLY_ANSI}" \
    -or \
    -name "${TF_DESTROY_ANSI}" | xargs rm -rfv
}

function tf_plan() {
  log notice "terraform plan in ${PWD}"
  if ! terraform init -upgrade >${TF_INIT_ANSI} 2>&1; then
    log error "Failed to initialize terraform in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  if ! terraform plan -out=${TF_PLAN_OUT} >${TF_PLAN_ANSI} 2>&1; then
    log error "Failed to create terraform plan in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  if !terraform show ${TF_PLAN_OUT} >${TF_PLAN_ANSI}; then
    log error "Failed to show terraform plan in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_apply() {
  log notice "terraform apply in ${PWD}"
  if [ ! -f "${TF_PLAN_OUT}" ]; then
    log warn "no ${TF_PLAN_OUT} found in ${PWD}, run terraform plan first"
    tf_plan
  fi
  if ! terraform apply -auto-approve ${TF_PLAN_OUT} >${TF_APPLY_ANSI} 2>&1; then
    log error "Failed to apply terraform in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_destroy() {
  log notice "terraform destroy in ${PWD}"
  if ! terraform init -upgrade >${TF_INIT_ANSI} 2>&1; then
    log error "Failed to initialize terraform in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  if ! terraform destroy -auto-approve >${TF_DESTROY_ANSI} 2>&1; then
    log error "Failed to destroy terraform in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_plan_and_apply() {
  local target_dir="${1}"
  if [ -n "${target_dir}" ]; then
    shift
    if ! pushd ${target_dir} >/dev/null 2>&1; then
      log error "Failed to change directory to ${target_dir}"
      return ${RETURN_FAILURE:-1}
    fi
  fi
  if ! tf_plan $@ || ! tf_apply $@; then
    log error "Failed to plan and apply terraform in ${PWD}"
  fi
  if [ -n "${target_dir}" ]; then
    if ! popd >/dev/null 2>&1; then
      log error "Failed to return to the previous directory"
      return ${RETURN_FAILURE:-1}
    fi
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_plan_and_destroy() {
  local target_dir="${1}"
  if [ -n "${target_dir}" ]; then
    shift
    if ! pushd ${target_dir} >/dev/null 2>&1; then
      log error "Failed to change directory to ${target_dir}"
      return ${RETURN_FAILURE:-1}
    fi
  fi
  if ! tf_plan $@ || ! tf_destroy $@; then
    log error "Failed to plan and destroy terraform in ${PWD}"
  fi
  if [ -n "${target_dir}" ]; then
    if ! popd >/dev/null 2>&1; then
      log error "Failed to return to the previous directory"
      return ${RETURN_FAILURE:-1}
    fi
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_extract_example() {
  find . \( -name '*.md' -or -name '*.markdown' \) -type f | xargs -I{} sed -n '/^```terraform$/,/^```$/p' {} | grep -v '^```' | sed '/^$/d'
}

function tf_replace() {
  local resource_id="${1}"
  if [ -z "${resource_id}" ]; then
    log error "Usage: terraform_replace <resource_id>"
    return ${RETURN_FAILURE:-1}
  else
    shift
  fi
  terraform apply -replace="${resource_id}" $@
}

function tf_validate_module() {
  find . -name '*.tf' -type f | xargs grep -E '\s+source\s+=' | grep -v '/provider.tf:' | grep '\.\./' | sort | uniq | sed -Er 's/^([^:]+):[^"]+"([^"]+)"/\1 \2/g' | while read -r tf_file tf_reference; do
    pushd $(dirname ${tf_file}) >/dev/null 2>&1
    if [ -d "${tf_reference}" ]; then
      log notice "${tf_file} -> ${tf_reference}"
    else
      log error "${tf_file} -> ${tf_reference}"
    fi
    popd >/dev/null 2>&1
  done
}

function tf_failed_plan() {
  find . -name ${TF_PLAN_ANSI} | xargs ls -lh | awk '$5!=0{print}'
}

function tf_failed_apply() {
  find . -name ${TF_APPLY_ANSI} | xargs ls -lh | awk '$5!=0{print}'
}

function tf_failed_destroy() {
  find . -name ${TF_DESTROY_ANSI} | xargs ls -lh | awk '$5!=0{print}'
}

function tf_find_module() {
  find . -name '*.tf' -type f |
    grep -vE 'output\.tf|provider\.tf|variable\.tf' |
    xargs grep -EIn '^\s+source\s+=\s+' |
    awk '{print $1,$NF}' |
    tr -d '"' |
    while IFS= read -r item; do
      if [ -d "${item/* /}" ]; then
        log notice "${item/ */} [${item/* /}] found"
      else
        log error "${item/ */} [${item/* /}] not found"
      fi
    done
}
