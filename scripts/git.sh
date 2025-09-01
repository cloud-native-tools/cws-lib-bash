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
    if [[ -n ${commit} ]]; then
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

function git_active_branch() {
  local topn=${1:-20}

  # Print table header with wider columns for Branch and Commit Message
  printf "%-60s | %-20s | %-25s | %s\n" "Branch" "Last Commit" "Author" "Commit Message"
  printf "%-60s-|-%-20s-|-%-25s-|-%s\n" "$(printf '%0.s-' {1..60})" "$(printf '%0.s-' {1..20})" "$(printf '%0.s-' {1..25})" "$(printf '%0.s-' {1..50})"

  # Get branch information with commit details, sorted by most recent commits first
  git for-each-ref --sort=-committerdate --format='%(refname:short)|%(committerdate:relative)|%(authorname)|%(subject)' refs/heads refs/remotes | head -n ${topn} | while IFS='|' read -r branch_name commit_date author subject; do
    # Adjust column widths - Branch: 60, Date: 20, Author: 25, Message: no truncation
    branch_display=$(printf "%-60.60s" "${branch_name}")
    date_display=$(printf "%-20.20s" "${commit_date}")
    author_display=$(printf "%-25.25s" "${author}")
    # Don't truncate the commit message, let it display fully

    printf "%-60s | %-20s | %-25s | %s\n" "${branch_display}" "${date_display}" "${author_display}" "${subject}"
  done
}

function git_dead_branch() {
  local topn=${1:-20}

  # Print table header with wider columns for Branch and Commit Message
  printf "%-60s | %-20s | %-25s | %s\n" "Branch" "Last Commit" "Author" "Commit Message"
  printf "%-60s-|-%-20s-|-%-25s-|-%s\n" "$(printf '%0.s-' {1..60})" "$(printf '%0.s-' {1..20})" "$(printf '%0.s-' {1..25})" "$(printf '%0.s-' {1..50})"

  # Get branch information with commit details, sorted by oldest commits first
  git for-each-ref --sort=committerdate --format='%(refname:short)|%(committerdate:relative)|%(authorname)|%(subject)' refs/heads refs/remotes | head -n ${topn} | while IFS='|' read -r branch_name commit_date author subject; do
    # Adjust column widths - Branch: 60, Date: 20, Author: 25, Message: no truncation
    branch_display=$(printf "%-60.60s" "${branch_name}")
    date_display=$(printf "%-20.20s" "${commit_date}")
    author_display=$(printf "%-25.25s" "${author}")
    # Don't truncate the commit message, let it display fully

    printf "%-60s | %-20s | %-25s | %s\n" "${branch_display}" "${date_display}" "${author_display}" "${subject}"
  done
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
  local msg=${1:-"backup at $(date_now)"}

  # Check if there are any changes to commit
  if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    log info "Committing local changes"
    git_add "${msg}"
  else
    log info "No local changes to commit"
  fi

  # Pull with rebase to integrate remote changes
  log info "Pulling remote changes with rebase"
  if ! git_pull; then
    log error "Failed to pull and rebase remote changes"
    return ${RETURN_FAILURE:-1}
  fi

  # Push the changes
  log info "Pushing changes to remote"
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
  if ! git show --pretty="From %H %cd%nFrom: %an <%ae>%nDate: %ad%nSubject: [PATCH] Revert \"$(git log -1 --pretty=%s ${commit_id})\"%n%nThis reverts commit ${commit_id}.%n" --binary -R "${commit_id}" >"${revert_filename}"; then
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
          if [[ -n $file ]] && git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            if ! grep -q " $file\$" "$tmp_file"; then
              echo "$timestamp $file" >>"$tmp_file"
            fi
          fi
        done
    done

  # Sort by timestamp and output the results
  if [[ -f $tmp_file ]]; then
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
          if [[ -n $file ]] && git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            if ! grep -q " $file\$" "$tmp_file"; then
              echo "$timestamp $file" >>"$tmp_file"
            fi
          fi
        done
    done

  # Sort by timestamp and output the results
  if [[ -f $tmp_file ]]; then
    sort -r "$tmp_file" | head -n "$count"
    rm -f "$tmp_file"
  fi
}

