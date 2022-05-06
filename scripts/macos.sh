function add_vault_pass() {
    local name="$1"
    read -s VAULT_PASSWORD
    echo
    security add-generic-password -U -a $USER -s ${name} -w "$VAULT_PASSWORD"
    unset VAULT_PASSWORD
}

function print_vault_pass() {
    local name="$1"
    security find-generic-password -a $USER -s ${name} -w
}