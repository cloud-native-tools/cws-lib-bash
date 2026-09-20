#!/usr/bin/env bash
# render-mermaid.sh — Render Mermaid to high-quality SVG and PNG
#
# Two rendering backends (REMOTE-FIRST policy):
#   • server — a mermaid.ink-compatible render server (MERMAID_SERVER, default
#              https://mermaid.ink). The source plus a default config is
#              zlib-compressed + base64-encoded (the official "pako:" state
#              protocol) and fetched from /svg/{enc} (SVG) and /img/{enc} (PNG).
#              THE DEFAULT — no local tooling needed.
#   • local  — mermaid-cli (`mmdc`, @mermaid-js/mermaid-cli) via npx; needs a
#              Chrome/Chromium for puppeteer (set PUPPETEER_EXECUTABLE_PATH if
#              your Chrome is in a non-standard location). ONLY with explicit
#              user consent (remote-first policy): when the server is
#              unreachable the script asks the user (TTY) or exits with
#              instructions for the agent to ask the user — it NEVER falls back
#              to local silently.
# Backend selection: MERMAID_BACKEND=server|local|auto (default server).
#   server → remote only; local only after user consent (prompt or error).
#   auto   → probe server; local still requires user consent.
#   local  → explicit opt-in (user already consented).
#
# Style is NOT injected: Mermaid styles are authored in-source via %%{init}%%
# directives / classDef / themeVariables (unlike PlantUML skinparams). The
# script only supplies a default theme + CJK-capable fontFamily config, which
# in-source directives override.
#
# Usage: render-mermaid.sh <input.mmd> [output_dir] [output_prefix]

set -euo pipefail

MERMAID_SERVER="${MERMAID_SERVER:-https://mermaid.ink}"
MERMAID_BACKEND="${MERMAID_BACKEND:-server}"   # server | local | auto (remote-first)
MERMAID_THEME="${MERMAID_THEME:-default}"    # default | neutral | dark | forest | base
MERMAID_FONT="${MERMAID_FONT:-Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif}"
SVG_SCALE=3        # mmdc scale for SVG (local backend only)
PNG_SCALE=2        # mmdc scale for PNG (local backend only)
HTTP_UA="render-mermaid.sh/1.0 (spec-kit draw-mermaid)"
PNG_MIN_SIZE=1000  # PNG smaller than this = likely a render error page

log() { printf '[render-mermaid] %s\n' "$*" >&2; }
warn() { printf '[render-mermaid] WARNING: %s\n' "$*" >&2; }

# ── Backend resolution ────────────────────────────────────────────────────────

# Encode source + default config into the mermaid.ink "pako:" state:
#   percent-encoded( base64( zlib( JSON {code, mermaid:{theme, themeVariables}} ) ) )
# pako.deflate produces a zlib stream, so python's zlib.compress matches it.
# Percent-encoding is required: base64 can contain '/' or '+' which would
# otherwise break the URL path (curl does not auto-encode like browsers).
# Reads the raw diagram source from stdin.
mermaid_state_encode() {
  python3 -c '
import sys, json, zlib, base64, urllib.parse, os
code = sys.stdin.read()
config = {
    "code": code,
    "mermaid": {
        "theme": os.environ.get("MERMAID_THEME", "default"),
        "themeVariables": {
            "fontFamily": os.environ.get(
                "MERMAID_FONT",
                "Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif"),
        },
    },
}
b64 = base64.b64encode(zlib.compress(json.dumps(config).encode("utf-8"))).decode()
sys.stdout.write(urllib.parse.quote(b64, safe=""))
'
}

# Probe whether a mermaid render server is reachable (tiny known-good diagram).
server_reachable() {
  local server="${1:-$MERMAID_SERVER}"
  local probe
  probe=$(printf 'graph TD\nA-->B' | mermaid_state_encode 2>/dev/null || true)
  [[ -z "$probe" ]] && return 1
  curl -sf -m 10 -H "User-Agent: ${HTTP_UA}" "${server}/img/pako:${probe}" -o /dev/null 2>/dev/null
}

