function ansible_ping_hosts() {
  # Check dependencies first
  ansible_check || return ${RETURN_FAILURE}

  # Validate required environment variables
  if [ -z "${ANSIBLE_USER_INVENTORY}" ]; then
    log error "ANSIBLE_USER_INVENTORY environment variable is not set"
    return ${RETURN_FAILURE}
  fi

  if [ ! -f "${ANSIBLE_USER_INVENTORY}" ]; then
    log error "Ansible inventory file not found: ${ANSIBLE_USER_INVENTORY}"
    return ${RETURN_FAILURE}
  fi
  
  log info "Pinging hosts from inventory: ${ANSIBLE_USER_INVENTORY}"
  printf "%-120s %-16s %s\n" "HOST" "STATE" "MESSAGE"
  ansible all -i ${ANSIBLE_USER_INVENTORY} -m ping |
    sed 's/^\}/@/g' |
    tr -d '\n' |
    tr '@' '\n' |
    awk \
      -v green="${GREEN}" \
      -v red="${RED}" \
      -v yellow="${YELLOW}" \
      -v clear="${CLEAR}" '\
      $3=="SUCCESS"{
        printf "%-120s %s%-16s%s\n", $1, green, $3, clear
      } 
      /FAILED!/{
        # Extract error message from the output
        match($0, /"msg": *"([^"]+)"/, err_msg)
        msg = err_msg[1]
        if (msg == "") {
          match($0, /"module_stderr": *"([^"]+)"/, err_details)
          msg = err_details[1]
        }
        if (msg == "") {
          msg = "Unknown error"
        }
        printf "%-120s %s%-16s%s %s\n", $1, red, "FAILED!", clear, msg
      } 
      $3=="UNREACHABLE!"{
        # Extract msg field using regex
        match($0, /"msg": *"([^"]+)"/, arr)
        msg = arr[1]
        printf "%-120s %s%-16s%s %s\n", $1, yellow, $3, clear, msg
      }'
      
  return ${RETURN_SUCCESS}
}

function ansible_run_playbook() {
  local playbook=${1}
  local hosts=${2:-""}
  local inventory=${3:-""}
  local variables=${4:-""}

  # Check dependencies first
  ansible_check || return ${RETURN_FAILURE}

  # Parameter validation
  if [ -z "${playbook}" ]; then
    log error "Usage: ansible_run_playbook <playbook> [hosts] [inventory] [variables]"
    log error "Example: ansible_run_playbook playbook.yaml host1,host2 inventory.yaml \"var1=value1 var2=value2\""
    return ${RETURN_FAILURE}
  fi
  
  if [ ! -f "${playbook}" ]; then
    log error "Playbook file not found: ${playbook}"
    return ${RETURN_FAILURE}
  fi
  
  # If inventory is not provided as parameter, use the environment variable
  if [ -z "${inventory}" ]; then
    if [ -z "${ANSIBLE_USER_INVENTORY}" ]; then
      log error "No inventory specified and ANSIBLE_USER_INVENTORY environment variable is not set"
      return ${RETURN_FAILURE}
    fi
    inventory="${ANSIBLE_USER_INVENTORY}"
  fi
  
  if [ ! -f "${inventory}" ]; then
    log error "Inventory file not found: ${inventory}"
    return ${RETURN_FAILURE}
  fi

  # Determine if debug mode is enabled
  local debug_options=""
  if [ "${ANSIBLE_DEBUG}" == "true" ]; then
    debug_options="-vv"
    log info "Debug mode enabled"
  fi

  # Process host limit option
  local limit_option=""
  if [ -n "${hosts}" ]; then
    limit_option="--limit ${hosts}"
    log notice "Running playbook on specific hosts: ${hosts}"
  fi

  # Process extra variables
  local var_option=""
  if [ -n "${variables}" ]; then
    var_option="--extra-vars \"${variables}\""
    log notice "Running playbook with variables: ${variables}"
  fi

  # Process vault password option
  local vault_option=""
  if [ -n "${ANSIBLE_USER_VAULT_PASS}" ] && [ -f "${ANSIBLE_USER_VAULT_PASS}" ]; then
    log notice "Using vault password file: ${ANSIBLE_USER_VAULT_PASS}"
    vault_option="--vault-password-file=${ANSIBLE_USER_VAULT_PASS}"
  fi

  log notice "Running Ansible playbook: ${playbook}"
  # shellcheck disable=SC2086
  ansible-playbook \
    -i ${inventory} \
    ${limit_option} \
    ${var_option} \
    ${debug_options} \
    ${vault_option} \
    ${playbook}
    
  local exit_code=$?
  if [ ${exit_code} -eq 0 ]; then
    log info "Playbook execution completed successfully"
  else
    log error "Playbook execution failed with exit code ${exit_code}"
  fi
  
  return ${exit_code}
}

