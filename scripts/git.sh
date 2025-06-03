GIT_URL_PATTERN='^(https://|http://|git@|git://)([^/:]+)(/|:)([^/]+)/(.+)(\.git)'

function get_commit_list() {
  local log_file=$1
  local begin=$2
  git log --pretty="%cd_%h" --date="short" --after="${begin}" >"${log_file}"
}

function git_track_lfs() {
  local file_size=${1:-"+1M"}
  log info "using git lfs track files larger than ${file_size}"
  find_files_by_size "${file_size}" | xargs git lfs track
}

function git_checkout_by_date() {
  local git_url=$1
  local git_dir=$2
  local begin=${3:-$(date '+%Y-%m-%d' --date="- 7 days")}
  local end=${4:-$(date '+%Y-%m-%d')}
  local step=${5:-"1days"}

  if [ -z "${git_url}" ] || [ -z "${git_dir}" ]; then
    log error "Usage: git_checkout_by_date <git_url> <git_dir> [begin_date] [end_date] [step]"
    return ${RETURN_FAILURE:-1}
  fi

  git clone "${git_url}" "${git_dir}"
  safe_pushd "${git_dir}" || return ${RETURN_FAILURE:-1}
  commit_log=commit.log

  get_commit_list "${commit_log}" "${begin}"
  # Check if commit log was created and has content
  if [ ! -s "${commit_log}" ]; then
    log warning "No commits found between ${begin} and ${end}"
    safe_popd
    return ${RETURN_FAILURE:-1}
  fi

  iter=$(date '+%Y-%m-%d' -d "${begin}")
  while [[ true ]]; do
    if [[ $(date '+%s' -d ${iter}) -gt $(date '+%s' -d ${end}) ]]; then break; fi
    commit=$(grep ${iter} ${commit_log} | tail -n1)
    if [[ -n "${commit}" ]]; then
      log info "commit: ${commit#*_} at ${commit%_*}"
    fi
    iter=$(date '+%Y-%m-%d' -d "${iter}+${step}")
  done
  safe_popd || return ${RETURN_FAILURE:-1}
}

function git_update_all() {
  for git_dir in $(git_list_repos); do
    safe_pushd "${git_dir}"
    log info "update in ${PWD}"
    git pull --all
    safe_popd
  done
}

function git_top_branch() {
  git branch -a --sort=-committerdate | head -n 20
}

function git_dead_branch() {
  git branch -a --sort=-committerdate | tail -n 20
}

function git_init_submodule() {
  git submodule update --init --recursive
}

function git_update_submodule() {
  git submodule update --init --recursive --remote
}

function git_sync_ignore() {
  # Check if there are any files to remove from cache
  if git ls-files -ci --exclude-standard | grep -q .; then
    git ls-files -ci --exclude-standard | xargs git rm --cached
    log info "Removed ignored files from git cache"
  else
    log info "No ignored files to remove from cache"
  fi
}

function git_clean() {
  git clean -d -x -f
  # Handle empty directory lists safely
  find . -type d -empty | grep -v .git | xargs -r rm -rfv
}

function git_tags() {
  git log --tags --simplify-by-decoration --pretty="format:%ci %d"
}

function git_logs() {
  git log --graph --oneline --all --decorate
}

function git_list_repos() {
  local root=${1:-${PWD}}
  for git_dir in $(find ${root} -name '.git' -type d); do
    if [ -f ${git_dir}/config ]; then
      echo $(dirname ${git_dir})
    fi
  done
}

function git_list_url() {
  for git_dir in $(git_list_repos $@); do
    grep -w 'url' ${git_dir}/.git/config | cut -d' ' -f 3
  done
}

function git_locate() {
  local ref=${1}
  local count=${2:-50}
  local commit=$(git rev-parse ${ref})
  git log --pretty='%Cred%h%Creset -%C(auto)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' -${count} ${commit}~${count}..${commit}
}

function git_graph() {
  local count=${1:-50}
  git log --graph --all --pretty='%Cred%h%Creset -%C(auto)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' -${count}
}

function git_parse_url() {
  local url=$1
  local verbose=$2
  if [ -z "${verbose}" ]; then
    log plain ${url} | sed -E "s~${GIT_URL_PATTERN}~\1 \2 \3 \4 \5 \6~g"
  else
    log plain ${url} | sed -E "s~${GIT_URL_PATTERN}~schema=\1 host=\2 delim=\3 project=\4 repository=\5 suffix=\6~g"
  fi
}

function git_convert_to_https_url() {
  local root=${1:-.}
  git_list_url ${root} | sed -E "s~${GIT_URL_PATTERN}~https://\2/\4/\5\6~g"
}

function git_clone() {
  local url=${1}
  if [ -z "${url}" ]; then
    log error "Usage: git_clone <url>"
    return ${RETURN_FAILURE:-1}
  fi
  shift
  git clone --progress -j$(get_core_count) ${url} "$@"
}

function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi

  ensure_dir "${dir}"
  shift 2
  git -C "${dir}" clone --progress -j$(get_core_count) --recurse-submodules ${url} "$@"
}

function git_tag_to_commit() {
  local url=${1}
  local tag=${2}
  if [ -n "${tag}" ] && [ -n "${url}" ]; then
    git ls-remote --tags ${url} | grep -w ${tag} | cut -f1
  fi
}

