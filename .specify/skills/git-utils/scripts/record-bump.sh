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
#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
_script_interface_guard() {
    _sig_name="${0##*/}"
    _sig_stop=0
    for _sig_arg in "$@"; do
        if [ "$_sig_stop" -eq 1 ]; then continue; fi
        case "$_sig_arg" in
            --) _sig_stop=1 ;;
            -h|--help) return 0 ;;
            --version)
                _sig_dir="$(dirname -- "$0")"
                case "$_sig_dir" in /*) ;; *) _sig_dir="./$_sig_dir" ;; esac
                _sig_ver="unknown"
                _sig_level=0
                while [ -d "$_sig_dir" ] && [ "$_sig_level" -le 12 ]; do
                    if [ -f "$_sig_dir/pyproject.toml" ] && [ -e "$_sig_dir/.git" ]; then
                        _sig_ver="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$_sig_dir/pyproject.toml" 2>/dev/null | head -n 1)"
                        [ -n "$_sig_ver" ] || _sig_ver="unknown"
                        break
                    fi
                    if [ "$_sig_dir" = "/" ]; then break; fi
                    _sig_dir="$(dirname -- "$_sig_dir")"
                    _sig_level=$((_sig_level + 1))
                done
                printf '%s %s\n' "$_sig_name" "$_sig_ver"
                exit 0 ;;
        esac
    done
    return 0
}
_script_interface_guard "$@"

# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its bash half by
# `.specify/scripts/bash/script-interface.sh` and `.specify/scripts/python/sync-mirrors.py`. No rule of its own.)
_sig_usage() {
    printf 'usage: %s\n' 'record-bump.sh [arguments]'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' 'appends or annotates one row in the parent ledger; a flag-only invocation writes nothing'
    printf ''exit-codes:' %s\n' '0 success; 1 a documented check failed; 2 argument or environment error'
}

_sig_answers() {
    _sig_want=""
    _sig_stop=0
    for _sig_tok in "$@"; do
        if [ "$_sig_stop" -eq 1 ]; then continue; fi
        case "$_sig_tok" in
            --) _sig_stop=1 ;;
            -h|--help) [ -n "$_sig_want" ] || _sig_want=help ;;
            --version) [ -n "$_sig_want" ] || _sig_want=version ;;
            -*)
                case " --status " in
                    *" $_sig_tok "*) ;;
                    *)
                        if [ -z "" ]; then
                            printf 'error: unrecognized option: %s\n' "$_sig_tok" >&2
                            _sig_usage >&2
                            exit 2
                        fi
                        ;;
                esac
                ;;
        esac
    done
    case "$_sig_want" in
        help) _sig_usage; exit 0 ;;
    esac
    return 0
}

_sig_answers "$@"
set -u
# script-interface:86:end

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
