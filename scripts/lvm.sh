function lvm_create() {
    local vg_name=${1}
    local lvm_size=${2}
    lvcreate -y -L ${lvm_size} -i 5 -I 4096 ${vg_name} -n "${vg_name}-test-${i}"
}

function lvm_remove() {
    local vg_name=${1:-adb-vg}
    for lv in $(ls /dev/${vg_name}/${vg_name}-test-*); do
        lvremove -y ${lv}
    done
}

function lvm_test_mkfs() {
    local vg_name=${1:-adb-vg}
    local fs_type=${2:-ext4}
    for lv in $(ls /dev/${vg_name}/${vg_name}-test-*); do
        trace_file=$(basename ${lv})-$(date '+%s')-${fs_type}.data
        case ${fs_type} in
        ext4)
            perf record -e 'raw_syscalls:*' -o ${trace_file} -- /usr/sbin/mkfs.${fs_type} -F -m0 -E stride=1,stripe-width=4 ${lv} &
            ;;
        xfs)
            perf record -e 'raw_syscalls:*' -o ${trace_file} -- /usr/sbin/mkfs.${fs_type} -f ${lv} &
            ;;
        esac
    done
    iostat -dmx 1 60 >${vg_name}-iostat-$(date '+%s').log &
    perf record -F 99 -a -g -o ${vg_name}-all-$(date '+%s').data -- sleep 60
    for trace_file in $(ls ${vg_name}-test-*.data); do
        report_file=${trace_file}.log
        perf trace -S -i ${trace_file} -o ${report_file}
    done
}
