#!/usr/bin/env bash
# ============================================================
# vendor-echarts.sh — place a real, pinned echarts.min.js into
# the deliverable's vendor/ directory (offline-critical output).
#
# Rationale (R1 review): a vendor/ directory that stays empty and an
# HTML that only *falls back* to a local copy render a blank canvas
# in offline sandboxes. This script makes the local copy real and
# verifies it, so the deliverable renders without any network access.
#
# Usage:
#   bash .specify/scripts/vendor-echarts.sh <target-dir> [version]
#     <target-dir>  deliverable directory that should contain vendor/
#     [version]     pinned ECharts version, default 5.6.0
#
# The generated file is vendor/echarts.min.js, referenced first by the
# template loader (CDN is only a fallback, and the loader never uses
# document.write).
# ============================================================
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
    printf 'usage: %s\n' '\nbash .specify/scripts/vendor-echarts.sh <target-dir> [version]\n<target-dir>  deliverable directory that should contain vendor/\n[version]     pinned ECharts version, default 5.6.0'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' 'writes only through the options it documents; a flag-only invocation writes nothing'
    printf ''exit-codes:' %s\n' '0 the request was answered; 2 argument error; 3 a check found something to report'
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
                case "  " in
                    *" $_sig_tok "*) ;;
                    *)
                        if [ -z "1" ]; then
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

DIR="${1:?usage: vendor-echarts.sh <target-dir> [version]}"
VERSION="${2:-5.6.0}"
VENDOR_DIR="$DIR/vendor"
OUT="$VENDOR_DIR/echarts.min.js"
URL="https://cdn.jsdelivr.net/npm/echarts@${VERSION}/dist/echarts.min.js"

mkdir -p "$VENDOR_DIR"

echo "==> Downloading echarts@${VERSION} into $OUT"
if command -v curl >/dev/null 2>&1; then
  if ! curl -fsSL --connect-timeout 10 --max-time 60 --retry 2 --retry-delay 2 -o "$OUT" "$URL"; then
    echo "ERROR: curl failed to download $URL (network unreachable?)" >&2
    echo "       Place the file manually: download $URL and save it as $OUT" >&2
    rm -f "$OUT"
    exit 1
  fi
elif command -v wget >/dev/null 2>&1; then
  if ! wget -q -O "$OUT" "$URL"; then
    echo "ERROR: wget failed to download $URL (network unreachable?)" >&2
    echo "       Place the file manually: download $URL and save it as $OUT" >&2
    rm -f "$OUT"
    exit 1
  fi
else
  echo "ERROR: neither curl nor wget is available — download $URL manually to $OUT" >&2
  exit 1
fi

# --- verification: the file must be real and non-empty --------------
if [ ! -s "$OUT" ]; then
  echo "ERROR: download produced an empty/missing file at $OUT" >&2
  rm -f "$OUT"
  exit 1
fi

SIZE=$(wc -c < "$OUT")
echo "==> vendor/echarts.min.js present: $SIZE bytes"

# Version marker check: echarts.min.js starts with a banner comment.
HEADER=$(head -c 300 "$OUT" | tr -d '\n')
if printf '%s' "$HEADER" | grep -q "v${VERSION}"; then
  echo "==> version marker v${VERSION} found in banner"
else
  echo "WARN: could not confirm version marker 'v${VERSION}' in the file header" >&2
  echo "      (header: ${HEADER:0:120})" >&2
fi

# JS syntax check when node is available (deterministic, no browser needed).
if command -v node >/dev/null 2>&1; then
  if node --check "$OUT" >/dev/null 2>&1; then
    echo "==> node --check passed (valid JS)"
  else
    echo "ERROR: node --check failed on $OUT — file is not valid JavaScript" >&2
    exit 1
  fi
else
  echo "WARN: node not found, skipped JS syntax check" >&2
fi

echo "==> Done. HTML loader references vendor/echarts.min.js first; CDN is only a fallback."
