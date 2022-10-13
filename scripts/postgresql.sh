function pgbeanch_test() {
    local sql_file=${1:-/tmp/test.sql}
    local username=${2:-adbpgadmin}
    local database=${3:-adbpgadmin}
    pgbench -n -f ${sql_file} -c 10 -j 2 -t 10000 --username=${username} ${database}
}