function ansible_check_vault() {
  local vault_file=${1}
  
  # Check dependencies first
  ansible_check || return ${RETURN_FAILURE}
  
  # Parameter validation
  if [ -z "${vault_file}" ]; then
    log error "Usage: ansible_check_vault <vault_file>"
    log error "Example: ansible_check_vault /path/to/roles/docker/vars/vault.yml"
    return ${RETURN_FAILURE}
  fi

  if [ ! -f "${vault_file}" ]; then
    log error "Vault file not found: ${vault_file}"
    return ${RETURN_FAILURE}
  fi
  
  # Check if ANSIBLE_USER_VAULT_PASS is set
  if [ -z "${ANSIBLE_USER_VAULT_PASS}" ]; then
    log error "ANSIBLE_USER_VAULT_PASS environment variable is not set"
    return ${RETURN_FAILURE}
  fi

  log notice "Checking vault file: ${vault_file}"
  
  # Check if vault is encrypted properly
  if grep -q "^\$ANSIBLE_VAULT;" "${vault_file}"; then
    log info "Vault file is encrypted: ${vault_file}"
  else
    log warn "Vault file is NOT encrypted: ${vault_file}"
  fi

  # Check if vault password file exists and is readable
  if [ -f "${ANSIBLE_USER_VAULT_PASS}" ]; then
    log info "Vault password file exists: ${ANSIBLE_USER_VAULT_PASS}"
    if [ -r "${ANSIBLE_USER_VAULT_PASS}" ]; then
      log info "Vault password file is readable"
    else
      log error "Vault password file is not readable: ${ANSIBLE_USER_VAULT_PASS}"
      return ${RETURN_FAILURE}
    fi
  else
    log error "Vault password file not found: ${ANSIBLE_USER_VAULT_PASS}"
    log error "Create the vault password file with: echo 'your-vault-password' > ${ANSIBLE_USER_VAULT_PASS}"
    log error "And secure it with: chmod 600 ${ANSIBLE_USER_VAULT_PASS}"
    return ${RETURN_FAILURE}
  fi

  # Try to view the vault contents to verify if password works
  local temp_output
  temp_output=$(ANSIBLE_VAULT_PASSWORD_FILE=${ANSIBLE_USER_VAULT_PASS} ansible-vault view "${vault_file}" 2>&1)
  local exit_code=$?
  
  if [ ${exit_code} -eq 0 ]; then
    log info "Vault password is correct. Vault can be decrypted successfully."
    log info "Variables defined in vault file:"
    echo "${temp_output}" | grep -E "^[a-zA-Z0-9_]+:" | awk '{print "  - " $1}'
    
    # Check specifically for docker_registry_password
    if echo "${temp_output}" | grep -q "docker_registry_password:"; then
      log info "docker_registry_password is defined in the vault file"
    else
      log warn "docker_registry_password is NOT defined in the vault file"
    fi
  else
    log error "Failed to decrypt vault file with the provided password file"
    log error "${temp_output}"
    return ${RETURN_FAILURE}
  fi

  return ${RETURN_SUCCESS}
}

