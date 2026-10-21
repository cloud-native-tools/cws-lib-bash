#!/usr/bin/env bash
# record-bump.sh — append/annotate a submodule pointer-bump row in the parent's ledger.
#
# Usage:
#   record-bump.sh <submodule-path>              # append a new bump row (Validation=pending)
#   record-bump.sh --status <pass|fail> <path>   # set Validation on the most recent row for <path>
#
# Rules encoded (see SKILL.md):
#   - old SHA  = the submodule commit currently recorded in the parent tree (the gitlink at HEAD)
#   - new SHA  = the submodule's working HEAD (what `git add <path>` will/did stage)
#   - branch   = the submodule's current branch (must NOT be detached)
# Run from the parent repo root.
set -euo pipefail

SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"

LEDGER="${SKILL_WORKDIR}/submodule-edits.md"
TEMPLATE="${SKILL_HOME}/assets/ledger-template.md"

STATUS=""
if [ "${1:-}" = "--status" ]; then
  STATUS="${2:-}"
  case "$STATUS" in pass|fail) ;; *) echo "error: --status must be pass|fail" >&2; exit 2;; esac
  SUB_PATH="${3:-}"
else
  SUB_PATH="${1:-}"
fi
[ -n "$SUB_PATH" ] || { echo "error: submodule path required" >&2; exit 2; }

# Must be inside a git repo that actually has this submodule.
git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "error: not inside a git repo" >&2; exit 2; }
git submodule status "$SUB_PATH" >/dev/null 2>&1 || { echo "error: '$SUB_PATH' is not a submodule" >&2; exit 2; }

ensure_ledger() {
  if [ ! -f "$LEDGER" ]; then
    cp "$TEMPLATE" "$LEDGER"
    echo "created ledger: $LEDGER"
  fi
}

if [ -n "$STATUS" ]; then
  # Update Validation on the last row matching this submodule path.
  [ -f "$LEDGER" ] || { echo "error: no ledger at $LEDGER" >&2; exit 1; }
  last_line="$(grep -n "| ${SUB_PATH} |" "$LEDGER" | tail -n1 | cut -d: -f1 || true)"
  [ -n "$last_line" ] || { echo "error: no ledger row for '$SUB_PATH'" >&2; exit 1; }
  # Column 7 is Validation; replace pending/pass/fail token in that row.
  awk -v ln="$last_line" -v st="$STATUS" 'NR==ln{sub(/\| (pending|pass|fail) \|/, "| " st " |")}1' "$LEDGER" > "$LEDGER.tmp" && mv "$LEDGER.tmp" "$LEDGER"
  echo "updated row $last_line: Validation=$STATUS"
  exit 0
fi

# Append a new bump row.
ensure_ledger
OLD_SHA="$(git ls-tree HEAD "$SUB_PATH" | awk '{print substr($3,1,7)}')"
NEW_SHA="$(git -C "$SUB_PATH" rev-parse --short HEAD)"
BRANCH="$(git -C "$SUB_PATH" symbolic-ref --short HEAD 2>/dev/null || echo 'DETACHED!')"
PARENT_COMMIT="$(basename "$(git rev-parse --show-toplevel)")@$(git rev-parse --short HEAD)"
DATE="$(date +%Y-%m-%d)"

if [ "$BRANCH" = "DETACHED!" ]; then
  echo "warning: submodule '$SUB_PATH' is on a DETACHED HEAD — create a project-<PARENT_SLUG>/<topic> branch first (see SKILL.md Phase 1)" >&2
fi

printf '| %s | %s | %s | %s | %s | %s | pending | - |\n' \
  "$DATE" "$SUB_PATH" "$BRANCH" "$OLD_SHA" "$NEW_SHA" "$PARENT_COMMIT" >> "$LEDGER"
echo "recorded bump: $SUB_PATH $OLD_SHA -> $NEW_SHA on $BRANCH (Validation=pending)"
