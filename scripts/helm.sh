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
      log error "${values_file} exists, skipping"
    fi
  fi
}
