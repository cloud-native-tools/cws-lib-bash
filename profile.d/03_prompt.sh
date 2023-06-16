function bash_prompt() {
  if [[ "$?" != "0" ]]; then
    log plain "[$(log plain ${SYMBOL_FAILURE})][\D{%Y-%m-%d} \t][\u@\h \w]\$\n "
  else
    log plain "[$(log plain ${SYMBOL_SUCCESS})][\D{%Y-%m-%d} \t][\u@\h \w]\$\n "
  fi
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

  printf '\0337\033[r\033[999;999H\033[6n\0338' > /dev/tty
  IFS='[;R' read -r _ rows cols _ < /dev/tty

  stty "$old"

  # echo "cols:$cols"
  # echo "rows:$rows"
  stty cols "$cols" rows "$rows"
}