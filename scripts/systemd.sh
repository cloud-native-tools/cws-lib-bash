# Checks if the current environment is running under systemd
function systemd_available() {
  # Check if systemctl command exists
  if ! command -v systemctl >/dev/null 2>&1; then
    return ${RETURN_FAILURE:-1}
  fi

  # Check if we're in a systemd environment by looking for systemd PID 1
  if [[ "$(ps -o comm= 1)" != "systemd" ]]; then
    return ${RETURN_FAILURE:-1}
  fi

  # Check if we can communicate with systemd
  if systemctl is-system-running --quiet 2>/dev/null; then
    return ${RETURN_SUCCESS:-0}
  else
    # Even if systemd is not fully running, we're still in a systemd environment
    # Check if systemd boot environment variables are set
    if [[ -n "$XDG_RUNTIME_DIR" ]] && [[ -d "$XDG_RUNTIME_DIR" ]]; then
      return ${RETURN_SUCCESS:-0}
    fi
    
    # Fallback: check if systemd process exists
    if pgrep -f "/lib/systemd/systemd" >/dev/null 2>&1; then
      return ${RETURN_SUCCESS:-0}
    fi
  fi

  return ${RETURN_FAILURE:-1}
}

function systemd_list_unit_file() {
  find ${@} -regex '.*\.service\|.*\.socket|.*\.device|.*\.mount|.*\.automount|.*\.swap|.*\.target|.*\.path|.*\.timer' 2>/dev/null
}

# Lists system unit files across specified paths
function systemd_list_system_unit_file() {
  systemd_list_unit_file \
    /etc/systemd/system.control/ \
    /run/systemd/system.control/ \
    /run/systemd/transient/ \
    /run/systemd/generator.early/ \
    /etc/systemd/system/ \
    /etc/systemd/system.attached/ \
    /run/systemd/system/ \
    /run/systemd/system.attached/ \
    /run/systemd/generator/ \
    /usr/lib/systemd/system/ \
    /run/systemd/generator.late/
}

# Lists user unit files across specified paths
function systemd_list_user_unit_file() {
  systemd_list_unit_file \
    ~/.config/systemd/user.control/ \
    ~/.config/systemd/user/ \
    /etc/systemd/user/ \
    /run/systemd/user/ \
    /usr/lib/systemd/user/ \
    $XDG_RUNTIME_DIR/systemd/user.control/ \
    $XDG_RUNTIME_DIR/systemd/transient/ \
    $XDG_RUNTIME_DIR/systemd/generator.early/ \
    $XDG_RUNTIME_DIR/systemd/generator.late/ \
    $XDG_RUNTIME_DIR/systemd/user/ \
    $XDG_RUNTIME_DIR/systemd/generator/ \
    $XDG_DATA_HOME/systemd/user/ \
    $XDG_DATA_DIRS/systemd/user/ \
    $XDG_CONFIG_DIRS/systemd/user/
}

# Lists all unit files (both system and user)
function systemd_list_all_unit_file() {
  systemd_list_system_unit_file
  systemd_list_user_unit_file
}
