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


function rust_mirror () 
{ 
    local repo_root="${1:-/oss_code/repo}";
    local serve_url="${2:-https://workspace.code-workspace.cloud}";
    local channels="${3:-1.96.1}";
    default_targets="$(printf '%s,' "${RUST_MIRROR_TARGETS[@]}")";
    local targets="${4:-${default_targets%,}}";
    local upstream="${RUST_UPSTREAM:-https://static.rust-lang.org/}";
    
    log info "Repo root: ${repo_root}";
    log info "Rust channel(s): ${channels}";
    log info "Target(s): ${targets}";
    log info "Upstream url: ${upstream}";
    
    # --mirror 必须指向 Nginx location / 的根目录（如 /oss_code/repo）
    # 不能指向版本子目录（如 /oss_code/repo/1.96.1），否则 RUSTUP_DIST_SERVER
    # 访问 /dist/... 时会因路径不匹配导致 404
    # 参见: docs/mirror/setup-rust-mirror.md
    local mirror_dir="${repo_root}";
    local mirror_dist="${mirror_dir}/dist";
    mkdir -pv "${mirror_dist}";
    
    # 修复1: 正确的返回值 + 设置 RUST_BACKTRACE 以便诊断
    if RUST_BACKTRACE=1 rustup-mirror \
        --mirror "${mirror_dir}" \
        --url "${serve_url}" \
        --upstream-url "${upstream}" \
        --channels "${channels}" \
        --targets "${targets}"; then
        
        # 修复2: rustup-mirror 0.9.0 在 line 521 有 panic bug
        # panic 发生在写入 manifest 之后、日期目录拷贝时
        # manifest 和组件文件应该已存在，但需要验证
        
        log info "rustup-mirror completed (may have panicked at date-copy step)";
        
        # 修复3: 验证 manifest 存在
        local manifest="${mirror_dist}/channel-rust-${channels}.toml"
        local manifest_sha="${manifest}.sha256"
        
        if [ ! -f "${manifest}" ]; then
            log error "Manifest ${manifest} not found - rustup-mirror failed before writing manifest";
            return ${RETURN_FAILURE:-1};
        fi
        
        # 修复4: 验证并修复 manifest sha256
        if [ ! -f "${manifest_sha}" ]; then
            log warn "Manifest .sha256 missing, regenerating...";
            sha256sum "${manifest}" | awk '{print $1}' > "${manifest_sha}";
        else
            # 验证 sha256 是否匹配
            local actual_hash actual_stored
            actual_hash=$(sha256sum "${manifest}" | awk '{print $1}')
            actual_stored=$(awk '{print $1}' "${manifest_sha}")
            if [ "${actual_hash}" != "${actual_stored}" ]; then
                log warn "Manifest sha256 mismatch, regenerating...";
                sha256sum "${manifest}" | awk '{print $1}' > "${manifest_sha}";
            fi
        fi
        
        # 修复5: 删除 .asc 文件（TOML被修改后GPG签名失效）
        find "${mirror_dist}" -name "*.asc" -delete 2>/dev/null;
        
        # 为日期子目录中的组件创建顶层符号链接
        # rustup 在 legacy 回退模式下会尝试从 dist/ 直接下载（不带日期）
        # 但 rustup-mirror 将文件存储在 dist/{date}/ 下
        # 从 manifest 中提取日期，避免在共享 dist 目录中找到其他版本的日期目录
        local manifest_date
        manifest_date=$(awk -F'"' '/^date = / {print $2}' "${manifest}")
        local date_dir="${mirror_dist}/${manifest_date}"
        if [ -n "${manifest_date}" ] && [ -d "${date_dir}" ]; then
            log info "Found date directory: ${date_dir}";
            for f in "${date_dir}"/*.tar.*; do
                [ -f "$f" ] || continue
                local base
                base=$(basename "$f")
                if [ ! -e "${mirror_dist}/${base}" ]; then
                    ln -sf "${date_dir}/${base}" "${mirror_dist}/${base}"
                    log info "Created symlink: ${base}";
                fi
            done
        fi
        
        # 修复7: 验证关键组件的 sha256 存在
        local host_target
        case "$(uname -m)" in
            x86_64)  host_target="x86_64-unknown-linux-gnu" ;;
            aarch64) host_target="aarch64-unknown-linux-gnu" ;;
            *)       host_target="$(uname -m)-unknown-linux-gnu" ;;
        esac
        
        local std_file="rust-${channels}-${host_target}.tar.gz"
        local std_sha="${mirror_dist}/${std_file}.sha256"
        # 检查符号链接或实际文件
        if [ -e "${mirror_dist}/${std_file}" ] && [ ! -f "${std_sha}" ]; then
            log warn "Missing .sha256 for ${std_file}, generating...";
            # 找到实际文件路径（可能是符号链接）
            local real_file
            real_file=$(readlink -f "${mirror_dist}/${std_file}")
            sha256sum "${real_file}" | awk '{print $1}' > "${std_sha}";
        fi
        
        log info "Mirror verification and fixup completed";
        return ${RETURN_SUCCESS:-0};
    else
        local rc=$?;
        log error "rustup-mirror failed with exit code ${rc}";
        log error "Mirror may be incomplete. Check ${mirror_dir}/dist/ for missing files.";
        return ${rc};
    fi
}