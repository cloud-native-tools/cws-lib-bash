#!/bin/bash


function motd_generate() {
  # from https://gist.github.com/nyanshell/0f598d39f0c31a44c336
  motd="/etc/motd"
  HOSTNAME=$(uname -n)
  KERNEL=$(uname -r)
  CPU=$(awk -F '[ :][ :]+' '/^model name/ { print $2; exit; }' /proc/cpuinfo)
  ARCH=$(uname -m)
  IP=$(hostname -i)
  DISC=$(df -h | awk '$NF=="/"{print $5 }')
  NET=$(ifconfig|grep -E 'bond|eth' -A1|grep inet|awk '{print $2}'|tr '\n' ',')
  MEMORY_USED=$(free -t -m | grep "Total:" | awk '{print $3}')
  MEMORY_TOTAL=$(free -t -m | grep "Total:" | awk '{print $2}')
  MEMORY_SWAP=$(free -m | tail -n 1 | awk '{print $3}')
  PSA=$(ps -Afl | wc -l)
  PSU=$(ps U $USER h | wc -l)
  CMDLINE=$(cat /proc/cmdline)

  #Time of day
  HOUR=$(date +"%H")
  if [ $HOUR -lt 12 -a $HOUR -ge 0 ]; then
    TIME="morning"
  elif [ $HOUR -lt 17 -a $HOUR -ge 12 ]; then
    TIME="afternoon"
  else
    TIME="evening"
  fi

  #System uptime
  uptime=$(cat /proc/uptime | cut -f1 -d.)
  upDays=$((uptime / 60 / 60 / 24))
  upHours=$((uptime / 60 / 60 % 24))
  upMins=$((uptime / 60 % 60))
  upSecs=$((uptime % 60))

  #System load
  LOAD1=$(cat /proc/loadavg | awk {'print $1'})
  LOAD5=$(cat /proc/loadavg | awk {'print $2'})
  LOAD15=$(cat /proc/loadavg | awk {'print $3'})

  #Color variables
  C='\033[0m'
  R='\033[0;31m'
  G='\033[0;32m'
  Y='\033[0;33m'
  B='\033[0;34m'
  P='\033[0;35m'
  W='\033[0;37m'
  X='\033[0m'


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
  echo -e "       $R KERNEL   $W= $KERNEL                                   " >>$motd
  echo -e "       $R CMDLINE  $W= $CMDLINE                                  " >>$motd
  echo -e "       $R HOSTNAME $W= $HOSTNAME                                 " >>$motd
  echo -e "       $R ARCH     $W= $ARCH                                     " >>$motd
  echo -e "       $R USERS    $W= Currently $(users | wc -w) users logged on" >>$motd
  echo -e "$R===============================================================" >>$motd
  echo -e "       $R CPU Usage       $W= $LOAD1 1 min $LOAD5 5 min $LOAD15 15 min " >>$motd
  echo -e "       $R Memory Used     $W= $MEMORY_USED MB / $MEMORY_TOTAL MB       " >>$motd
  echo -e "       $R Swap in use     $W= $MEMORY_SWAP MB                          " >>$motd
  echo -e "       $R Processes       $W= You are running $PSU of $PSA processes   " >>$motd
  echo -e "       $R System Uptime   $W= $upDays days $upHours hours $upMins minutes $upSecs seconds " >>$motd
  echo -e "       $R Disk Space Used $W= $DISC                              " >>$motd
  echo -e "$R===============================================================" >>$motd
  echo -e "$X" >>$motd
}

function motd() {
  cat /etc/motd
}

if touch /etc/motd 2>/dev/null
then
  motd_generate
fi
