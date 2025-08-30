function java_flags() {
  java -XX:+PrintFlagsFinal -version
}

function java_dump() {
  local pid=$1
  local output=$2
  jmap -dump:format=b,file=${output} ${pid}
}

function jar_extract() {
  local jar_file=${1}
  local target_dir=${2:-$(pwd)}
  
  # Parameter validation
  if [ -z "${jar_file}" ]; then
    log error "Usage: jar_extract <jar_file> [target_dir]"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if jar file exists
  if [ ! -f "${jar_file}" ]; then
    log error "JAR file not found: ${jar_file}"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Check if jar command is available
  if ! have jar; then
    log error "jar command not found. Please install Java Development Kit (JDK)"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Create target directory if it doesn't exist
  if [ ! -d "${target_dir}" ]; then
    log info "Creating target directory: ${target_dir}"
    mkdir -p "${target_dir}" || {
      log error "Failed to create target directory: ${target_dir}"
      return ${RETURN_FAILURE:-1}
    }
  fi
  
  # Extract jar file to target directory
  log info "Extracting ${jar_file} to ${target_dir}"
  cd "${target_dir}" && jar xf "${jar_file}" || {
    log error "Failed to extract ${jar_file}"
    return ${RETURN_FAILURE:-1}
  }
  
  log info "Successfully extracted ${jar_file} to ${target_dir}"
  return ${RETURN_SUCCESS:-0}
}