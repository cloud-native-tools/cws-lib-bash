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
  for gf in $(find . -name .git); do
    pushd "${gf%/.git}" >/dev/null 2>&1
    log info "update in $(pwd)"
    git pull --all
    popd >/dev/null 2>&1
  done
}

function git_top_branch() {
  git branch -a --sort=-committerdate | head -n 20
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
    fi
  done
}

function git_update_submodule() {
  git submodule update --init --recursive --remote
}

function git_sync_ignore() {
  git ls-files -ci --exclude-standard | xargs git rm --cached
}

function git_clean() {
  git clean -dfX
  find . -type d -empty | grep -v .git | xargs rm -rfv
}

function git_tag() {
  git log --tags --simplify-by-decoration --pretty="format:%ci %d"
}

function git_list_url() {
  local root=${1:-.}
  for git_dir in $(find ${root} -name '.git' -type d); do
    grep -w 'url' ${git_dir}/config | cut -d' ' -f 3
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

function git_https_url() {
  local root=${1:-.}
  git_list_url ${root} | sed -E "s~${GIT_URL_PATTERN}~https://\2/\4/\5\6~g"
}

function git_clone_into() {
  local dir=${1:-${PWD}}
  if [ $# -gt 0 ]; then shift; fi
  git -C ${dir} clone --progress --recurse-submodules -j$(nproc) $@
}

function git_tag_to_commit() {
  local url=${1}
  local tag=${2}
  if [ -n "${tag}" ] && [ -n "${url}" ]; then
    git ls-remote --tags ${url} | grep -w ${tag} | cut -f1
  fi
}