function git_remote_heads() {
  local url=${1}
  if [ -n "${url}" ]; then
    git ls-remote --heads ${url}
  fi
}

function git_clone_branches() {
  local url=${1}
  local filter=${2:-.*}

  if [ -z "${url}" ]; then
    log error "Usage: git_clone_branches <url>"
    return ${RETURN_FAILURE}
  fi

  log info "clone branches from ${url}"
  git_remote_heads ${url} | grep -E "${filter}" | head -n 10 | while read commit_id ref_name; do
    branch_name=${ref_name#refs/heads/}
    git clone -b ${branch_name} --depth=1 ${url} ${branch_name}
    log notice "branch ${branch_name}[${commit_id}] cloned into ${PWD}/${branch_name}"
  done
}

function git_update_bare() {
  local root=${1:-${PWD}}
  for head in $(find ${root} -name HEAD); do
    safe_pushd $(dirname ${head})
    git remote prune origin
    git remote update
    safe_popd
  done
}

function git_describe() {
  local commit_id=${1}
  git describe --tags --abbrev=0 ${commit_id}
}

function git_switch() {
  local version=${1}
  if [ -f .gitmodules ]; then
    grep 'path =' .gitmodules | awk '{print $NF}' | xargs rm -rf
    git clean -dfx
  fi

  if [ -n "${version}" ]; then
    git status
    git checkout ${version}
  fi
  if [ -f .gitmodules ]; then
    git submodule sync
    git submodule update --init --recursive
  fi
  git reset --hard
}

function git_search() {
  local pattern="${1}"
  git log -p -S "${pattern}"
}

function git_mirror() {
  local url=${1}
  git_clone ${url} --mirror
}

function git_clone_local() {
  local local_path=${1}
  if [ ! -d "${local_path}" ] || [ ! -f "${local_path}/config" ]; then
    log error "${local_path} not exist or it is not a git repository"
    return ${RETURN_FAILURE}
  fi
  shift
  git_clone file://${local_path} \
    --depth=1 \
    --no-hardlinks \
    --recurse-submodules \
    --shallow-submodules \
    $@
}

function git_config_signed_off_hook() {
  local hook_file=${1:-.git/hooks/commit-msg}
  cat <<'EOF' >${hook_file}
  #!/bin/sh

SOB=$(git var GIT_AUTHOR_IDENT | sed -n 's/^\(.*>\).*$/Signed-off-by: \1/p')
grep -qs "^$SOB" "$1" || echo "$SOB" >> "$1"
EOF
  chmod +x ${hook_file}
}

function git_archive() {
  local branch_name=${1:-HEAD}
  git archive --format=tar --output=$(basename ${PWD}).tar ${branch_name}
}

function git_copy_commit() {
  local dest_dir=${1}
  local commit_id=${2:-HEAD}
  if [ -z "${dest_dir}" ]; then
    log error "Usage: git_copy_commit <dest_dir>"
    return ${RETURN_FAILURE}
  fi
  ensure_dir ${dest_dir}
  git archive --format=tar --output=/dev/stdout ${commit_id} | tar xf - -C ${dest_dir}
}

function git_encode_commit() {
  local commit_id=${1:-HEAD}
  git archive --format=tar --output=/dev/stdout ${commit_id} | encode_tar_stream
}

function git_pull() {
  git pull --rebase $@
}

function git_pull_all() {
  git pull --all --rebase $@
}

function git_push() {
  local remote=$(git config --get branch.$(git rev-parse --abbrev-ref HEAD).remote)
  local branch=$(git branch --show-current)
  if [ -z "${remote}" ]; then
    remote="origin"
  fi
  log notice "git push [${branch}] to [${remote}]"
  git push ${remote} ${branch}
}

function git_push_all() {
  local branch=${1}
  if [ -z "${branch}" ]; then
    branch=$(git branch --show-current)
  else
    shift
  fi
  for remote in $(git remote); do
    if [ "${remote}" = "origin" ]; then
      continue
    fi
    log info "===================   Local:[${branch}], Remote:[${remote}/${branch}]    ==================="
    git push $@ ${remote} ${branch}
    git push ${remote} --tags
  done
}

function git_add() {
  local msg=$@
  git add -A
  git commit -m "${msg}"
}

function git_backup() {
  git_pull
  git_add "backup at $(date_now)"
  git_push
}

function git_commit_id() {
  git rev-parse HEAD
}

function git_create_tag() {
  local tag_name=${1:-$(date_tag)}
  git tag ${tag_name}
  git_push_all
}

function git_delete_tag() {
  local tag_name=${1:-$(date_tag)}

  # delete tag locally
  git tag -d ${tag_name}
  for remote in $(git remote); do
    log info "===================  delete Tag: [${remote}/${tag_name}] ==================="
    git push --delete ${remote} ${tag_name}
  done
}

function git_recreate_tag() {
  local tag_name=${1:-$(date_tag)}
  git_delete_tag ${tag_name}
  git_create_tag ${tag_name}
}

function git_commit_to_patch() {
  local commit_id=${1}
  local output_dir=${2}
  if [ -z "${commit_id}" ] || [ -z "${output_dir}" ]; then
    log error "Usage: git_commit_to_patch <commit_id> <output_dir>"
    return ${RETURN_FAILURE}
  fi
  git format-patch -1 ${commit_id} -o ${output_dir}
}

function git_revert_patch() {
  local commit_id=${1}
  local output_dir=${2:-$(pwd)}

  if [ -z "${commit_id}" ]; then
    log error "Usage: git_revert_patch <commit_id> [output_dir]"
    return ${RETURN_FAILURE:-1}
  fi

  # Validate commit ID exists
  if ! git rev-parse --quiet --verify "${commit_id}" >/dev/null; then
    log error "Invalid commit ID: ${commit_id}"
    return ${RETURN_FAILURE:-1}
  fi

  # Ensure output directory exists
  ensure_dir "${output_dir}"

  # Create revert patch filename based on commit
  local short_hash=$(git rev-parse --short "${commit_id}")
  local revert_filename="${output_dir}/revert-${short_hash}.patch"

  log info "Generating revert patch for commit ${short_hash} to ${revert_filename}"

  # Generate the revert patch
  if ! git show --pretty="From %H %cd%nFrom: %an <%ae>%nDate: %ad%nSubject: [PATCH] Revert \"$(git log -1 --pretty=%s ${commit_id})\"%n%nThis reverts commit ${commit_id}.%n" --binary -R "${commit_id}" > "${revert_filename}"; then
    log error "Failed to create revert patch for commit ${short_hash}"
    return ${RETURN_FAILURE:-1}
  fi

  log notice "Revert patch created: ${revert_filename}"
  return ${RETURN_SUCCESS:-0}
}

function git_latest_added_files() {
  local count=${1:-30}
  local tmp_file=$(mktemp)

  # First collect all file additions in the temp file
  git rev-list --all --no-merges --first-parent --format='%aI %H' --since="2 years ago" |
    awk '!/^commit/ {print $1, $2}' |
    while read -r timestamp commit_hash; do
      git diff-tree --no-commit-id --name-only --diff-filter=AR -r "$commit_hash" |
        while read -r file; do
          # Only include files that still exist
          if [[ -n "$file" ]] && git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            if ! grep -q " $file\$" "$tmp_file"; then
              echo "$timestamp $file" >>"$tmp_file"
            fi
          fi
        done
    done

  # Sort by timestamp and output the results
  if [[ -f "$tmp_file" ]]; then
    sort -r "$tmp_file" | head -n "$count"
    rm -f "$tmp_file"
  fi
}

function git_latest_updated_files() {
  local count=${1:-30}
  local tmp_file=$(mktemp)

  # First collect all file modifications in the temp file
  git rev-list --all --no-merges --first-parent --format='%aI %H' --since="2 years ago" |
    awk '!/^commit/ {print $1, $2}' |
    while read -r timestamp commit_hash; do
      git diff-tree --no-commit-id --name-only --diff-filter=M -r "$commit_hash" |
        while read -r file; do
          # Only include files that still exist
          if [[ -n "$file" ]] && git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            if ! grep -q " $file\$" "$tmp_file"; then
              echo "$timestamp $file" >>"$tmp_file"
            fi
          fi
        done
    done

  # Sort by timestamp and output the results
  if [[ -f "$tmp_file" ]]; then
    sort -r "$tmp_file" | head -n "$count"
    rm -f "$tmp_file"
  fi
}

function git_setup_ssh_repo() {
  local repo="${1}"
  local home="${DATA_DIR:-/data}/git"
  local username=git
  local ssh_dir="${home}/.ssh"
  local auth_keys_src="${HOME}/.ssh/authorized_keys"
  local auth_keys_dst="${ssh_dir}/authorized_keys"
  local ssh_setup_needed=false

  if [ -z "${repo}" ]; then
    log error "Usage: git_setup_ssh_repo <repo>"
    return ${RETURN_FAILURE:-1}
  fi

  repo=${repo#/}
  repo=${repo%.git}.git

  # Check if SSH setup is needed
  if [ ! -d "${ssh_dir}" ] || [ ! -f "${auth_keys_dst}" ]; then
    ssh_setup_needed=true
    log info "SSH infrastructure not found, will initialize"
  else
    # Verify SSH setup integrity
    if [ ! -r "${auth_keys_dst}" ] || [ "$(stat -c '%U:%G' "${ssh_dir}" 2>/dev/null)" != "${username}:${username}" ]; then
      ssh_setup_needed=true
      log info "SSH infrastructure needs repair"
    else
      log info "SSH infrastructure already configured, skipping setup"
    fi
  fi

  # Validate source authorization file only if SSH setup is needed
  if [ "${ssh_setup_needed}" = "true" ] && [ ! -f "${auth_keys_src}" ]; then
    log error "Source SSH authorized_keys missing: ${auth_keys_src}"
    return ${RETURN_FAILURE:-1}
  fi

  # User management - check if user exists and create if needed
  if ! getent passwd "${username}" >/dev/null 2>&1; then
    log info "Creating user: '${username}' with home: ${home}"
    if ! useradd -m -U "${username}" -d "${home}" -s /usr/bin/git-shell; then
      log error "User creation failed: ${username}"
      return ${RETURN_FAILURE:-1}
    fi
    # Ensure home directory ownership
    [ -d "${home}" ] && chown "${username}:${username}" "${home}"
    ssh_setup_needed=true
  else
    log info "User already exists: '${username}'"
  fi

  # SSH setup only if needed
  if [ "${ssh_setup_needed}" = "true" ]; then
    log info "Setting up SSH infrastructure"

    # Create SSH directory with validation
    if ! mkdir -p "${ssh_dir}"; then
      log error "Directory creation failed: ${ssh_dir}"
      return ${RETURN_FAILURE:-1}
    fi

    # Copy keys with verification
    if ! cp -fv "${auth_keys_src}" "${auth_keys_dst}"; then
      log error "Key copy failed: ${auth_keys_src} -> ${auth_keys_dst}"
      return ${RETURN_FAILURE:-1}
    fi

    # Final validation
    if [ ! -f "${auth_keys_dst}" ]; then
      log error "SSH setup incomplete: ${auth_keys_dst} missing"
      return ${RETURN_FAILURE:-1}
    fi

    # Permission hardening
    if ! chown -R "${username}:${username}" "${home}"; then
      log error "Ownership change failed: ${home}"
      return ${RETURN_FAILURE:-1}
    fi
    chmod 700 "${ssh_dir}" || return ${RETURN_FAILURE:-1}
    chmod 600 "${auth_keys_dst}" || return ${RETURN_FAILURE:-1}

    log notice "SSH infrastructure setup completed"
  fi

  # Git repository setup
  cd "${home}" || return ${RETURN_FAILURE:-1}

  if [ -d "${repo}" ]; then
    if [ -f "${repo}/config" ] && grep -q "bare = true" "${repo}/config"; then
      log info "Git repository already exists: ${repo}"
    else
      log error "Directory exists but is not a bare git repository: ${repo}"
      return ${RETURN_FAILURE:-1}
    fi
  else
    log info "Creating bare git repository: ${repo}"
    if ! git init --bare "${repo}"; then
      log error "Git repository initialization failed: ${repo}"
      return ${RETURN_FAILURE:-1}
    fi

    # Ensure repository ownership
    if ! chown -R "${username}:${username}" "${repo}"; then
      log error "Repository ownership change failed: ${repo}"
      return ${RETURN_FAILURE:-1}
    fi

    log notice "Git repository created: ${repo}"
  fi

  log notice "Git remote setup complete at [${repo}]. Add with: git remote add <remote_name> git@<ssh_name>:${repo}"
  return ${RETURN_SUCCESS:-0}
}

function git_list_unstaged_repo() {
  local root=${1:-${PWD}}
  for repo in $(git_list_repos "${root}"); do
    safe_pushd "${repo}" || continue
    local info=$(git_info)
    # '*' in branch indicates uncommitted changes
    if [[ "${info}" == *"*"* ]]; then
      echo "${repo}"
    fi
    safe_popd
  done
}

function git_info() {
  local git_info=""
  if [ -d .git ] && [ -f .git/config ]; then
    if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null; then
      local git_branch=$(
        git symbolic-ref --short HEAD 2>/dev/null ||
          git describe --tags --exact-match 2>/dev/null ||
          git rev-parse --short HEAD 2>/dev/null ||
          echo "(detached)"
      )
      local git_status=$(git status --porcelain 2>/dev/null)
      if [ -z "${git_status}" ]; then
        local git_info="[git: ${BOLD_GREEN}${git_branch}${CLEAR}]"
      else
        local git_info="[git: ${BOLD_RED}${git_branch}*${CLEAR}]"
      fi
    fi
  fi
  if is_macos; then
    echo "${git_info}"
  else
    echo -e "${git_info}"
  fi
}

function git_status_repos() {
  local root=${1:-${PWD}}
  local show_all=${2:-false}

  if [ ! -d "${root}" ]; then
    log error "Directory does not exist: ${root}"
    return ${RETURN_FAILURE:-1}
  fi

  # Print table header
  printf "%-40s | %-15s | %-10s | %s\n" "Repository" "Branch" "Status" "Details"
  printf "%-40s-|-%-15s-|-%-10s-|-%s\n" "$(printf '%0.s-' {1..40})" "$(printf '%0.s-' {1..15})" "$(printf '%0.s-' {1..7})" "$(printf '%0.s-' {1..20})"

  # Process each repository
  for repo_path in $(git_list_repos "${root}"); do
    safe_pushd "${repo_path}" >/dev/null || continue

    # Get repository name (last component of path)
    local repo_name=$(basename "${repo_path}")

    # Get current branch
    local branch=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo "(detached)")

    # Get status information
    local status_output=$(git status --porcelain 2>/dev/null)
    local status_count=$(echo "${status_output}" | grep -v '^$$' | wc -l | tr -d ' ')
    local status_details=""

    # Determine status and details
    if [ -z "${status_output}" ]; then
      local status="Clean"
      if [ "${show_all}" = "true" ]; then
        # For clean repositories, show commit information if show_all is true
        local last_commit=$(git log -1 --pretty=format:"%h - %s (%cr)" 2>/dev/null)
        status_details="Last: ${last_commit}"
      else
        status_details="-"
      fi
    else
      local status="Modified"
      # Count of each type of change
      local added=$(echo "${status_output}" | grep -c '^A')
      local modified=$(echo "${status_output}" | grep -c '^M')
      local deleted=$(echo "${status_output}" | grep -c '^D')
      local untracked=$(echo "${status_output}" | grep -c '^\?')

      status_details="M:${modified} A:${added} D:${deleted} ?:${untracked}"
    fi

    # Print repository info in table row
    printf "%-40s | %-15s | %-10s | %s\n" "${repo_name}" "${branch}" "${status}" "${status_details}"

    safe_popd >/dev/null
  done

  return ${RETURN_SUCCESS:-0}
}

# Git hook functions - Generate content for each type of git hook

function git_hook_install() {
  local hook_type=${1}
  local target_dir=${2:-.git/hooks}

  if [ -z "${hook_type}" ]; then
    log error "Usage: git_hook_install <hook_type> [target_dir]"
    return ${RETURN_FAILURE:-1}
  fi

  if [ ! -d "${target_dir}" ]; then
    log error "Target directory does not exist: ${target_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  local hook_content=""
  local hook_file="${target_dir}/${hook_type}"

  # Generate hook content based on type
  case "${hook_type}" in
    pre-commit)
      hook_content=$(git_hook_pre_commit)
      ;;
    commit-msg)
      hook_content=$(git_hook_commit_msg)
      ;;
    pre-push)
      hook_content=$(git_hook_pre_push)
      ;;
    pre-receive)
      hook_content=$(git_hook_pre_receive)
      ;;
    post-update)
      hook_content=$(git_hook_post_update)
      ;;
    update)
      hook_content=$(git_hook_update)
      ;;
    pre-merge-commit)
      hook_content=$(git_hook_pre_merge_commit)
      ;;
    prepare-commit-msg)
      hook_content=$(git_hook_prepare_commit_msg)
      ;;
    pre-rebase)
      hook_content=$(git_hook_pre_rebase)
      ;;
    applypatch-msg)
      hook_content=$(git_hook_applypatch_msg)
      ;;
    pre-applypatch)
      hook_content=$(git_hook_pre_applypatch)
      ;;
    push-to-checkout)
      hook_content=$(git_hook_push_to_checkout)
      ;;
    sendemail-validate)
      hook_content=$(git_hook_sendemail_validate)
      ;;
    *)
      log error "Unknown hook type: ${hook_type}"
      log notice "Available hook types: pre-commit, commit-msg, pre-push, pre-receive, post-update, update, pre-merge-commit, prepare-commit-msg, pre-rebase, applypatch-msg, pre-applypatch, push-to-checkout, sendemail-validate"
      return ${RETURN_FAILURE:-1}
      ;;
  esac

  echo "${hook_content}" > "${hook_file}"
  chmod +x "${hook_file}"
  log notice "Git hook installed: ${hook_file}"

  return ${RETURN_SUCCESS:-0}
}

