function shfmt_file() {
  local file_path=${1}
  local indent=${2:-2}        # Default to 2 spaces, 0 for tabs
  local write_mode=${3:-true} # Default to write back to file
  local extra_opts=${4:-""}   # Additional options
  
  # Check if file exists
  if [ ! -f "${file_path}" ]; then
    log error "File not found: ${file_path}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if shfmt is available
  if ! have shfmt; then
    log error "shfmt command not found. Please install shfmt first."
    return ${RETURN_FAILURE:-1}
  fi
  
  # Build shfmt command options
  local shfmt_opts=""
  
  # Set indentation
  if [ "${indent}" -eq 0 ]; then
    shfmt_opts="${shfmt_opts} -i 0"  # Use tabs
  else
    shfmt_opts="${shfmt_opts} -i ${indent}"  # Use spaces
  fi
  
  # Add commonly used options
  shfmt_opts="${shfmt_opts} -ci"  # Case indent
  shfmt_opts="${shfmt_opts} -s"   # Simplify code
  
  # Add extra options if provided
  if [ -n "${extra_opts}" ]; then
    shfmt_opts="${shfmt_opts} ${extra_opts}"
  fi
  
  # Format the file
  if [ "${write_mode}" = "true" ]; then
    # Write back to file (like your example)
    local temp_file="${file_path}.shfmt_temp"
    
    if shfmt ${shfmt_opts} "${file_path}" > "${temp_file}"; then
      mv -f "${temp_file}" "${file_path}"
      log info "Successfully formatted: ${file_path}"
      return ${RETURN_SUCCESS:-0}
    else
      log error "Failed to format file: ${file_path}"
      [ -f "${temp_file}" ] && rm -f "${temp_file}"
      return ${RETURN_FAILURE:-1}
    fi
  else
    # Just output to stdout
    shfmt ${shfmt_opts} "${file_path}"
    return $?
  fi
}

function shfmt_check_file() {
  local file_path=${1}
  local indent=${2:-2}
  local extra_opts=${3:-""}
  
  # Check if file exists
  if [ ! -f "${file_path}" ]; then
    log error "File not found: ${file_path}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if shfmt is available
  if ! have shfmt; then
    log error "shfmt command not found. Please install shfmt first."
    return ${RETURN_FAILURE:-1}
  fi
  
  # Build shfmt command options
  local shfmt_opts=""
  
  # Set indentation
  if [ "${indent}" -eq 0 ]; then
    shfmt_opts="${shfmt_opts} -i 0"
  else
    shfmt_opts="${shfmt_opts} -i ${indent}"
  fi
  
  # Add commonly used options
  shfmt_opts="${shfmt_opts} -ci -s"
  
  # Add extra options if provided
  if [ -n "${extra_opts}" ]; then
    shfmt_opts="${shfmt_opts} ${extra_opts}"
  fi
  
  # Check if file needs formatting (using -l flag)
  if shfmt -l ${shfmt_opts} "${file_path}" | grep -q "${file_path}"; then
    log warn "File needs formatting: ${file_path}"
    return ${RETURN_FAILURE:-1}
  else
    log info "File is properly formatted: ${file_path}"
    return ${RETURN_SUCCESS:-0}
  fi
}

function shfmt_diff_file() {
  local file_path=${1}
  local indent=${2:-2}
  local extra_opts=${3:-""}
  
  # Check if file exists
  if [ ! -f "${file_path}" ]; then
    log error "File not found: ${file_path}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if shfmt is available
  if ! have shfmt; then
    log error "shfmt command not found. Please install shfmt first."
    return ${RETURN_FAILURE:-1}
  fi
  
  # Build shfmt command options
  local shfmt_opts=""
  
  # Set indentation
  if [ "${indent}" -eq 0 ]; then
    shfmt_opts="${shfmt_opts} -i 0"
  else
    shfmt_opts="${shfmt_opts} -i ${indent}"
  fi
  
  # Add commonly used options
  shfmt_opts="${shfmt_opts} -ci -s"
  
  # Add extra options if provided
  if [ -n "${extra_opts}" ]; then
    shfmt_opts="${shfmt_opts} ${extra_opts}"
  fi
  
  # Show diff (using -d flag)
  shfmt -d ${shfmt_opts} "${file_path}"
  return $?
}

function shfmt_directory() {
  local dir_path=${1}
  local indent=${2:-2}
  local write_mode=${3:-true}
  local extra_opts=${4:-""}
  
  # Check if directory exists
  if [ ! -d "${dir_path}" ]; then
    log error "Directory not found: ${dir_path}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if shfmt is available
  if ! have shfmt; then
    log error "shfmt command not found. Please install shfmt first."
    return ${RETURN_FAILURE:-1}
  fi
  
  log info "Finding shell files in: ${dir_path}"
  
  # Find all shell files
  local shell_files
  shell_files=$(shfmt -f "${dir_path}")
  
  if [ -z "${shell_files}" ]; then
    log info "No shell files found in: ${dir_path}"
    return ${RETURN_SUCCESS:-0}
  fi
  
  local success_count=0
  local error_count=0
  
  # Process each file
  while IFS= read -r file; do
    if [ -n "${file}" ]; then
      if shfmt_file "${file}" "${indent}" "${write_mode}" "${extra_opts}"; then
        ((success_count++))
      else
        ((error_count++))
      fi
    fi
  done <<< "${shell_files}"
  
  log info "Formatted ${success_count} files successfully, ${error_count} errors"
  
  if [ "${error_count}" -eq 0 ]; then
    return ${RETURN_SUCCESS:-0}
  else
    return ${RETURN_FAILURE:-1}
  fi
}