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
  for d in $(find . -name '*.tf' -type f | xargs dirname | sort | uniq); do
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
    fi
  done
}

function tf_plan() {
  terraform plan -out=plan.out
  terraform show plan.out >plan.ansi
}

function tf_extract_example() {
  find . \( -name '*.md' -or -name '*.markdown' \) -type f | xargs -I{} sed -n '/^```terraform$/,/^```$/p' {} | grep -v '^```' | sed '/^$/d'
}

function tf_replace() {
  local resource_id="${1}"
  if [ -z "${resource_id}" ]; then
    log error "Usage: terraform_replace <resource_id>"
    return ${RETURN_FAILURE:-1}
  fi
  terraform apply -replace="${resource_id}"
}
