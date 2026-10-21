#!/bin/bash

# Source the environment
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
source "${project_root}/bin/cws_bash_env"

# Test counters
total_tests=0
passed_tests=0
failed_tests=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function log_test_result() {
    local passed="$1"
    local desc="$2"
    if [ "$passed" == "true" ]; then
        echo -e "${GREEN}[PASS]${NC} $desc"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}[FAIL]${NC} $desc"
        failed_tests=$((failed_tests + 1))
    fi
    total_tests=$((total_tests + 1))
}

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

echo "Running tests for jq_prettier..."

# --- Success paths ---

# 1. Sorts each entry's object keys alphabetically
cat > "${tmp_dir}/keys.json" <<'EOF'
[{"b": 1, "a": 2, "c": 3}]
EOF
actual=$(jq_prettier "${tmp_dir}/keys.json" | jq -r '.[0] | keys_unsorted | join(",")')
if [ "${actual}" == "a,b,c" ]; then
    log_test_result "true" "sorts entry object keys alphabetically"
else
    log_test_result "false" "sorts entry object keys alphabetically. Expected 'a,b,c', Got: '${actual}'"
fi

# 2. Deduplicates entries by key
cat > "${tmp_dir}/dup.json" <<'EOF'
[{"region_id": "cn-hangzhou", "v": 1}, {"region_id": "cn-hangzhou", "v": 2}, {"region_id": "cn-beijing", "v": 3}]
EOF
actual=$(jq_prettier "${tmp_dir}/dup.json" "region_id" "region_id" | jq -r 'length')
if [ "${actual}" == "2" ]; then
    log_test_result "true" "deduplicates entries by key"
else
    log_test_result "false" "deduplicates entries by key. Expected length 2, Got: '${actual}'"
fi

# 3. Sorts entries by key
cat > "${tmp_dir}/sort.json" <<'EOF'
[{"region_id": "cn-beijing"}, {"region_id": "cn-hangzhou"}, {"region_id": "ap-northeast-1"}]
EOF
actual=$(jq_prettier "${tmp_dir}/sort.json" "" "region_id" | jq -r '.[0].region_id')
if [ "${actual}" == "ap-northeast-1" ]; then
    log_test_result "true" "sorts entries by key"
else
    log_test_result "false" "sorts entries by key. Expected first entry 'ap-northeast-1', Got: '${actual}'"
fi

# 4. Combined behavior of the original process_json.sh: key sort + dedupe + entry sort
cat > "${tmp_dir}/combined.json" <<'EOF'
[
  {"region_id": "cn-hangzhou", "zz": 1, "aa": 2},
  {"region_id": "cn-beijing", "b_key": 1, "a_key": 2},
  {"region_id": "cn-hangzhou", "dup": true}
]
EOF
output=$(jq_prettier "${tmp_dir}/combined.json" "region_id" "region_id")
actual_len=$(echo "${output}" | jq -r 'length')
actual_first=$(echo "${output}" | jq -r '.[0].region_id')
actual_keys=$(echo "${output}" | jq -r '.[1] | keys_unsorted | join(",")')
if [ "${actual_len}" == "2" ] && [ "${actual_first}" == "cn-beijing" ] && [ "${actual_keys}" == "aa,region_id,zz" ]; then
    log_test_result "true" "combined: dedupe + entry sort + key sort"
else
    log_test_result "false" "combined: dedupe + entry sort + key sort. Expected len=2 first=cn-beijing keys=aa,region_id,zz, Got: len=${actual_len} first=${actual_first} keys=${actual_keys}"
fi

# 5. Without optional keys: keeps all entries (only key sorting applied)
cat > "${tmp_dir}/plain.json" <<'EOF'
[{"x": 1}, {"y": 2}]
EOF
actual=$(jq_prettier "${tmp_dir}/plain.json" | jq -r 'length')
if [ "${actual}" == "2" ]; then
    log_test_result "true" "no optional keys keeps all entries"
else
    log_test_result "false" "no optional keys keeps all entries. Expected length 2, Got: '${actual}'"
fi

# --- Error paths ---

# 6. Missing argument fails
if ! jq_prettier > /dev/null 2>&1; then
    log_test_result "true" "missing argument returns failure"
else
    log_test_result "false" "missing argument should return failure"
fi

# 7. Non-existent file fails
if ! jq_prettier "${tmp_dir}/no_such_file.json" > /dev/null 2>&1; then
    log_test_result "true" "non-existent file returns failure"
else
    log_test_result "false" "non-existent file should return failure"
fi

# 8. Non-array input fails
echo '{"not": "array"}' > "${tmp_dir}/object.json"
if ! jq_prettier "${tmp_dir}/object.json" > /dev/null 2>&1; then
    log_test_result "true" "non-array input returns failure"
else
    log_test_result "false" "non-array input should return failure"
fi

# 9. Invalid JSON fails
echo "not json at all" > "${tmp_dir}/invalid.json"
if ! jq_prettier "${tmp_dir}/invalid.json" > /dev/null 2>&1; then
    log_test_result "true" "invalid JSON returns failure"
else
    log_test_result "false" "invalid JSON should return failure"
fi

echo "------------------------------------------------"
echo "Tests completed: $passed_tests/$total_tests passed."

if [ "$failed_tests" -eq 0 ]; then
    exit 0
else
    exit 1
fi
