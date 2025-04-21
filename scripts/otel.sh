function otelcol_generate_config() {
  local config_file=${1:-/etc/otel/otelcol-contrib/dynamic.yaml}
  local log_dir=${2:-${OUTPUT_DIR}}

  if ! have yq; then
    log error "yq is not installed. Please install yq to use this function." >&2
    return ${RETURN_FAILURE}
  fi

  [[ -d "${log_dir}" ]] || {
    log error "Output directory does not exist: ${log_dir}" >&2
    return ${RETURN_FAILURE}
  }

  cd "${log_dir}" || exit 1

  if [ ! -f "${config_file}" ]; then
    mkdir -p "$(dirname ${config_file})"
    yq eval -n '
    .receivers = {}
    | .processors = {}
    | .exporters = {}
    | .extensions = {}
    | .connectors = {}
    | .service.pipelines = {}
  ' >"${config_file}"
  fi

  log info "Adding stdout/stderr log receivers"
  for file in *.stdout *.stderr; do
    [[ -e "${file}" ]] || continue
    local type="filelog"
    [[ -p "${file}" ]] && type="namedpipe"

    local config_value
    if [[ "${type}" == "namedpipe" ]]; then
      config_value="{\"path\": \"${log_dir}/${file}\"}"
    else
      config_value="{\"include\": [\"${log_dir}/${file}\"]}"
    fi
    log notice "Adding [${type}] receiver for ${file}"
    yq eval -i ".receivers.\"${type}/${file}\" = ${config_value}" "${config_file}"
  done

  log info "Adding processors"
  for file in *.stdout *.stderr; do
    [[ -e "${file}" ]] || continue
    log notice "Adding attributes processor for ${file}"
    yq eval -i ".processors.\"attributes/${file}\".actions = [{\"action\": \"insert\", \"key\": \"from\", \"value\": \"${file}\"}]" "${config_file}"
  done

  for stream in stdout stderr; do
    [[ -e "/dev/${stream}" ]] || continue
    yq eval -i ".exporters.\"file/${stream}\" = {\"path\": \"/dev/${stream}\"}" "${config_file}"
  done

  log info "Adding file exporters for stdout and stderr"
  for file in *.stdout *.stderr; do
    [[ -e "${file}" ]] || continue
    local receiver_type="filelog"
    [[ -p "${file}" ]] && receiver_type="namedpipe"
    log notice "Adding [${receiver_type}] exporter for ${file}"
    local exporter="file/${file##*.}"
    yq eval -i ".service.pipelines.\"logs/${file}\" = {
      \"receivers\": [\"${receiver_type}/${file}\"],
      \"processors\": [\"attributes/${file}\", \"transform\"],
      \"exporters\": [\"${exporter}\"]
    }" "${config_file}"
  done
}