function git_hook_install_all() {
  local target_dir=${1:-.git/hooks}

  if [ ! -d "${target_dir}" ]; then
    log error "Target directory does not exist: ${target_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  # Install all common hooks
  git_hook_install pre-commit "${target_dir}"
  git_hook_install commit-msg "${target_dir}"
  git_hook_install pre-push "${target_dir}"
  git_hook_install pre-merge-commit "${target_dir}"
  git_hook_install prepare-commit-msg "${target_dir}"
  git_hook_install pre-rebase "${target_dir}"

  # Server-side hooks (usually only needed for git servers)
  if [ -n "${2}" ] && [ "${2}" = "server" ]; then
    git_hook_install update "${target_dir}"
    git_hook_install pre-receive "${target_dir}"
    git_hook_install post-update "${target_dir}"
  fi

  log notice "All git hooks installed in ${target_dir}"
  return ${RETURN_SUCCESS:-0}
}

function git_hook_pre_commit() {
  cat <<'EOF'
#!/bin/bash

# Git pre-commit hook to run checks before committing
# Exit with non-zero status to abort the commit

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "${STAGED_FILES}" ]; then
    echo "No files staged for commit"
    exit 0
fi

EXIT_CODE=0

# Check for whitespace errors
echo "Checking for whitespace errors..."
if ! git diff-index --check --cached HEAD --; then
    echo "Whitespace errors found. Please fix them before committing."
    EXIT_CODE=1
