GIT_URL_PATTERN='^(https://|http://|git@|git://)([^/:]+)(/|:)([^/]+)/([^.]+)(.git)?'

function git_track_lfs() {
  local file_size=${1:-"+1M"}
  log info "using git lfs track file large than ${file_size}"
  find . -type f -size "${file_size}" | grep -v /.git/ | xargs git lfs track
}

function git_checkout_by_date() {
  local git_url=$1
  local git_dir=$2
  local begin=${3:-$(date '+%Y-%m-%d' --date="- 7 days")}
  local end=${4:-$(date '+%Y-%m-%d')}
  local step=${5:-"1days"}

  git clone "${git_url}" "${git_dir}"
  pushd "${git_dir}" >/dev/null 2>&1
  commit_log=commit.log

  git log --pretty="%cd_%h" --date="short" --after="${begin}" >${commit_log}
  iter=$(date '+%Y-%m-%d' -d "${begin}")
  while [[ true ]]; do
    if [[ $(date '+%s' -d ${iter}) -gt $(date '+%s' -d ${end}) ]]; then break; fi
    commit=$(grep ${iter} ${commit_log} | tail -n1)
    if [[ -n "${commit}" ]]; then
      log info "commit: ${commit#*_} at ${commit%_*}"
    fi
    iter=$(date '+%Y-%m-%d' -d "${iter}+${step}")
  done
  popd || exit
}

function git_update_all() {
  for git_dir in $(git_list_repos); do
    pushd "${git_dir}" >/dev/null 2>&1
    log info "update in $(pwd)"
    git pull --all
    popd >/dev/null 2>&1
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
  git ls-files -ci --exclude-standard | xargs git rm --cached
}

function git_clean() {
  git clean -d -x -f
  find . -type d -empty | grep -v .git | xargs rm -rfv
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
    return ${RETURN_FAILURE}
  fi
  shift
  git clone --progress -j$(nproc) ${url} $@
}

function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE}
  fi

  if [ ! -d "${dir}" ]; then
    mkdir -p ${dir}
  fi
  shift 2
  git -C ${dir} clone --progress -j$(nproc) --recurse-submodules ${url} $@
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
    pushd $(dirname ${head}) >/dev/null 2>&1
    git remote prune origin
    git remote update
    popd >/dev/null 2>&1
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

function git_copy_workdir() {
  local dest_dir=${1}
  local commit_id=${2:-HEAD}
  if [ -z "${dest_dir}" ]; then
    log error "Usage: git_install <dest_dir>"
    return ${RETURN_FAILURE}
  fi
  if [ ! -d "${dest_dir}" ]; then
    mkdir -p ${dest_dir}
  fi
  git archive --format=tar --output=/dev/stdout ${commit_id} | tar xf - -C ${dest_dir}
}

function git_pull() {
  git pull --rebase
}

function git_pull_all() {
  git pull --all --rebase
}

function git_push() {
  local remote=$(git config --get branch.$(git rev-parse --abbrev-ref HEAD).remote)
  local branch=$(git branch | awk '{print $NF}')
  log notice "git push ${branch} to ${remote}"
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
    if [ "${remote}" != "origin" ]; then
      log info "===================   Local:[${branch}], Remote:[${remote}/${branch}]    ==================="
      git push $@ ${remote} ${branch}
      git push ${remote} --tags
    fi
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
