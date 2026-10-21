# Prompt (提示符) —— 探测结果只从 02_probe.sh 取，本文件不重复实现探测逻辑

# 当前 conda/mamba 活动环境标记（优先 mamba），无环境或工具缺失时输出空串
function bash_prompt_conda_env() {
  local env_name=""
  if has_mamba; then
    env_name=$(mamba info --envs 2>/dev/null | awk '$2=="*"{print "[mamba",$1"]"}')
  elif has_conda; then
    env_name=$(conda info --envs 2>/dev/null | awk '$2=="*"{print "[conda",$1"]"}')
  fi

  if [ -n "${env_name}" ]; then
    echo "${BOLD_CYAN}${env_name}${CLEAR}"
  fi
}

function bash_prompt() {
  # 注意：必须先取 $?，任何命令（含 local 声明）都会覆盖它
  local exit_code=${?}
  local last_exit
  if [[ ${exit_code} != "0" ]]; then
    last_exit=$(log plain ${SYMBOL_FAILURE})
  else
    last_exit=$(log plain ${SYMBOL_SUCCESS})
  fi

  local user_indicator='$'
  if is_root; then
    user_indicator="#"
  fi

  # 形如 [amd64][linux: none|docker|kvm]
  local env_info="[${BASH_ARCH}][${BASH_OS}: $(virt_type)]"
  local conda_env=$(bash_prompt_conda_env)

  log plain "[${last_exit}]${env_info}${conda_env}[\D{%Y-%m-%d} \t][\u@\h \w]$(git_info)${user_indicator}\n "
}

is_bash && enable -n echo
is_bash && PROMPT_COMMAND='PS1=$(bash_prompt)'

function precmd() {
  if [[ $? != "0" ]]; then
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
