function jq_array_add() {
  local field=${1}
  local new_array=${2}
  local json_file=${3:--}
  cat ${json_file} | jq ".${field} = . + ${new_array}"
}

function jq_dict_add() {
  local new_dict=${1}
  local json_file=${2:--}
  cat ${json_file} | jq ". = . + ${new_dict}"
}

function jq_format() {
  local json_file=${1:--}
  cat ${json_file} | jq .
}

function jq_sort_file() {
  local json_file=${1}

  if [ ! -f "${json_file}" ]; then
    log error "Usage: jq_sort_file <json_file>"
    return ${RETURN_FAILURE}
  fi
  local tmp_dir=$(mktemp -d)
  trap 'rm -rf "${tmp_dir}"' EXIT

  if jq -S --indent 2 '
    def sort_keys:
      if type == "object" then
        to_entries | sort_by(.key) | map( .value |= sort_keys ) | from_entries
      else
        .
      end;
    sort_keys
  ' "${json_file}" >"${tmp_dir}/sorted.json"; then
    mv "${tmp_dir}/sorted.json" "${json_file}"
  fi
}

function jq_otel_logs() {
  local logs_file=${1:--}
  cat ${logs_file} | jq -r '.resourceLogs[] | .scopeLogs[] | .logRecords[] |  "\(.attributes[].value.stringValue) \(.body.stringValue)"'
}