function git_setup_ssh_repo() {
  local repo="${1}"
  local username=git
  local home="${GIT_STORAGE:-/home/${username}}"
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
    if [[ ${info} == *"*"* ]]; then
      echo "${repo}"
    fi
    safe_popd
  done
}

function git_info() {
  local git_info=""

  # Quick check if we're in a git repository
  if [ ! -d .git ] && [ ! -f .git/config ]; then
    echo ""
    return
  fi

  # Use git rev-parse to check if we're inside work tree (faster than other methods)
  if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo ""
    return
  fi

  # Get branch name (relatively fast)
  local git_branch=$(
    git symbolic-ref --short HEAD 2>/dev/null ||
      git describe --tags --exact-match 2>/dev/null ||
      git rev-parse --short HEAD 2>/dev/null ||
      echo "(detached)"
  )

  # Fast status check using git diff-index instead of git status --porcelain
  # This is much faster for large repositories (0.5s vs 2.4s)
  local has_changes=""

  # Check working tree changes (modified files) and staged changes (cached)
  if ! git diff-index --quiet HEAD -- 2>/dev/null || ! git diff-index --quiet --cached HEAD -- 2>/dev/null; then
    has_changes="*"
  fi

  # Format output with colors - use color variables if available, fallback to ANSI codes
  if [ -z "${has_changes}" ]; then
    if [ -n "${BOLD_GREEN}" ] && [ -n "${CLEAR}" ]; then
      git_info="[git: ${BOLD_GREEN}${git_branch}${CLEAR}]" # Use defined color variables
    else
      git_info="[git: \033[1;32m${git_branch}\033[0m]" # Fallback to ANSI codes
    fi
  else
    if [ -n "${BOLD_RED}" ] && [ -n "${CLEAR}" ]; then
      git_info="[git: ${BOLD_RED}${git_branch}*${CLEAR}]" # Use defined color variables
    else
      git_info="[git: \033[1;31m${git_branch}*\033[0m]" # Fallback to ANSI codes
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

function git_pull_repos() {
  local root=${1:-${PWD}}
  for repo_path in $(git_list_repos "${root}"); do
    safe_pushd "${repo_path}" || continue
    log info "Pulling updates in ${repo_path}"
    git pull || log warning "Failed to pull updates in ${repo_path}"
    safe_popd
  done
}

function git_ignored() {
  local root=${1:-${PWD}}
  local show_stats=${2:-false}
  local max_files=${3:-100}

  # Check if we're in a git repository
  if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    log error "Not in a git repository"
    return ${RETURN_FAILURE:-1}
  fi

  # Check if .gitignore exists
  if [ ! -f "${root}/.gitignore" ]; then
    log warning "No .gitignore file found in ${root}"
  fi

  log info "Listing files ignored by git in ${root}"

  # Use a temporary file to avoid "Argument list too long" error
  local temp_file=$(mktemp)

  # Use git ls-files to list ignored files and write to temp file
  # The -i flag shows ignored files
  # The --exclude-standard flag uses standard ignore rules (.gitignore, .git/info/exclude, etc.)
  # The -o flag shows untracked files (optional, to get all ignored files)
  git ls-files -i --exclude-standard --others 2>/dev/null | sort >"${temp_file}"

  if [ ! -s "${temp_file}" ]; then
    log notice "No ignored files found in the working directory"
    rm -f "${temp_file}"
    return ${RETURN_SUCCESS:-0}
  fi

  # Count total ignored files
  local total_count=$(wc -l <"${temp_file}" | tr -d ' ')

  # Display the results
  if [ "${show_stats}" = "true" ]; then
    log notice "Found ${total_count} ignored files (showing first ${max_files}):"
    echo
    printf "%-60s | %s\n" "File Path" "Size"
    printf "%-60s-|-%s\n" "$(printf '%0.s-' {1..60})" "$(printf '%0.s-' {1..10})"

    head -n "${max_files}" "${temp_file}" | while IFS= read -r file; do
      if [ -n "${file}" ]; then
        if [ -f "${file}" ]; then
          local file_size=$(du -h "${file}" 2>/dev/null | cut -f1)
          printf "%-60s | %s\n" "${file}" "${file_size:-0}"
        elif [ -d "${file}" ]; then
          local dir_size=$(du -sh "${file}" 2>/dev/null | cut -f1)
          printf "%-60s | %s (dir)\n" "${file}" "${dir_size:-0}"
        else
          printf "%-60s | %s\n" "${file}" "N/A"
        fi
      fi
    done

    if [ "${total_count}" -gt "${max_files}" ]; then
      echo
      log notice "... and $((total_count - max_files)) more files (use 'git_ignored . false <max_files>' to show more)"
    fi
  else
    log notice "Found ${total_count} ignored files (showing first ${max_files}):"
    head -n "${max_files}" "${temp_file}"

    if [ "${total_count}" -gt "${max_files}" ]; then
      echo
      log notice "... and $((total_count - max_files)) more files (use 'git_ignored . false <max_files>' to show more)"
    fi
  fi

  # Clean up temporary file
  rm -f "${temp_file}"

  return ${RETURN_SUCCESS:-0}
}

function git_confirm_dangerous_operation() {
  local operation_name=${1:-"dangerous git operation"}
  local force=${2:-false}
  local warning_lines=("${@:3}")

  if [ ${#warning_lines[@]} -eq 0 ]; then
    warning_lines=(
      "This operation will:"
      "  1. Remove ALL git history permanently"
      "  2. Force push to ALL remote repositories"
      "  3. Make the current state the new initial commit"
    )
  fi

  log warn "${operation_name}:"
  for line in "${warning_lines[@]}"; do
    echo "${line}"
  done
  echo ""
  log error "WARNING: This action cannot be undone!"
  echo ""

  if [ "${force}" = "true" ]; then
    log notice "Force mode enabled, skipping confirmation"
    return ${RETURN_SUCCESS:-0}
  fi

  read -p "Do you want to continue? Type 'YES' to confirm: " confirmation

  if [ "${confirmation}" != "YES" ]; then
    log notice "Operation cancelled by user"
    return ${RETURN_FAILURE:-1}
  fi

  return ${RETURN_SUCCESS:-0}
}

function git_backup_repository() {
  local repo_dir=${1:-$(pwd)}
  local backup_base_dir=${2:-""}
  local exclude_git=${3:-false}

  if [ ! -d "${repo_dir}" ]; then
    log error "Repository directory does not exist: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  if [ ! -d "${repo_dir}/.git" ]; then
    log error "Not a git repository: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  # Generate backup directory name
  local repo_name=$(basename "${repo_dir}")
  if [ -n "${backup_base_dir}" ]; then
    local backup_dir="${backup_base_dir}/${repo_name}_backup_$(date +%Y%m%d_%H%M%S)"
  else
    local backup_dir="${repo_dir}_backup_$(date +%Y%m%d_%H%M%S)"
  fi

  log info "Creating backup of repository: ${repo_dir}"

  # Create backup directory
  mkdir -p "${backup_dir}" || {
    log error "Failed to create backup directory: ${backup_dir}"
    return ${RETURN_FAILURE:-1}
  }

  # Use rsync to handle symlinks properly if available, otherwise use cp
  if have rsync; then
    if [ "${exclude_git}" = "true" ]; then
      rsync -av --exclude='.git' "${repo_dir}/" "${backup_dir}/"
    else
      rsync -av "${repo_dir}/" "${backup_dir}/"
    fi
  else
    # Fallback to cp if rsync is not available
    if [ "${exclude_git}" = "true" ]; then
      find "${repo_dir}" -type f -not -path "*/.git/*" -exec cp --parents {} "${backup_dir}/" \; 2>/dev/null || {
        log warn "Some files may not have been copied due to permissions"
      }
    else
      cp -r "${repo_dir}"/* "${backup_dir}/" 2>/dev/null || true
      cp -r "${repo_dir}/.git" "${backup_dir}/" 2>/dev/null || true
    fi
  fi

  log notice "Backup created at: ${backup_dir}"
  echo "${backup_dir}"
  return ${RETURN_SUCCESS:-0}
}

function git_repository_info() {
  local repo_dir=${1:-$(pwd)}
  local verbose=${2:-true}

  # Change to repository directory
  local original_dir=$(pwd)
  cd "${repo_dir}" 2>/dev/null || {
    log error "Directory does not exist: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  }

  # Check if we're in a git repository
  if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    log error "Not a git repository: ${repo_dir}"
    cd "${original_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  if [ "${verbose}" = "true" ]; then
    log info "Repository information for: ${repo_dir}"
  fi

  local current_branch=$(git branch --show-current 2>/dev/null || echo 'detached HEAD')
  local current_commit=$(git rev-parse HEAD 2>/dev/null || echo 'no commits')
  local repo_size=$(du -sh .git 2>/dev/null | cut -f1 || echo 'unknown')
  local total_commits=$(git rev-list --count HEAD 2>/dev/null || echo '0')
  local status=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

  if [ "${verbose}" = "true" ]; then
    echo "  Repository path: ${repo_dir}"
    echo "  Current branch: ${current_branch}"
    echo "  Current commit: ${current_commit}"
    echo "  Repository size: ${repo_size}"
    echo "  Total commits: ${total_commits}"
    echo "  Modified files: ${status}"

    log info "Remote repositories:"
    if git remote -v >/dev/null 2>&1; then
      git remote -v | sed 's/^/  /' || true
    else
      echo "  No remotes configured"
    fi
  else
    # Output in machine-readable format
    echo "path=${repo_dir}"
    echo "branch=${current_branch}"
    echo "commit=${current_commit}"
    echo "size=${repo_size}"
    echo "commits=${total_commits}"
    echo "modified=${status}"
  fi

  cd "${original_dir}"
  return ${RETURN_SUCCESS:-0}
}

function git_reset_history() {
  local repo_dir=${1:-$(pwd)}
  local commit_message=${2:-"Fresh start - removed all history $(date '+%Y-%m-%d %H:%M:%S')"}

  # Change to repository directory
  local original_dir=$(pwd)
  cd "${repo_dir}" 2>/dev/null || {
    log error "Directory does not exist: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  }

  # Check if we're in a git repository
  if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    log error "Not a git repository: ${repo_dir}"
    cd "${original_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  log info "Starting git history reset..."

  # Get current branch name
  local current_branch=$(git branch --show-current 2>/dev/null)
  if [ -z "${current_branch}" ]; then
    current_branch="main"
    log warn "No current branch detected, using 'main' as default"
  fi
  log info "Current branch: ${current_branch}"

  # Get list of all remotes
  local remotes=($(git remote 2>/dev/null || true))
  if [ ${#remotes[@]} -gt 0 ]; then
    log info "Found remotes: ${remotes[*]}"
  else
    log warn "No remote repositories found"
  fi

  # Stage all files
  log info "Staging all files..."
  git add -A

  # Check if there are any changes to commit
  if git diff --staged --quiet 2>/dev/null; then
    log info "No changes to commit, using current HEAD"
    # Get current commit message if it exists
    commit_message=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "Initial commit")
  else
    log info "Committing current changes..."
    git commit -m "${commit_message}" || {
      log error "Failed to commit current changes"
      cd "${original_dir}"
      return ${RETURN_FAILURE:-1}
    }
  fi

  # Create orphan branch
  local temp_branch="temp_fresh_start_$(date +%s)"
  log info "Creating orphan branch: ${temp_branch}"
  git checkout --orphan "${temp_branch}" || {
    log error "Failed to create orphan branch"
    cd "${original_dir}"
    return ${RETURN_FAILURE:-1}
  }

  # Add all files to the orphan branch
  log info "Adding all files to orphan branch..."
  git add -A

  # Create initial commit
  log info "Creating initial commit..."
  git commit -m "${commit_message}" || {
    log error "Failed to create initial commit"
    cd "${original_dir}"
    return ${RETURN_FAILURE:-1}
  }

  # Delete old branch if it exists
  if git show-ref --verify --quiet "refs/heads/${current_branch}"; then
    log info "Deleting old branch: ${current_branch}"
    git branch -D "${current_branch}" || {
      log warn "Failed to delete old branch: ${current_branch}"
    }
  fi

  # Rename orphan branch to original branch name
  log info "Renaming branch ${temp_branch} to ${current_branch}"
  git branch -m "${temp_branch}" "${current_branch}" || {
    log error "Failed to rename branch"
    cd "${original_dir}"
    return ${RETURN_FAILURE:-1}
  }

  # Force push to all remotes
  for remote in "${remotes[@]}"; do
    log info "Force pushing to remote: ${remote}"
    if ! git push --force "${remote}" "${current_branch}" 2>/dev/null; then
      log warn "Failed to push to remote: ${remote}"
    fi
  done

  # Clean up local repository
  log info "Cleaning up local repository..."
  git gc --aggressive --prune=now >/dev/null 2>&1 || {
    log warn "Git cleanup failed, but continuing..."
  }

  log notice "Git history reset completed!"
  cd "${original_dir}"
  return ${RETURN_SUCCESS:-0}
}

function git_show_cleanup_results() {
  local repo_dir=${1:-$(pwd)}
  local backup_dir=${2:-""}

  # Change to repository directory
  local original_dir=$(pwd)
  cd "${repo_dir}" 2>/dev/null || {
    log error "Directory does not exist: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  }

  log info "Final repository information:"
  echo "  Current branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"
  echo "  Current commit: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
  echo "  Repository size: $(du -sh .git 2>/dev/null | cut -f1 || echo 'unknown')"
  echo "  Total commits: $(git rev-list --count HEAD 2>/dev/null || echo '1')"

  log notice "Repository cleanup completed successfully!"
  if [ -n "${backup_dir}" ] && [ -d "${backup_dir}" ]; then
    log notice "Backup is available at: ${backup_dir}"
    log warn "You can remove the backup directory when you're satisfied with the results"
  fi

  cd "${original_dir}"
  return ${RETURN_SUCCESS:-0}
}

function git_clean_history() {
  local repo_dir=${1:-$(pwd)}
  local force=${2:-false}

  # Validate input parameters
  if [ ! -d "${repo_dir}" ]; then
    log error "Directory does not exist: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  # Check if we're in a git repository
  if [ ! -d "${repo_dir}/.git" ]; then
    log error "Not a git repository: ${repo_dir}"
    return ${RETURN_FAILURE:-1}
  fi

  # Check if git command is available
  if ! have git; then
    log error "Git command not found"
    return ${RETURN_FAILURE:-1}
  fi

  # Main execution flow
  log info "Starting Git History Cleanup for repository: ${repo_dir}"

  # Get initial repository info
  git_repository_info "${repo_dir}"

  # Confirm operation (unless force mode is enabled)
  if ! git_confirm_dangerous_operation "Git History Cleanup" "${force}"; then
    return ${RETURN_FAILURE:-1}
  fi

  # Create backup
  local backup_dir=$(git_backup_repository "${repo_dir}")
  if [ $? -ne 0 ]; then
    log error "Failed to create backup"
    return ${RETURN_FAILURE:-1}
  fi

  # Reset git history
  if ! git_reset_history "${repo_dir}"; then
    log error "Git history cleanup failed"
    return ${RETURN_FAILURE:-1}
  fi

  # Show final results
  git_show_cleanup_results "${repo_dir}" "${backup_dir}"

  return ${RETURN_SUCCESS:-0}
}
