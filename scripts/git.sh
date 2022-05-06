function git_track_lfs() {
  local file_size=$1
  find . -type f -size +${file_size} | grep -v /.git/ | grep -v /target/ | xargs git lfs track
}

function git_checkout_by_date() {
  local git_url=$1
  local git_dir=$2
  local begin=${3:-$(date '+%Y-%m-%d' --date="- 7 days")}
  local end=${4:-$(date '+%Y-%m-%d')}
  local step=${5:-"1days"}

  git clone "${git_url}" "${git_dir}"
  pushd "${git_dir}" > /dev/null 2>&1
  commit_log=commit.log

  git log --pretty="%cd_%h" --date="short" --after="${begin}" >${commit_log}
  iter=$(date '+%Y-%m-%d' -d "${begin}")
  while [[ true ]]; do
    if [[ $(date '+%s' -d ${iter}) -gt $(date '+%s' -d ${end}) ]]; then break; fi
    commit=$(grep ${iter} ${commit_log} | tail -n1)
    if [[ -n "${commit}" ]]; then
      echo "commit: ${commit#*_} at ${commit%_*}"
    fi
    iter=$(date '+%Y-%m-%d' -d "${iter}+${step}")
  done
  popd || exit
}

function git_update_all() {
  for gf in $(find . -name .git); do
    pushd "${gf%/.git}" >/dev/null 2>&1
    echo "update in $(pwd)"
    git pull --all
    popd >/dev/null 2>&1
  done
}

function git_top_branch() {
  git branch -a --sort=-committerdate | head -n 20
}

function git_push_all(){
  local branch=${1:-main}
  for remote in $(git remote)
  do
    echo "=======    Remote ${remote}    ======="
    git push ${remote} ${branch}
  done
}