# Locate mmdc (mermaid-cli). npx --yes fetches it on demand when absent.
resolve_mmdc() {
  if command -v mmdc >/dev/null 2>&1; then
    echo "mmdc"; return 0
  fi
  if command -v npx >/dev/null 2>&1; then
    echo "npx --yes @mermaid-js/mermaid-cli"; return 0
  fi
  return 1
}

# Remote-first consent gate for local rendering. Returns 0 only when the user
# explicitly agrees to fall back to mermaid-cli. Interactive when stdin is a
# TTY; otherwise (agent-driven Bash) exits with instructions so the agent asks
# the user — local rendering is NEVER chosen silently.
local_consent_gate() {
  local mmdc_cmd="${1:-}"
  if [[ -z "$mmdc_cmd" ]]; then
    warn "本地渲染需要 mermaid-cli（mmdc），但未找到（npx 不可用）。"
    warn "请先询问用户是否接受本地渲染；获确认并安装 @mermaid-js/mermaid-cli 后再以 MERMAID_BACKEND=local 重试。"
    return 1
  fi
  if [[ -t 0 ]]; then
    local ans
    read -r -p "[render-mermaid] 远端渲染不可用，是否改用本地渲染（mermaid-cli + Chrome）？[y/N] " ans
    [[ "$ans" =~ ^[yY] ]]
  else
    warn "远端渲染不可用（${MERMAID_SERVER} 不可达）。"
    warn "本地渲染需用户确认：请先询问用户是否接受本地渲染（需要 @mermaid-js/mermaid-cli + Chrome）；"
    warn "获确认后以 MERMAID_BACKEND=local 重新执行。"
    return 1
  fi
}

# Decide which backend to use. Echoes "server <url>" or "local <cmd>".
# Remote-first: server is tried first; local is used ONLY after user consent.
# Exits when neither a reachable server nor a consented local tool is available.
select_backend() {
  local mmdc_cmd; mmdc_cmd="$(resolve_mmdc || true)"
  case "$MERMAID_BACKEND" in
    local)
      [[ -n "$mmdc_cmd" ]] || { warn "MERMAID_BACKEND=local but no mmdc/npx found"; exit 1; }
      echo "local $mmdc_cmd" ;;
    server|auto|*)
      if server_reachable "$MERMAID_SERVER"; then
        echo "server $MERMAID_SERVER"
        return
      fi
      warn "Render server unreachable (${MERMAID_SERVER})."
      if local_consent_gate "$mmdc_cmd"; then
        echo "local $mmdc_cmd"
      else
        exit 1
      fi ;;
  esac
}

# ── Rendering ─────────────────────────────────────────────────────────────────

# Render a .mmd to a target format via the chosen backend.
# render_diagram <mmd_file> <out_file> <svg|png>
render_diagram() {
  local mmd="$1" out="$2" fmt="$3"
  if [[ "$BACKEND" == "local" ]]; then
    local cfg="${out}.mermaid.json"
    cat > "$cfg" <<EOF
{
  "theme": "${MERMAID_THEME}",
  "fontFamily": "${MERMAID_FONT}"
}
EOF
    local scale=$SVG_SCALE
    [[ "$fmt" == "png" ]] && scale=$PNG_SCALE
    if ! $MMDC_CMD -i "$mmd" -o "$out" -b white -s "$scale" -c "$cfg" 2>"${out}.mmdclog"; then
      warn "mermaid-cli rendering failed (${fmt}):"; sed 's/^/[mmdc] /' "${out}.mmdclog" >&2 || true
      rm -f "${out}.mmdclog" "$cfg"; return 1
    fi
    rm -f "${out}.mmdclog" "$cfg"
    [[ -f "$out" ]]
  else
    local enc
    if ! enc="$(mermaid_state_encode < "$mmd")" || [[ -z "$enc" ]]; then
      warn "Mermaid state encoding failed (python3 required for server backend)"
      return 1
    fi
    local path="svg"
    [[ "$fmt" == "png" ]] && path="img"
    # mermaid.ink /img/ defaults to JPEG; ?type=png forces PNG output.
    local query=""
    [[ "$fmt" == "png" ]] && query="?type=png"
    curl -sf -m 60 -H "User-Agent: ${HTTP_UA}" "${MERMAID_SERVER}/${path}/pako:${enc}${query}" -o "$out"
  fi
}

