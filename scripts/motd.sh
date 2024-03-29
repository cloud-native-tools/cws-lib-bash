#!/bin/bash

#Color variables
C='\033[0m'
R='\033[0;31m'
G='\033[0;32m'
Y='\033[0;33m'
B='\033[0;34m'
P='\033[0;35m'
W='\033[0;37m'
X='\033[0m'

function motd_generate() {
  # from https://gist.github.com/nyanshell/0f598d39f0c31a44c336
  if [ -f "/etc/os-release" ]; then
    source /etc/os-release
  fi
  motd="/etc/motd"
  HOSTNAME=$(uname -n)
  KERNEL=$(uname -r)
  CPU=$(awk -F '[ :][ :]+' '/^model name/ { print $2; exit; }' /proc/cpuinfo)
  ARCH=$(uname -m)
  IP=$(hostname -i)
  NET=$(ifconfig | grep -E 'bond|eth' -A1 | grep inet -w | awk '{print $2}' | tr '\n' ',')
  CMDLINE=$(cat /proc/cmdline)

  #Clear screen before motd
  clear >$motd

  log color "$Y
    _     _  _  _             _
   / \   | |(_)| |__    __ _ | |__    __ _
  / _ \  | || || '_ \  / _\` || '_ \  / _\` |
 / ___ \ | || || |_) || (_| || |_) || (_| |
/_/   \_\|_||_||_.__/  \__,_||_.__/  \__,_|
$C" >>$motd
  log color "$R===============================================================" >>$motd
  log color "       $R Welcome to $Y $HOSTNAME $IP [$NET]                     " >>$motd
  log color "       $R CPU      $W= $CPU                                      " >>$motd
  log color "       $R ARCH     $W= $ARCH                                     " >>$motd
  log color "       $R HOSTNAME $W= $HOSTNAME                                 " >>$motd
  log color "       $R OS       $W= $PRETTY_NAME                              " >>$motd
  log color "       $R KERNEL   $W= $KERNEL                                   " >>$motd
  log color "       $R CMDLINE  $W= $CMDLINE                                  " >>$motd
  log color "$R===============================================================" >>$motd
  log color "$X" >>$motd
}

function motd() {
  cat /etc/motd
}
