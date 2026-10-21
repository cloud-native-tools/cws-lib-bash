#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/313_specify.sh"

# Container runtime: agent CLIs run as the image's develop account.
function is_container() {
  return 0
}
assert_eq "develop:develop" "$(specify_user)" "container should use develop"

CWS_DEVELOP_USER=custom
CWS_DEVELOP_GROUP=customgrp
assert_eq "custom:customgrp" "$(specify_user)" "container should honor CWS_DEVELOP_* overrides"
unset CWS_DEVELOP_USER CWS_DEVELOP_GROUP

# Docker host (physical or VM): agent CLIs run as the host operator account.
function is_container() {
  return 1
}
assert_eq "agent:agent" "$(specify_user)" "docker host should use agent"

print_summary
