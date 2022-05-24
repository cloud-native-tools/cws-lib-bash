#!/bin/bash

function huge_pg() {
    FORMAT="%-10s\t%-20s\t%-20s\n"

    PID=$1

    m0=$(sudo numastat -p ${PID} | grep ^Total |
        awk -F' ' '{printf "%.2f", $2/1024}')
    m1=$(sudo numastat -p ${PID} | grep ^Total |
        awk -F' ' '{printf "%.2f", $3/1024}')

    anon_thp=$(sudo grep AnonHugePages /proc/${PID}/smaps |
        awk 'BEGIN {Total=0} { if($2>4) Total+=$2} END {printf "%.2f", Total/1024/1024}')
    shmem_thp=$(sudo grep ShmemPmdMapped /proc/${PID}/smaps |
        awk 'BEGIN {Total=0} { if($2>4) Total+=$2} END {printf "%.2f", Total/1024/1024}')
    largepages=$(sudo cat $(sudo find /sys/kernel/debug/kvm/ \
        -name "${PID}-*")/largepages | awk '{printf "%.2f", $1/512}')

    printf $FORMAT mem node0 ${m0}
    printf $FORMAT mem node1 ${m1}
    printf $FORMAT thp anon_thp ${anon_thp}
    printf $FORMAT thp shmem_thp ${shmem_thp}
    printf $FORMAT thp largepages ${largepages}
}