fi

# Check for large files
echo "Checking for large files..."
for FILE in ${STAGED_FILES}; do
    FILE_SIZE=$(du -k "${FILE}" | cut -f1)
    if [ "${FILE_SIZE}" -gt 500 ]; then
        echo "Warning: ${FILE} is ${FILE_SIZE}KB - consider using Git LFS for large files"
    fi
done

# Run custom checks here
# ...

if [ ${EXIT_CODE} -ne 0 ]; then
    echo "Pre-commit checks failed. Commit aborted."
fi

exit ${EXIT_CODE}
EOF
}

function git_hook_commit_msg() {
  cat <<'EOF'
#!/bin/bash

# Git commit-msg hook to validate commit messages
# $1 is the path to the temporary file containing the commit message

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "${COMMIT_MSG_FILE}")

# Check commit message format
# Example: require a ticket number at the beginning of the message
if ! grep -qE "^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([a-z0-9_-]+\))?: .+" "${COMMIT_MSG_FILE}"; then
    echo "Invalid commit message format."
    echo "Please use the format: <type>(<scope>): <description>"
    echo "Where <type> is one of: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert"
    exit 1
fi

# Check minimum length
if [ ${#COMMIT_MSG} -lt 10 ]; then
    echo "Commit message is too short (minimum 10 characters)"
    exit 1
fi

# Check maximum length of first line
FIRST_LINE=$(head -n 1 "${COMMIT_MSG_FILE}")
if [ ${#FIRST_LINE} -gt 72 ]; then
    echo "First line of commit message is too long (maximum 72 characters)"
    exit 1
fi

# Add Signed-off-by line if not present
SOB=$(git var GIT_AUTHOR_IDENT | sed -n 's/^\(.*>\).*$/Signed-off-by: \1/p')
if ! grep -qs "^$SOB" "${COMMIT_MSG_FILE}"; then
    echo "" >> "${COMMIT_MSG_FILE}"
    echo "$SOB" >> "${COMMIT_MSG_FILE}"
fi

exit 0
EOF
}

function git_hook_pre_push() {
  cat <<'EOF'
#!/bin/bash

# Git pre-push hook
# $1 is the name of the remote to which the push is being done
# $2 is the URL to which the push is being done

REMOTE="$1"
URL="$2"

Z40=0000000000000000000000000000000000000000

# Get the list of refs being pushed
while read LOCAL_REF LOCAL_SHA REMOTE_REF REMOTE_SHA; do
    if [ "${LOCAL_SHA}" = ${Z40} ]; then
        # Branch deletion, do nothing
        continue
    fi

    if [ "${REMOTE_SHA}" = ${Z40} ]; then
        # New branch, examine all commits
        RANGE="${LOCAL_SHA}"
    else
        # Update to existing branch, examine new commits
        RANGE="${REMOTE_SHA}..${LOCAL_SHA}"
    fi

    # Check for WIP commits
    if git log --grep="WIP" "${RANGE}" | grep -q "WIP"; then
        echo "Error: WIP commit detected. Please remove WIP commits before pushing."
        exit 1
    fi

    # Check for TODO commits
    if git log --grep="TODO" "${RANGE}" | grep -q "TODO"; then
        echo "Warning: TODO found in commit message. Consider addressing TODOs before pushing."
    fi

    # Run tests if applicable
    # if [ -f "run_tests.sh" ]; then
    #     echo "Running tests..."
    #     if ! ./run_tests.sh; then
    #         echo "Tests failed. Push aborted."
    #         exit 1
    #     fi
    # fi
done

exit 0
EOF
}

function git_hook_pre_receive() {
  cat <<'EOF'
#!/bin/bash

# Git pre-receive hook (server-side)
# Reads stdin in the format: <old-value> <new-value> <ref-name>

Z40=0000000000000000000000000000000000000000

while read OLD_REV NEW_REV REF_NAME; do
    # Branch or tag deletion
    if [ "${NEW_REV}" = ${Z40} ]; then
        echo "Deleting ${REF_NAME}"
        continue
    fi

    # New branch or tag
    if [ "${OLD_REV}" = ${Z40} ]; then
        echo "Creating ${REF_NAME}"
        RANGE="${NEW_REV}"
    else
        # Update to existing branch or tag
        echo "Updating ${REF_NAME}"
        RANGE="${OLD_REV}..${NEW_REV}"
    fi

    # Check for protected branches
    if [ "${REF_NAME}" = "refs/heads/main" ] || [ "${REF_NAME}" = "refs/heads/master" ]; then
        # Check if user has permission (example)
        # CURRENT_USER=$(git config user.name)
        # if ! echo "${AUTHORIZED_USERS}" | grep -q "${CURRENT_USER}"; then
        #     echo "Error: You don't have permission to push to ${REF_NAME}"
        #     exit 1
        # fi
        echo "Warning: Pushing to protected branch ${REF_NAME}"
    fi

    # Check for file size limits
    TOO_LARGE_FILES=$(git rev-list --objects ${RANGE} | \
        git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
        awk '/^blob/ && $3 >= 10485760 {print $4}' | sort -u)

    if [ -n "${TOO_LARGE_FILES}" ]; then
        echo "Error: Files exceeding size limit (10MB) found:"
        echo "${TOO_LARGE_FILES}"
        echo "Consider using Git LFS for large files."
        exit 1
    fi
done

exit 0
EOF
}

function git_hook_post_update() {
  cat <<'EOF'
#!/bin/bash

# Git post-update hook (server-side)
# This hook is called after a successful push to update secondary services
# $@ contains the list of refs that were updated

echo "Running post-update hook"

# Update reference repository for git daemon
# git update-server-info

# Update any deployment systems
# ./deploy.sh "$@"

# Notify CI/CD system
# curl -s -X POST "https://ci.example.com/trigger?refs=$*"

# Notify team chat
# MESSAGE="Repository updated with refs: $*"
# curl -s -X POST -H "Content-Type: application/json" -d "{\"text\":\"${MESSAGE}\"}" "https://chat.example.com/webhook"

echo "Post-update hook completed"
exit 0
EOF
}

function git_hook_update() {
  cat <<'EOF'
#!/bin/bash

# Git update hook (server-side)
# $1 is the ref being updated
# $2 is the old object name
# $3 is the new object name

REF_NAME="$1"
OLD_REV="$2"
NEW_REV="$3"

# Get the branch or tag name
if [[ "${REF_NAME}" =~ ^refs/heads/ ]]; then
    BRANCH_NAME="${REF_NAME#refs/heads/}"
    echo "Branch ${BRANCH_NAME} is being updated"
elif [[ "${REF_NAME}" =~ ^refs/tags/ ]]; then
    TAG_NAME="${REF_NAME#refs/tags/}"
    echo "Tag ${TAG_NAME} is being updated"
else
    echo "Ref ${REF_NAME} is being updated"
fi

# Check for force pushes
if [ "${OLD_REV}" != "0000000000000000000000000000000000000000" ] &&
   ! git merge-base --is-ancestor "${OLD_REV}" "${NEW_REV}"; then
    echo "Warning: Force push detected on ${REF_NAME}"

    # Optionally prevent force pushes to specific branches
    if [ "${BRANCH_NAME}" = "main" ] || [ "${BRANCH_NAME}" = "master" ]; then
        echo "Error: Force pushing to ${BRANCH_NAME} is not allowed"
        exit 1
    fi
fi

# Check for specific file patterns
RESTRICTED_FILES=$(git diff --name-only "${OLD_REV}" "${NEW_REV}" | grep -E '\.env$|password|secret|credential' || true)
if [ -n "${RESTRICTED_FILES}" ]; then
    echo "Warning: Potentially sensitive files detected:"
    echo "${RESTRICTED_FILES}"
    echo "Make sure these files don't contain sensitive information."
    # Uncomment to block the push
    # exit 1
fi

exit 0
EOF
}

function git_hook_pre_merge_commit() {
  cat <<'EOF'
#!/bin/bash

# Git pre-merge-commit hook
# This hook is called before a merge commit is created

# Get the name of the branch being merged
MERGE_BRANCH=$(git symbolic-ref --short HEAD)
echo "Preparing to create merge commit on ${MERGE_BRANCH}"

# Check for conflicts
CONFLICTS=$(git diff --name-only --diff-filter=U)
if [ -n "${CONFLICTS}" ]; then
    echo "Warning: Unresolved conflicts in the following files:"
    echo "${CONFLICTS}"
    echo "Please resolve conflicts before continuing."
    # Uncomment to block the commit
    # exit 1
fi

# Run tests or other validations
# if [ -f "./run_tests.sh" ]; then
#     echo "Running tests before merge commit..."
#     if ! ./run_tests.sh; then
#         echo "Tests failed. Merge commit aborted."
#         exit 1
#     fi
# fi

exit 0
EOF
}

function git_hook_prepare_commit_msg() {
  cat <<'EOF'
#!/bin/bash

# Git prepare-commit-msg hook
# $1 is the name of the file containing the commit message
# $2 is the source of the commit message (message|template|merge|squash|commit)
# $3 is the commit SHA1 (only given when amending)

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"
SHA1="$3"

# For merge commits, add the merged branch name
if [ "${COMMIT_SOURCE}" = "merge" ]; then
    MERGE_BRANCH=$(git rev-parse --abbrev-ref MERGE_HEAD)
    echo "Merge branch '${MERGE_BRANCH}'" > "${COMMIT_MSG_FILE}"
    exit 0
fi

# For squash commits, keep the original messages
if [ "${COMMIT_SOURCE}" = "squash" ]; then
    exit 0
fi

# For regular commits, prepend branch name if it contains a ticket number
if [ -z "${COMMIT_SOURCE}" ] || [ "${COMMIT_SOURCE}" = "message" ]; then
    BRANCH_NAME=$(git symbolic-ref --short HEAD)

    # Extract ticket number from branch name (e.g., feature/JIRA-123-description)
    if [[ "${BRANCH_NAME}" =~ [A-Z]+-[0-9]+ ]]; then
        TICKET="${BASH_REMATCH[0]}"

        # Only prepend if not already in the message
        if ! grep -q "${TICKET}" "${COMMIT_MSG_FILE}"; then
            TEMP_FILE=$(mktemp)
            echo "[${TICKET}] $(cat ${COMMIT_MSG_FILE})" > "${TEMP_FILE}"
            cat "${TEMP_FILE}" > "${COMMIT_MSG_FILE}"
            rm "${TEMP_FILE}"
        fi
    fi
fi

exit 0
EOF
}

function git_hook_pre_rebase() {
  cat <<'EOF'
#!/bin/bash

# Git pre-rebase hook
# $1 is the upstream branch we're rebasing onto
# $2 is the branch being rebased (or empty when rebasing the current branch)

UPSTREAM="$1"
BRANCH="$2"

# If branch is empty, get the current branch
if [ -z "${BRANCH}" ]; then
    BRANCH=$(git symbolic-ref --short HEAD)
fi

echo "Preparing to rebase ${BRANCH} onto ${UPSTREAM}"

# Prevent rebasing of protected branches
if [ "${BRANCH}" = "master" ] || [ "${BRANCH}" = "main" ]; then
    echo "Error: Rebasing ${BRANCH} is not allowed. Please create a new branch instead."
    exit 1
fi

# Check if the branch has been pushed
REMOTE_REF=$(git for-each-ref --format='%(upstream:short)' refs/heads/"${BRANCH}")
if [ -n "${REMOTE_REF}" ]; then
    echo "Warning: Branch ${BRANCH} has a remote counterpart (${REMOTE_REF})."
    echo "Rebasing will rewrite history and require a force push."

    # Uncomment to prevent rebasing of pushed branches
    # echo "Error: Rebasing a pushed branch is not allowed."
    # exit 1
fi

# Additional checks before rebasing
# ...

exit 0
EOF
}

function git_hook_applypatch_msg() {
  cat <<'EOF'
#!/bin/bash

# Git applypatch-msg hook
# $1 is the name of the file that contains the proposed commit message

COMMIT_MSG_FILE="$1"
COMMIT_MSG=$(cat "${COMMIT_MSG_FILE}")

# Check if the commit message meets our standards
if [ ${#COMMIT_MSG} -lt 10 ]; then
    echo "Error: Commit message is too short (minimum 10 characters)"
    exit 1
fi

# Check for ticket reference
if ! grep -qE '\b[A-Z]+-[0-9]+\b' "${COMMIT_MSG_FILE}"; then
    echo "Warning: No ticket reference found in the commit message."
    echo "Consider adding a ticket reference like JIRA-123."
fi

# Check for imperative mood in the first line
FIRST_LINE=$(head -n 1 "${COMMIT_MSG_FILE}")
if ! echo "${FIRST_LINE}" | grep -qE '^(Add|Fix|Update|Change|Remove|Refactor|Document|Style|Test|Optimize|Merge|Revert|Bump)'; then
    echo "Warning: First line should begin with a verb in the imperative mood."
    echo "Examples: Add, Fix, Update, Change, Remove, Refactor, etc."
fi

exit 0
EOF
}

function git_hook_pre_applypatch() {
  cat <<'EOF'
#!/bin/bash

# Git pre-applypatch hook
# This hook is invoked by git-am after the patch is applied but before a commit is made

# Run tests to verify that the patch doesn't break anything
echo "Running tests before applying patch..."

# Example: Run project-specific tests
# if [ -f "./run_tests.sh" ]; then
#     if ! ./run_tests.sh; then
#         echo "Tests failed. Patch will not be applied."
#         exit 1
#     fi
# fi

# Verify coding standards
echo "Checking coding standards..."

# Example: Run linters or style checkers
# if command -v shellcheck >/dev/null 2>&1; then
#     SHELL_SCRIPTS=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.sh$')
#     if [ -n "${SHELL_SCRIPTS}" ]; then
#         if ! shellcheck ${SHELL_SCRIPTS}; then
#             echo "Shell script issues found. Please fix before applying patch."
#             exit 1
#         fi
#     fi
# fi

echo "Pre-applypatch checks passed."
exit 0
EOF
}

function git_hook_push_to_checkout() {
  cat <<'EOF'
#!/bin/bash

# Git push-to-checkout hook
# This hook is invoked when a git-receive-pack runs with the option to update the working tree
# $1 is the branch being updated
# $2 is the old object name
# $3 is the new object name

BRANCH="$1"
OLD_REV="$2"
NEW_REV="$3"

echo "Updating working tree for branch ${BRANCH}"

# Check if we need to run any build processes
if [ -f "package.json" ]; then
    echo "Node.js project detected, running npm install..."
    npm install

    if grep -q "build" package.json; then
        echo "Running build script..."
        npm run build
    fi
fi

# Check if we need to restart any services
if [ -f "docker-compose.yml" ]; then
    echo "Docker Compose project detected, restarting services..."
    docker-compose down && docker-compose up -d
fi

# Example: Reload a web server if configuration changed
if git diff --name-only "${OLD_REV}" "${NEW_REV}" | grep -q "nginx.conf"; then
    echo "Nginx configuration changed, reloading nginx..."
    # systemctl reload nginx
fi

echo "Working tree updated successfully."
exit 0
EOF
}

function git_hook_sendemail_validate() {
  cat <<'EOF'
#!/bin/bash

# Git sendemail-validate hook
# This hook validates patch emails before they are sent
# $1 is the file containing the email to be sent
# $2 is the email format (patch|suppress-cc|cc|compose|default)

EMAIL_FILE="$1"
EMAIL_FORMAT="$2"

echo "Validating email before sending (${EMAIL_FORMAT})"

# Check for sensitive information
if grep -i -E "password|secret|token|key|credential" "${EMAIL_FILE}"; then
    echo "Error: Potential sensitive information found in email."
    echo "Please review the email content before sending."
    exit 1
fi

# Verify patch formatting
if [ "${EMAIL_FORMAT}" = "patch" ]; then
    # Check patch format
    if ! grep -q "^---$" "${EMAIL_FILE}"; then
        echo "Warning: Patch might not be correctly formatted."
    fi

    # Check for sufficient context lines
    if grep -q "^@@ .* @@$" "${EMAIL_FILE}"; then
        CONTEXT_LINES=$(grep -E "^@@ .* @@$" "${EMAIL_FILE}" | grep -oE ',[0-9]+' | sed 's/,//' | sort -n | head -n 1)
        if [ -n "${CONTEXT_LINES}" ] && [ "${CONTEXT_LINES}" -lt 3 ]; then
            echo "Warning: Patch has less than 3 context lines. Consider using more context."
        fi
    fi

    # Check subject prefix
    if ! grep -q "^\[PATCH\]" "${EMAIL_FILE}"; then
        echo "Warning: Subject line should start with [PATCH]."
    fi
fi

echo "Email validation passed."
exit 0
EOF
}
