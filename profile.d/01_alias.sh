alias wgetc='wget --no-check-certificate -c '
alias lh='ls -lhStA --time-style="+${DATE_TIME_FORMAT}"'
alias now='date "+${DATE_TIME_FORMAT}"'
alias watch="watch -d -n1"
alias du1="du -ach -d1 -x|sort -h"
alias du2="du -ach -d2 -x|sort -h"
alias ..="cd .."
alias ...="cd ../.."
alias find_name="find . -name "
alias df="df -Th"
alias free="free -mwh"
alias psl="ps auxf"
alias psearch="ps aux | grep -v grep | grep -i -e VSZ -e"

[ -n "${BASH_VERSION}" ] && alias sh="bash"
[ -n "${ZSH_VERSION}" ] && alias sh="zsh"
