#!/bin/bash

# Deprecated filename alias: 313_specify.sh -> 313_ai_engine.sh (spec-kit ->
# ai-engine brand rename). Kept so downstream main-pinned / raw-URL fetches of
# the old path keep working during the transition; this file only forwards.
# Function-level deprecated aliases (specify_install / specify_ensure) live in
# 313_ai_engine.sh. Removed once every client project has migrated.
# shellcheck source=/dev/null
source "$(dirname "${BASH_SOURCE[0]}")/313_ai_engine.sh"