function ansible_run_task() {
  local role_name=${1}
  local task_file=${2}
  local hosts=${3}
  local inventory=${4:-""}
  local variables=${5:-""}

  # Check dependencies first
  ansible_check || return ${RETURN_FAILURE}

  # Parameter validation
  if [ -z "${role_name}" ] || [ -z "${task_file}" ] || [ -z "${hosts}" ]; then
    log error "Usage: ansible_run_task <role_name> <task_file> <hosts> [inventory] [variables]"
    log error "Example: ansible_run_task docker setup.yml web_servers inventory.yaml \"var1=value1 var2=value2\""
    return ${RETURN_FAILURE}
  fi
  
  # If inventory is not provided as parameter, use the environment variable
  if [ -z "${inventory}" ]; then
    if [ -z "${ANSIBLE_USER_INVENTORY}" ]; then
      log error "No inventory specified and ANSIBLE_USER_INVENTORY environment variable is not set"
      return ${RETURN_FAILURE}
    fi
    inventory="${ANSIBLE_USER_INVENTORY}"
  fi
  
  if [ ! -f "${inventory}" ]; then
    log error "Inventory file not found: ${inventory}"
    return ${RETURN_FAILURE}
  fi

  # Determine if debug mode is enabled
  local debug_options=""
  if [ "${ANSIBLE_DEBUG}" == "true" ]; then
    debug_options="-vv"
    log info "Debug mode enabled"
  fi

  # Process extra variables
  local var_option=""
  if [ -n "${variables}" ]; then
    var_option="--extra-vars \"${variables}\""
    log notice "Running task with variables: ${variables}"
  fi

  # Process vault password option
  local vault_option=""
  if [ -n "${ANSIBLE_USER_VAULT_PASS}" ] && [ -f "${ANSIBLE_USER_VAULT_PASS}" ]; then
    log notice "Using vault password file: ${ANSIBLE_USER_VAULT_PASS}"
    vault_option="--vault-password-file=${ANSIBLE_USER_VAULT_PASS}"
  fi

  log notice "Running task '${task_file}' from role '${role_name}' on hosts: ${hosts}"
  
  # shellcheck disable=SC2086
  ansible ${hosts} \
    -i ${inventory} \
    -m include_role \
    -a "name=${role_name} tasks_from=${task_file}" \
    ${debug_options} \
    ${var_option} \
    ${vault_option}
    
  local exit_code=$?
  if [ ${exit_code} -eq 0 ]; then
    log info "Task execution completed successfully"
  else
    log error "Task execution failed with exit code ${exit_code}"
  fi
  
  return ${exit_code}
}

function ansible_dump_config() {
  # Check dependencies first
  ansible_check || return ${RETURN_FAILURE}

  log notice "Dumping Official Ansible Environment Variables"
  
  # Print ansible version
  log info "Ansible version information:"
  ansible --version | sed 's/^/  /'
  
  # List of official Ansible environment variables
  # These are the standard variables that Ansible recognizes
  local official_vars=(
    "ANSIBLE_ACTION_PLUGINS"
    "ANSIBLE_CACHE_PLUGIN"
    "ANSIBLE_CACHE_PLUGIN_CONNECTION"
    "ANSIBLE_CACHE_PLUGIN_TIMEOUT"
    "ANSIBLE_COLLECTIONS_PATHS"
    "ANSIBLE_CONFIG"
    "ANSIBLE_FILTER_PLUGINS"
    "ANSIBLE_USER_INVENTORY"
    "ANSIBLE_LIBRARY"
    "ANSIBLE_RETRY_FILES_ENABLED"
    "ANSIBLE_RETRY_FILES_SAVE_PATH"
    "ANSIBLE_ROLES_PATH"
    "ANSIBLE_SSH_CONTROL_PATH_DIR"
    "ANSIBLE_USER_VAULT_PASS"
  )
  
  # Show official Ansible environment variables that are set
  log info "Official Ansible Environment Variables currently set:"
  
  local found_vars=false
  for var in "${official_vars[@]}"; do
    if [ -n "${!var}" ]; then
      found_vars=true
      printf "  %s=%s\n" "${var}" "${!var}"
    fi
  done
  
  if [ "${found_vars}" = false ]; then
    log warn "No official Ansible environment variables are currently set"
  fi
  
  # Show active config file
  log info "Active Ansible configuration file:"
  ansible --version | grep "config file" | sed 's/^.*config file = /  /'
  
  # Show any custom environment variables that might affect Ansible
  log info "Custom or non-standard Ansible environment variables:"
  env | grep -i "ANSIBLE" | grep -v -E "$(IFS="|"; echo "${official_vars[*]}")" | sort | sed 's/^/  /'
  
  log notice "Ansible environment variables dump completed"
  
  return ${RETURN_SUCCESS}
}

function ansible_check() {
  # Check if the 'log' function is available, which is required by all functions
  if ! type log >/dev/null 2>&1; then
    echo "ERROR: 'log' function is required but not available"
    echo "This script depends on the CWS-Lib-Bash logging utilities"
    echo "Make sure to source the core utilities before using ansible.sh"
    return ${RETURN_FAILURE:-1}
  fi

  # Check if ansible command is available
  if ! command -v ansible >/dev/null 2>&1; then
    log error "ansible command not found. Please install ansible first."
    return ${RETURN_FAILURE:-1}
  fi

  # Check if ansible-playbook command is available
  if ! command -v ansible-playbook >/dev/null 2>&1; then
    log error "ansible-playbook command not found. Please install ansible first."
    return ${RETURN_FAILURE:-1}
  fi

  # Check if ansible-vault command is available
  if ! command -v ansible-vault >/dev/null 2>&1; then
    log error "ansible-vault command not found. Please install ansible first."
    return ${RETURN_FAILURE:-1}
  fi
  
  return ${RETURN_SUCCESS:-0}
}
