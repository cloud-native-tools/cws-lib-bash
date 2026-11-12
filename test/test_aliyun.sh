#!/usr/bin/env bash

# Test script for the ECS instance RAM role metadata functions (scripts/250_aliyun.sh)
# The metadata service is mocked by overriding the curl wrappers, so no request
# ever reaches 100.100.100.200.

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_env"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"

work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT

curl_log="${work}/curl.log"
export ECS_META_URL="http://metadata.test/latest"

mock_token="mock-imds-token"
mock_roles="EcsRamRole"
mock_credentials='{"AccessKeyId":"STS.mock","AccessKeySecret":"mock-secret","Expiration":"2026-11-12T01:02:03Z","SecurityToken":"mock-security-token","LastUpdated":"2026-11-12T00:00:00Z","Code":"Success"}'
mock_status="200"

function curl_fetch() {
  printf 'fetch %s\n' "$*" >>"${curl_log}"
  local url=""
  local wants_status="false"
  local arg
  for arg in "$@"; do
    case "${arg}" in
      http://* | https://*) url="${arg}" ;;
      *http_code*) wants_status="true" ;;
    esac
  done
  if [ "${wants_status}" = "true" ]; then
    printf '%s' "${mock_status}"
    return 0
  fi
  case "${url}" in
    */api/token) printf '%s' "${mock_token}" ;;
    *security-credentials/) printf '%s\n' "${mock_roles}" ;;
    *security-credentials/*) printf '%s' "${mock_credentials}" ;;
  esac
}

# --- ecs_metadata_token: IMDSv2 token request and TTL validation ---
output=$(ecs_metadata_token)
assert_eq "${mock_token}" "${output}" "ecs_metadata_token should return the IMDSv2 token"
assert_contains "$(cat "${curl_log}")" "-X PUT" "ecs_metadata_token should use the PUT method"
assert_contains "$(cat "${curl_log}")" "X-aliyun-ecs-metadata-token-ttl-seconds: 21600" "ecs_metadata_token should default the TTL to 21600 seconds"

ecs_metadata_token 60 >/dev/null
assert_contains "$(tail -n 1 "${curl_log}")" "X-aliyun-ecs-metadata-token-ttl-seconds: 60" "ecs_metadata_token should honor a custom TTL"

output=$(ecs_metadata_token 21601 2>&1)
assert_eq "1" "$?" "ecs_metadata_token should reject a TTL above 21600 seconds"
assert_contains "${output}" "between 1 and 21600" "the TTL error should state the valid range"

output=$(ecs_metadata_token abc 2>&1)
assert_eq "1" "$?" "ecs_metadata_token should reject a non-numeric TTL"

# --- ecs_ram_roles / ecs_ram_role_name ---
assert_eq "${mock_roles}" "$(ecs_ram_roles)" "ecs_ram_roles should list the granted role names"

ecs_ram_roles "${mock_token}" >/dev/null
assert_contains "$(tail -n 1 "${curl_log}")" "X-aliyun-ecs-metadata-token: ${mock_token}" "ecs_ram_roles should forward the IMDSv2 token"

mock_roles=$'EcsRamRole\nSecondRole'
assert_eq "EcsRamRole" "$(ecs_ram_role_name)" "ecs_ram_role_name should return the first role name"
mock_roles="EcsRamRole"

# --- ecs_ram_role_exists ---
ecs_ram_role_exists
assert_success "ecs_ram_role_exists should succeed when the metadata service answers 200"

mock_status="404"
ecs_ram_role_exists
assert_fail "ecs_ram_role_exists should fail when no role is granted"
mock_status="200"

# --- ecs_ram_credentials ---
assert_eq "${mock_credentials}" "$(ecs_ram_credentials)" "ecs_ram_credentials should resolve the granted role automatically"
assert_eq "${mock_credentials}" "$(ecs_ram_credentials EcsRamRole)" "ecs_ram_credentials should accept an explicit role name"

mock_roles=""
ecs_ram_credentials >/dev/null 2>&1
assert_fail "ecs_ram_credentials should fail when no role is granted"
mock_roles="EcsRamRole"

# --- ecs_ram_field / ecs_ram_env (require jq) ---
if has_cmd jq; then
  assert_eq "STS.mock" "$(ecs_ram_field AccessKeyId)" "ecs_ram_field should extract AccessKeyId"
  assert_eq "2026-11-12T01:02:03Z" "$(ecs_ram_field Expiration)" "ecs_ram_field should extract Expiration"

  output=$(ecs_ram_field Arn 2>&1)
  assert_eq "1" "$?" "ecs_ram_field should reject an unknown field"
  assert_contains "${output}" "Unsupported field" "the field error should name the unsupported field"

  env_output=$(ecs_ram_env)
  assert_contains "${env_output}" 'export ALIBABA_CLOUD_ACCESS_KEY_ID="STS.mock"' "ecs_ram_env should export the AK for Alibaba Cloud SDKs"
  assert_contains "${env_output}" 'export ALIBABA_CLOUD_SECURITY_TOKEN="mock-security-token"' "ecs_ram_env should export the STS token"
  assert_contains "${env_output}" 'export ALICLOUD_ACCESS_KEY="STS.mock"' "ecs_ram_env should export the AK for the aliyun CLI"
  assert_contains "${env_output}" 'export ALICLOUD_SECURITY_TOKEN="mock-security-token"' "ecs_ram_env should export the STS token for the aliyun CLI"
  assert_contains "${env_output}" "expires at 2026-11-12T01:02:03Z" "ecs_ram_env should announce the expiration"

  # The emitted statements must be valid shell that an eval can apply
  (
    eval "${env_output}"
    [ "${ALIBABA_CLOUD_ACCESS_KEY_ID}" = "STS.mock" ] && [ "${ALICLOUD_SECURITY_TOKEN}" = "mock-security-token" ]
  )
  assert_success "ecs_ram_env output should be eval-able"
else
  log_warn "jq not found, skipping ecs_ram_field and ecs_ram_env assertions"
fi

print_summary
