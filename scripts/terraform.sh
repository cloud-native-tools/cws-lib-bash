TF_PLAN_OUT="plan.out"
TF_INIT_ANSI="init.ansi"
TF_PLAN_ANSI="plan.ansi"
TF_APPLY_ANSI="apply.ansi"
TF_DESTROY_ANSI="destroy.ansi"
TF_RC_FILE="tf.rc"

# Determines which Terraform binary to use, preferring tofu over terraform if available
function tf_bin() {
  if ! command -v tofu 2>&1; then
    if ! command -v terraform 2>&1; then
      command -v false
    fi
  fi
}

alias tf="$(tf_bin)"

# Reads and parses YAML files using Terraform console
function tf_read_yaml() {
  local yaml_file=${1}
  if [ -z "${yaml_file}" ] || [ ! -f "${yaml_file}" ]; then
    log error "Usage: terraform_read_yaml <yaml_file>"
    return ${RETURN_FAILURE}
  fi
  echo "yamldecode(file(\"${yaml_file}\"))" | $(tf_bin) console
}

# Reads and parses JSON files using Terraform console
function tf_read_json() {
  local json_file=${1}
  if [ -z "${json_file}" ] || [ ! -f "${json_file}" ]; then
    log error "Usage: terraform_read_json <json_file>"
    return ${RETURN_FAILURE}
  fi
  echo "jsondecode(file(\"${json_file}\"))" | $(tf_bin) console
}

function tf_format() {
  local target=${1:-${PWD}}
  for d in $(find ${target} -name '*.tf' -type f | grep -vE "/\.terraform" | xargs dirname | sort | uniq); do
    pushd ${d} >/dev/null 2>&1
    log info "Formatting $(tf_bin) files in ${PWD}"
    $(tf_bin) fmt
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
  log notice "clean $(tf_bin) plan files in ${PWD}"
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
  log notice "$(tf_bin) plan in ${PWD}"
  if ! $(tf_bin) init -upgrade >${TF_INIT_ANSI} 2>&1; then
    log error "Failed to initialize $(tf_bin) in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  if ! $(tf_bin) plan -out=${TF_PLAN_OUT} >${TF_PLAN_ANSI} 2>&1; then
    log error "Failed to create $(tf_bin) plan in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  if ! $(tf_bin) show ${TF_PLAN_OUT} >${TF_PLAN_ANSI}; then
    log error "Failed to show $(tf_bin) plan in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_apply() {
  log notice "$(tf_bin) apply in ${PWD}"
  if [ ! -f "${TF_PLAN_OUT}" ]; then
    log warn "no ${TF_PLAN_OUT} found in ${PWD}, run $(tf_bin) plan first"
    tf_plan
  fi
  if ! $(tf_bin) apply -auto-approve ${TF_PLAN_OUT} >${TF_APPLY_ANSI} 2>&1; then
    log error "Failed to apply $(tf_bin) in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_destroy() {
  log notice "$(tf_bin) destroy in ${PWD}"
  if ! $(tf_bin) init -upgrade >${TF_INIT_ANSI} 2>&1; then
    log error "Failed to initialize $(tf_bin) in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  if ! $(tf_bin) destroy -auto-approve >${TF_DESTROY_ANSI} 2>&1; then
    log error "Failed to destroy $(tf_bin) in ${PWD}"
    return ${RETURN_FAILURE:-1}
  fi
  return ${RETURN_SUCCESS:-0}
}

function tf_plan_and_apply() {
  local target_dir="${1}"
  if [ -n "${target_dir}" ]; then
    shift
    if ! pushd ${target_dir} >/dev/null 2>&1; then
      log error "Failed to change directory to [${target_dir}], current [${PWD}]"
      return ${RETURN_FAILURE:-1}
    fi
  fi
  if [ -f "${TF_RC_FILE}" ]; then
    log notice "found a [${TF_RC_FILE}] file in ${PWD}"
    . "${TF_RC_FILE}"
  fi
  if ! tf_plan $@ || ! tf_apply $@; then
    log error "Failed to plan and apply $(tf_bin) in ${PWD}"
  fi
  if [ -n "${target_dir}" ]; then
    if ! popd >/dev/null 2>&1; then
      log error "Failed to return to the previous directory, current [${PWD}]"
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
  if [ -f "${TF_RC_FILE}" ]; then
    log notice "found a [${TF_RC_FILE}] file in ${PWD}"
    . "${TF_RC_FILE}"
  fi
  if ! tf_plan $@ || ! tf_destroy $@; then
    log error "Failed to plan and destroy $(tf_bin) in ${PWD}"
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
  find . \( -name '*.md' -or -name '*.markdown' \) -type f | xargs -I{} sed -n '/^```$(tf_bin)$/,/^```$/p' {} | grep -v '^```' | sed '/^$/d'
}

function tf_replace() {
  local resource_id="${1}"
  if [ -z "${resource_id}" ]; then
    log error "Usage: terraform_replace <resource_id>"
    return ${RETURN_FAILURE:-1}
  else
    shift
  fi
  $(tf_bin) apply -replace="${resource_id}" $@
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
  find . -name ${TF_PLAN_ANSI} | xargs grep 'Error:' | awk -F: '{print $1}' | sort | uniq
}

function tf_failed_apply() {
  find . -name ${TF_APPLY_ANSI} | xargs grep 'Error:' | awk -F: '{print $1}' | sort | uniq
}

function tf_failed_destroy() {
  find . -name ${TF_DESTROY_ANSI} | xargs grep 'Error:' | awk -F: '{print $1}' | sort | uniq
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
