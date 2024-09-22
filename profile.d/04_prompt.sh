function bash_prompt() {
  if [[ "$?" != "0" ]]; then
    local last_exit=$(log plain ${SYMBOL_FAILURE})
  else
    local last_exit=$(log plain ${SYMBOL_SUCCESS})
  fi

  if [ $(id -u) = 0 ]; then
    local user_indicator="#"
  else
    local user_indicator="\$"
  fi

  if command -v mamba &>/dev/null; then
    local conda_env="${BOLD_CYAN}$(mamba info --envs | awk '$2=="*"{print "[mamba",$1"]"}')${CLEAR}"
  elif command -v conda &>/dev/null; then
    local conda_env="${BOLD_CYAN}$(conda info --envs | awk '$2=="*"{print "[conda",$1"]"}')${CLEAR}"
  else
    local conda_env=""
  fi

  if command -v systemd-detect-virt &>/dev/null; then
    local BASH_OS=$(systemd-detect-virt 2>/dev/null || echo "${BASH_OS}")
  fi
  local env_info="[${BASH_ARCH}][${BASH_OS}]"

  if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null; then
    local git_branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "(detached)")
    local git_status=$(git status --porcelain 2>/dev/null)
    if [ -z "${git_status}" ]; then
      local git_info="[git: ${BOLD_GREEN}${git_branch}${CLEAR}]"
    else
      local git_info="[git: ${BOLD_RED}${git_branch}*${CLEAR}]"
    fi
  else
    local git_info=""
  fi

  log plain "[${last_exit}]${env_info}${conda_env}[\D{%Y-%m-%d} \t][\u@\h \w]${git_info}${user_indicator}\n "
}

is_bash && enable -n echo
is_bash && PROMPT_COMMAND='PS1=$(bash_prompt)'

function precmd() {
  if [[ "$?" != "0" ]]; then
    export PROMPT="[$(log plain ${SYMBOL_FAILURE})][%D{%Y-%m-%d} %T][%n@%M %d]\$"$'\n'
  else
    export PROMPT="[$(log plain ${SYMBOL_SUCCESS})][%D{%Y-%m-%d} %T][%n@%M %d]\$"$'\n'
  fi
}

function resize() {
  old=$(stty -g)
  stty raw -echo min 0 time 5

  printf '\0337\033[r\033[999;999H\033[6n\0338' >/dev/tty
  IFS='[;R' read -r _ rows cols _ </dev/tty

  stty "$old"

  # echo "cols:$cols"
  # echo "rows:$rows"
  stty cols "$cols" rows "$rows"
}
