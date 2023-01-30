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

  echo -e "$Y
    _     _  _  _             _
   / \   | |(_)| |__    __ _ | |__    __ _
  / _ \  | || || '_ \  / _\` || '_ \  / _\` |
 / ___ \ | || || |_) || (_| || |_) || (_| |
/_/   \_\|_||_||_.__/  \__,_||_.__/  \__,_|
$C" >>$motd
  echo -e "$R===============================================================" >>$motd
  echo -e "       $R Welcome to $Y $HOSTNAME $IP [$NET]                     " >>$motd
  echo -e "       $R CPU      $W= $CPU                                      " >>$motd
  echo -e "       $R ARCH     $W= $ARCH                                     " >>$motd
  echo -e "       $R HOSTNAME $W= $HOSTNAME                                 " >>$motd
  echo -e "       $R OS       $W= $PRETTY_NAME                              " >>$motd
  echo -e "       $R KERNEL   $W= $KERNEL                                   " >>$motd
  echo -e "       $R CMDLINE  $W= $CMDLINE                                  " >>$motd
  echo -e "$R===============================================================" >>$motd
  echo -e "$X" >>$motd
}

function motd() {
  cat /etc/motd
}
