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

# Recursively splits large JSON files into smaller ones based on size threshold
function jq_smash_file() {
  local json_file=${1}
  local max_size=${2:-16384}  # Default 1MB in bytes
  local keep_source=${3:-true}  # Default to keep source file
  
  if [ -z "${json_file}" ]; then
    log error "Usage: jq_smash_file <json_file> [max_size_bytes] [keep_source]"
    log info "  json_file: Path to the JSON file to split"
    log info "  max_size_bytes: Maximum file size in bytes (default: 1048576 = 1MB)"
    log info "  keep_source: Whether to keep source file after splitting (default: true)"
    return ${RETURN_FAILURE:-1}
  fi
  
  if [ ! -f "${json_file}" ]; then
    log error "JSON file not found: ${json_file}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if jq command is available
  if ! have jq; then
    log error "jq command not found. Please install jq to use this function."
    return ${RETURN_FAILURE:-1}
  fi
  
  # Get file size in bytes
  local file_size=$(stat -c%s "${json_file}" 2>/dev/null || stat -f%z "${json_file}" 2>/dev/null)
  if [ -z "${file_size}" ]; then
    log error "Failed to get file size for: ${json_file}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # If file size is within limit, no need to split
  if [ "${file_size}" -le "${max_size}" ]; then
    log info "File ${json_file} (${file_size} bytes) is within size limit (${max_size} bytes), skipping"
    return ${RETURN_SUCCESS:-0}
  fi
  
  log info "Splitting ${json_file} (${file_size} bytes) - exceeds limit (${max_size} bytes)"
  
  # Get the directory and base filename
  local dir=$(dirname "${json_file}")
  local filename=$(basename "${json_file}")
  local basename="${filename%.*}"
  local extension="${filename##*.}"
  
  # Change to the file's directory
  local original_dir=$(pwd)
  cd "${dir}" || {
    log error "Failed to change to directory: ${dir}"
    return ${RETURN_FAILURE:-1}
  }
  
  # Determine JSON structure type
  local json_type=$(jq -r 'type' "${filename}" 2>/dev/null)
  if [ -z "${json_type}" ]; then
    log error "Failed to determine JSON type for: ${filename}"
    cd "${original_dir}"
    return ${RETURN_FAILURE:-1}
  fi
  
  local split_count=0
  local split_files=()
  
  case "${json_type}" in
    "object")
      log info "Processing JSON object: ${filename}"
      # Get all keys from the object
      local keys=$(jq -r 'keys[]' "${filename}" 2>/dev/null)
      if [ -z "${keys}" ]; then
        log warn "No keys found in JSON object: ${filename}"
        cd "${original_dir}"
        return ${RETURN_SUCCESS:-0}
      fi
      
      # Create subdirectory for split files
      local output_dir="${basename}"
      if ! mkdir -p "${output_dir}"; then
        log error "Failed to create output directory: ${output_dir}"
        cd "${original_dir}"
        return ${RETURN_FAILURE:-1}
      fi
      
      # Split each key-value pair into separate files
      for key in ${keys}; do
        local output_file="${output_dir}/${key}.${extension}"
        if jq ".\"${key}\"" "${filename}" > "${output_file}" 2>/dev/null; then
          log info "Created: ${output_file}"
          split_files+=("${output_file}")
          split_count=$((split_count + 1))
        else
          log warn "Failed to extract key '${key}' from ${filename}"
        fi
      done
      ;;
      
    "array")
      log info "Processing JSON array: ${filename}"
      # Get array length
      local array_length=$(jq 'length' "${filename}" 2>/dev/null)
      if [ -z "${array_length}" ] || [ "${array_length}" -eq 0 ]; then
        log warn "Empty or invalid JSON array: ${filename}"
        cd "${original_dir}"
        return ${RETURN_SUCCESS:-0}
      fi
      
      # Create subdirectory for split files
      local output_dir="${basename}"
      if ! mkdir -p "${output_dir}"; then
        log error "Failed to create output directory: ${output_dir}"
        cd "${original_dir}"
        return ${RETURN_FAILURE:-1}
      fi
      
      # Split each array element into separate files
      for ((i=0; i<array_length; i++)); do
        local output_file="${output_dir}/${i}.${extension}"
        if jq ".[$i]" "${filename}" > "${output_file}" 2>/dev/null; then
          log info "Created: ${output_file}"
          split_files+=("${output_file}")
          split_count=$((split_count + 1))
        else
          log warn "Failed to extract index ${i} from ${filename}"
        fi
      done
      ;;
      
    *)
      # Skip files that are not objects or arrays (strings, numbers, booleans, null)
      cd "${original_dir}"
      return ${RETURN_SUCCESS:-0}
      ;;
  esac
  
  # Return to original directory
  cd "${original_dir}"
  
  if [ ${split_count} -eq 0 ]; then
    log warn "No files were created from: ${json_file}"
    return ${RETURN_SUCCESS:-0}
  fi
  
  log info "Successfully split ${json_file} into ${split_count} files"
  
  # Delete source file if keep_source is false
  if [ "${keep_source}" = "false" ] || [ "${keep_source}" = "0" ]; then
    if rm -f "${json_file}"; then
      log info "Deleted source file: ${json_file}"
    else
      log warn "Failed to delete source file: ${json_file}"
    fi
  fi
  
  # Recursively process the split files
  local recursive_count=0
  for split_file in "${split_files[@]}"; do
    local full_split_path="${dir}/${split_file}"
    if [ -f "${full_split_path}" ]; then
      # Recursively call jq_smash_file on each split file
      if jq_smash_file "${full_split_path}" "${max_size}" "${keep_source}"; then
        recursive_count=$((recursive_count + 1))
      fi
    fi
  done
  
  log info "Recursively processed ${recursive_count} split files from: ${json_file}"
  return ${RETURN_SUCCESS:-0}
}
