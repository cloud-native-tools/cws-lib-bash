function cws_py_uninstall() {
  log info "Uninstalling cws-lib-python..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  if pip3 uninstall -y cws-lib-python; then
    log notice "cws-lib-python uninstalled successfully"
    return "${RETURN_SUCCESS:-0}"
  else
    log warn "Failed to uninstall cws-lib-python (it might not be installed)"
    return "${RETURN_SUCCESS:-0}"
  fi
}

function cws_py_is_installed() {
  # Check if python3 is available
  if ! have python3; then
    return "${RETURN_FAILURE:-1}"
  fi

  # Check via python import (most reliable method)
  if python3 -c "import cws_common" >/dev/null 2>&1; then
    return "${RETURN_SUCCESS:-0}"
  fi

  # Also check pip as requested (for logging/debugging purposes)
  if have pip3 && pip3 show cws-lib-python >/dev/null 2>&1; then
    log warn "cws-lib-python found in pip but import cws_common failed"
  fi

  return "${RETURN_FAILURE:-1}"
}

function cws_py_install() {
  log info "Installing cws-lib-python from multiple sources..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  log info "Uninstalling existing cws-lib-python (if any)..."
  cws_py_uninstall

  # Define installation sources in order of preference
  local sources=(
    "git+https://gitlab.alibaba-inc.com/cloud-native-tools/cws-lib-python.git@main"
    "git+https://gitee.com/cloud-native-tools/cws-lib-python.git@main"
    "git+https://github.com/cloud-native-tools/cws-lib-python.git@main"
  )

  # Test and try each source in order
  for source in "${sources[@]}"; do
    log info "Trying to install from: ${source}"

    # Extract hostname from the source URL for network testing
    local hostname=""
    if [[ ${source} == *"gitlab.alibaba-inc.com"* ]]; then
      hostname="gitlab.alibaba-inc.com"
    elif [[ ${source} == *"gitee.com"* ]]; then
      hostname="gitee.com"
    elif [[ ${source} == *"github.com"* ]]; then
      hostname="github.com"
    fi

    # Test network connectivity if we can extract a hostname
    if [ -n "${hostname}" ]; then
      log info "Testing network connectivity to ${hostname}..."
      if ! net_ping "${hostname}"; then
        log warn "Network connectivity to ${hostname} failed, skipping this source"
        continue
      fi
      log info "Network connectivity to ${hostname} successful"
    fi

    # Try to install from this source with timeout
    if pip3 install --timeout 20 "${source}"; then
      log notice "cws-lib-python installed successfully from ${source}"
      return "${RETURN_SUCCESS:-0}"
    else
      log warn "Failed to install from ${source}, trying next source..."
    fi
  done

  log error "Failed to install cws-lib-python from all available sources"
  return "${RETURN_FAILURE:-1}"
}
