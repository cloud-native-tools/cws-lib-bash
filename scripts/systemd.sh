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
