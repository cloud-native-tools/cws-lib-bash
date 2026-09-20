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
#   bash scripts/vendor-echarts.sh <target-dir> [version]
#     <target-dir>  deliverable directory that should contain vendor/
#     [version]     pinned ECharts version, default 5.6.0
#
# The generated file is vendor/echarts.min.js, referenced first by the
# template loader (CDN is only a fallback, and the loader never uses
# document.write).
# ============================================================
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
