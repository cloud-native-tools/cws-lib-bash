function rust_install() {
  local rust_version=${1:-stable}

  if ! command -v rustup >/dev/null 2>&1; then
    log info "Installing rustup..."
    if ! curl \
      --proto '=https' \
      --tlsv1.2 \
      -sSf https://sh.rustup.rs |
      sh -s -- -y \
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

RUST_UPSTREAM="https://static.rust-lang.org/"
RUST_MIRROR_TARGETS=(
  aarch64-apple-darwin
  aarch64-unknown-linux-gnu
  aarch64-unknown-linux-musl
  wasm32-unknown-emscripten
  wasm32-unknown-unknown
  wasm32-wasip2
  wasm64-unknown-unknown
  x86_64-apple-darwin
  x86_64-unknown-linux-gnu
  x86_64-unknown-linux-musl
)

function rust_mirror() {
  local repo_root="${1:-/storage/mirror/rust}"
  local serve_url="${2:-https://workspace.code-workspace.cloud}"
  local channels="${3:-stable}"
  default_targets="$(printf '%s,' "${RUST_MIRROR_TARGETS[@]}")"
  local targets="${4:-${default_targets%,}}"
  local upstream=${RUST_UPSTREAM}

  log info "Repo root: ${repo_root}"
  log info "Rust channel(s): ${channels}"
  log info "Target(s): ${targets}"
  log info "Upstream url: ${upstream}"

  mkdir -pv "${repo_root}/${channels}"
  if rustup-mirror \
    --mirror "${repo_root}/${channels}" \
    --url "${serve_url}" \
    --upstream-url "${upstream}" \
    --channels "${channels}" \
    --targets "${targets}"; then
    return ${RETURN_FAILURE:-1}
  else
    return ${RETURN_SUCCESS:-0}
  fi
}