# Validate PNG output is not blank/corrupted (returns 0 if valid).
validate_png() {
  local png_file="$1"
  [[ -f "$png_file" ]] || return 1
  local size; size=$(wc -c < "$png_file" | tr -d ' ')
  (( size >= PNG_MIN_SIZE )) || return 1
  if command -v file >/dev/null 2>&1 && ! file "$png_file" | grep -qi 'png image'; then
    return 1
  fi
  return 0
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  local input="${1:-}" output_dir="${2:-.}" prefix="${3:-diagram}"

  if [[ -z "$input" ]] || [[ ! -f "$input" ]]; then
    echo "Usage: render-mermaid.sh <input.mmd> [output_dir] [output_prefix]" >&2
    exit 1
  fi

  mkdir -p "$output_dir"

  # ── Select rendering backend ──
  local _selection
  _selection="$(select_backend)"
  BACKEND="${_selection%% *}"
  MMDC_CMD="${_selection#* }"
  if [[ "$BACKEND" == "local" ]]; then
    log "Backend: local mermaid-cli (${MMDC_CMD})"
  else
    MERMAID_SERVER="${MMDC_CMD}"
    log "Backend: server (${MERMAID_SERVER})"
  fi

  local mmd="${output_dir}/${prefix}.mmd"
  local svg="${output_dir}/${prefix}.svg"
  local png="${output_dir}/${prefix}.png"

  # ── Save the source next to the outputs (editable for future iterations) ──
  if [[ "$(cd "$(dirname "$input")" && pwd)/$(basename "$input")" != "$(cd "$output_dir" && pwd)/${prefix}.mmd" ]]; then
    cp -f "$input" "$mmd"
  fi
  log "Source saved: ${mmd}"

  # ── Step 1: Render SVG (vector, no size limit) ──
  log "Rendering SVG..."
  if ! render_diagram "$mmd" "$svg" svg; then
    warn "SVG rendering failed"
    exit 1
  fi

  # ── Step 2: Render PNG ──
  log "Rendering PNG..."
  if ! render_diagram "$mmd" "$png" png; then
    warn "PNG rendering failed (SVG still produced)"
  elif ! validate_png "$png"; then
    warn "PNG output appears invalid; removing it (use SVG for this diagram)"
    rm -f "$png"
  fi

  # ── Step 3: Report results ──
  local svg_vb png_dim
  svg_vb=$(grep -oE 'viewBox="[^"]*"' "$svg" 2>/dev/null | head -1 || echo "unknown")
  png_dim="n/a"
  if [[ -f "$png" ]]; then
    png_dim=$(file "$png" 2>/dev/null | grep -oE '[0-9]+ ?x ?[0-9]+' | head -1 || echo "unknown")
  fi

  echo "=== Rendering Complete ==="
  echo "Source: ${mmd}"
  echo "SVG:    ${svg} (${svg_vb})"
  echo "PNG:    ${png} (${png_dim})"
  echo "Backend: ${BACKEND}"
  # Dense-diagram tip: a narrow PNG (e.g. <1200px wide) compresses borders/text.
  # Zoom does NOT help (canvas scales with it) — raise fontSize or embed SVG wide.
  local png_w="${png_dim%% *}"
  if [[ "$png_w" =~ ^[0-9]+$ ]] && (( png_w < 1200 )); then
    echo "NOTE: PNG 仅 ${png_w}px 宽 — 文字密集时 HTML 请改引 SVG 并给足显示宽度，或上调 fontSize 重渲（放大 zoom 无效；有效字号量测见 howto/12 §2）。"
  fi
  [[ -f "$png" ]] || echo "NOTE: PNG not produced — embed the SVG for this diagram."
}

main "$@"
