function rpm_extract_file() {
  local rpm_file=${1}
  local target_dir=${2}

  # Parameter validation
  if [ -z "${rpm_file}" ] || [ -z "${target_dir}" ]; then
    log error "Usage: rpm_extract_file <rpm_file> <target_dir>"
    log error "  rpm_file   - Path to the RPM package file"
    log error "  target_dir - Directory to extract RPM contents to"
    return ${RETURN_FAILURE:-1}
  fi

  # Check if RPM file exists
  if [ ! -f "${rpm_file}" ]; then
    log error "RPM file not found: ${rpm_file}"
    return ${RETURN_FAILURE:-1}
  fi

  # Create target directory if it doesn't exist
  if [ ! -d "${target_dir}" ]; then
    if ! mkdir -p "${target_dir}"; then
      log error "Failed to create target directory: ${target_dir}"
      return ${RETURN_FAILURE:-1}
    fi
  fi

  # Check required tools availability
  if ! have rpm2cpio; then
    log error "rpm2cpio command not found"
    return ${RETURN_FAILURE:-1}
  fi

  if ! have cpio; then
    log error "cpio command not found"
    return ${RETURN_FAILURE:-1}
  fi

  log info "Extracting ${rpm_file} to ${target_dir}"

  # Extract RPM contents to target directory
  if (cd "${target_dir}" && rpm2cpio "${rpm_file}" | cpio -idmv); then
    log info "Successfully extracted RPM contents to ${target_dir}"
    return ${RETURN_SUCCESS:-0}
  else
    log error "Failed to extract ${rpm_file} to ${target_dir}"
    return ${RETURN_FAILURE:-1}
  fi
}

function rpm_get_source() {
  local spec_file=${1}

  # Parameter validation
  if [ -z "${spec_file}" ]; then
    log error "Usage: rpm_get_source <spec_file>"
    log error "  spec_file - Path to the RPM spec file"
    return ${RETURN_FAILURE:-1}
  fi

  # Check if spec file exists
  if [ ! -f "${spec_file}" ]; then
    log error "Spec file not found: ${spec_file}"
    return ${RETURN_FAILURE:-1}
  fi

  # Check required tools availability
  if ! have rpmbuild; then
    log error "rpmbuild command not found"
    log error "Please install rpm-build package"
    return ${RETURN_FAILURE:-1}
  fi

  log info "Getting source from spec file: ${spec_file}"

  # Extract source using rpmbuild
  if rpmbuild --nodeps -v -bp "${spec_file}"; then
    log info "Successfully extracted source from ${spec_file}"
    return ${RETURN_SUCCESS:-0}
  else
    log error "Failed to extract source from ${spec_file}"
    return ${RETURN_FAILURE:-1}
  fi
}
