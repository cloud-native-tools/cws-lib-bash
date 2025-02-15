TF_PLAN_OUT="plan.out"
TF_INIT_ANSI="init.ansi"
TF_PLAN_ANSI="plan.ansi"
TF_VALIDATE_ANSI="validate.ansi"
TF_APPLIED_ANSI="applied.ansi"
TF_FAILED_ANSI="failed.ansi"

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

function tf_plan() {
  terraform init -upgrade >${TF_INIT_ANSI} 2>&1
  terraform plan -out=${TF_PLAN_OUT} 2>${TF_VALIDATE_ANSI}
  terraform show ${TF_PLAN_OUT} >${TF_PLAN_ANSI}
}

function tf_apply() {
  local target_dir="${1}"
  if [ -n "${target_dir}" ]; then
    pushd ${target_dir} >/dev/null 2>&1
  fi

  log notice "terraform apply in $(pwd)"
  if [ ! -f "${TF_PLAN_OUT}" ]; then
    log warn "no ${TF_PLAN_OUT} found, run terraform plan first"
    tf_plan
  fi
  terraform apply -auto-approve ${TF_PLAN_OUT} >${TF_APPLIED_ANSI} 2>${TF_FAILED_ANSI}

  if [ -n "${target_dir}" ]; then
    popd >/dev/null 2>&1
  fi
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
  find . -name ${TF_VALIDATE_ANSI} | xargs ls -lh | awk '$5!=0{print}'
}

function tf_failed_apply() {
  find . -name ${TF_FAILED_ANSI} | xargs ls -lh | awk '$5!=0{print}'
}
