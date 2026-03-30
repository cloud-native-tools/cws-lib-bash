function rust_install() {
    local rust_version=${1:-stable}

    if ! command -v rustup >/dev/null 2>&1; then
        log info "Installing rustup..."
        if ! curl \
            --proto '=https' \
            --tlsv1.2 \
            -sSf https://sh.rustup.rs \
            | sh -s -- -y \
                 --profile minimal \
                 --default-toolchain "${rust_version}"; then
            log error "Failed to install rustup"
            return "${RETURN_FAILURE:-1}"
        fi
    fi

    if [ -f "${HOME}/.cargo/env" ]; then
        # shellcheck source=/dev/null
        source "${HOME}/.cargo/env"
    fi

    rustup self update || true
    rustup toolchain install "${rust_version}" --profile minimal || return "${RETURN_FAILURE:-1}"
    rustup default "${rust_version}" || return "${RETURN_FAILURE:-1}"

    log notice "Rust toolchain installed successfully"
    log plain "rustup version: $(rustup --version)"
    log plain "rustc version: $(rustc --version)"
    log plain "cargo version: $(cargo --version)"

    return "${RETURN_SUCCESS:-0}"
}

function rust_mirror() {
    local repo_root="/oss_code/repo"
    local download_dir=${1:-"${repo_root}/rust"}
    local channels="stable"
    local targets="aarch64-unknown-linux-gnu,aarch64-unknown-linux-musl,x86_64-unknown-linux-gnu,x86_64-unknown-linux-musl"
    local upstream_url="https://static.rust-lang.org/"
    local orig_dir=""
    local cleanup_orig_dir=0
    local rustup_mirror_cmd

    have rustup-mirror || {
        log error "rustup-mirror is required but was not found in PATH"
        return "${RETURN_FAILURE:-1}"
    }

    mkdir -p "${repo_root}" || {
        log error "Failed to create repo root directory: ${repo_root}"
        return "${RETURN_FAILURE:-1}"
    }
    repo_root=$(readlink -f "${repo_root}") || {
        log error "Failed to resolve repo root directory: ${repo_root}"
        return "${RETURN_FAILURE:-1}"
    }

    mkdir -p "${download_dir}" || {
        log error "Failed to create download directory: ${download_dir}"
        return "${RETURN_FAILURE:-1}"
    }
    download_dir=$(readlink -f "${download_dir}") || {
        log error "Failed to resolve download directory: ${download_dir}"
        return "${RETURN_FAILURE:-1}"
    }

    if [ -n "${orig_dir}" ]; then
        mkdir -p "${orig_dir}" || {
            log error "Failed to create orig directory: ${orig_dir}"
            return "${RETURN_FAILURE:-1}"
        }
        orig_dir=$(readlink -f "${orig_dir}") || {
            log error "Failed to resolve orig directory: ${orig_dir}"
            return "${RETURN_FAILURE:-1}"
        }
    else
        orig_dir=$(mktemp -d "${TMPDIR:-/tmp}/rustup-mirror-orig.XXXXXX") || {
            log error "Failed to create temporary orig directory"
            return "${RETURN_FAILURE:-1}"
        }
        cleanup_orig_dir=1
    fi

    log info "Syncing Rust mirror to ${download_dir}"
    log info "Repo root: ${repo_root}"
    log info "Rust channel(s): ${channels}"
    log info "Target(s): ${targets}"
    log info "Upstream url: ${upstream_url}"
    log info "Orig directory: ${orig_dir}"

    rustup_mirror_cmd=(
        rustup-mirror
        --orig "${orig_dir}"
        --mirror "${download_dir}"
        --upstream-url "${upstream_url}"
        --channels "${channels}"
        --targets "${targets}"
    )

    "${rustup_mirror_cmd[@]}" || {
        if [ "${cleanup_orig_dir}" -eq 1 ]; then
            rm -rf "${orig_dir}"
        fi
        return "${RETURN_FAILURE:-1}"
    }

    if [ "${cleanup_orig_dir}" -eq 1 ]; then
        rm -rf "${orig_dir}"
    fi

    log notice "Rust mirror is ready: ${download_dir}"
    log plain "Local mirror path: ${download_dir}"

    return "${RETURN_SUCCESS:-0}"
}