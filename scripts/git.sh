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

  repo=${repo#/}
  repo=${repo%.git}.git

  # Validate source authorization file
  if [ ! -f "${auth_keys_src}" ]; then
    log error "Source SSH authorized_keys missing: ${auth_keys_src}"
    return ${RETURN_FAILURE:-1}
  fi

  # User management with validation
  if getent passwd "${username}" >/dev/null 2>&1; then
    log info "User exists: '${username}'"
  else
    log info "Creating user: '${username}' with home: ${home}"
    if ! useradd -m -U "${username}" -d "${home}" -s /usr/bin/git-shell; then
      log error "User creation failed: ${username}"
      return ${RETURN_FAILURE:-1}
    fi
    # Ensure home directory ownership
    [ -d "${home}" ] && chown "${username}:${username}" "${home}"
  fi

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

  cd "${home}" || return ${RETURN_FAILURE:-1}
  if ! git init --bare "${repo}"; then
    log error "Git repository initialization failed: ${repo}"
    return ${RETURN_FAILURE:-1}
  fi
  # Permission hardening
  if ! chown -R "${username}:${username}" "${home}"; then
    log error "Ownership change failed: ${home}"
    return ${RETURN_FAILURE:-1}
  fi
  chmod 700 "${ssh_dir}" || return ${RETURN_FAILURE:-1}
  chmod 600 "${auth_keys_dst}" || return ${RETURN_FAILURE:-1}

  log notice "Git remote setup complete at [${repo}]. Add with: git remote add <remote_name> git@<ssh_name>:${repo}"
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
