#!/usr/bin/env bash
# render-excalidraw.sh — Render Excalidraw scene JSON to high-quality SVG + PNG
# via a self-hosted excalidraw render service.
#
# Same remote-first policy as draw-plantuml's render-plantuml.sh:
#   • server — POST the scene to an excalidraw render service (EXCALIDRAW_SERVER).
#              THE DEFAULT. The service is the `scripts/server/` bundled with the
#              draw-excalidraw skill (Node + headless Chromium driving the real
#              @excalidraw/excalidraw export pipeline).
#   • local  — start the bundled render service on this machine for this run,
#              then render. ONLY with explicit user consent (agent must ask the
#              user first): run `npm install`/`npm run build` if needed, launch
#              node server.mjs on a scratch port, render, stop it.
# Backend selection: EXCALIDRAW_BACKEND=server|local (default server).
#   server → remote only; when unreachable the script exits with instructions
#            for the agent to ask the user (never silently switches backend).
#   local  → explicit opt-in (user already consented).
#
# Usage: render-excalidraw.sh <input.excalidraw|.json> [output_dir] [output_prefix]
#
# Env:
#   EXCALIDRAW_SERVER      base URL of the render service (default http://127.0.0.1:8383)
#   EXCALIDRAW_BACKEND     server | local (default server)
#   EXCALIDRAW_SCALE       PNG scale factor (default 2)
#   EXCALIDRAW_PADDING     export padding px (default 16)
#   EXCALIDRAW_BG          viewBackgroundColor (default: scene's own or #ffffff)
#   EXCALIDRAW_LOCAL_PORT  port for the local-mode scratch server (default 8393)
#   EXCALIDRAW_CHROMIUM_PATH  browser binary for local mode (auto-detected if unset)
#
# Input: a `.excalidraw`/`.json` file — either a full scene object
# ({"type":"excalidraw","elements":[...]}) or a request wrapper that already
# contains a "scene" key. Output: <output_dir>/<prefix>.svg + <prefix>.png.

set -euo pipefail

EXCALIDRAW_SERVER="${EXCALIDRAW_SERVER:-http://127.0.0.1:8383}"
EXCALIDRAW_BACKEND="${EXCALIDRAW_BACKEND:-server}"   # server | local (remote-first)
EXCALIDRAW_SCALE="${EXCALIDRAW_SCALE:-2}"
EXCALIDRAW_PADDING="${EXCALIDRAW_PADDING:-16}"
EXCALIDRAW_LOCAL_PORT="${EXCALIDRAW_LOCAL_PORT:-8393}"
HTTP_UA="render-excalidraw.sh/1.0 (draw-excalidraw skill)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${SCRIPT_DIR}/server"

log() { printf '[render-excalidraw] %s\n' "$*" >&2; }
warn() { printf '[render-excalidraw] WARNING: %s\n' "$*" >&2; }
die() { printf '[render-excalidraw] ERROR: %s\n' "$*" >&2; exit "${2:-1}"; }

# Single global cleanup (EXIT trap): remove temp request files and stop a
# local-mode scratch server. Deliberately no RETURN traps — under `set -u`
# they fire after locals are released and abort the script.
TMP_FILES=()
LOCAL_SERVER_PID=""
cleanup() {
  local f
  for f in ${TMP_FILES[@]+"${TMP_FILES[@]}"}; do
    [[ -n "$f" ]] && rm -f "$f" 2>/dev/null
  done
  if [[ -n "$LOCAL_SERVER_PID" ]]; then
    kill "$LOCAL_SERVER_PID" 2>/dev/null
    local i
    for i in 1 2 3 4 5 6; do
      kill -0 "$LOCAL_SERVER_PID" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$LOCAL_SERVER_PID" 2>/dev/null; then
      kill -9 "$LOCAL_SERVER_PID" 2>/dev/null || true
    fi
  fi
  return 0
}
trap cleanup EXIT

usage() {
  echo "Usage: render-excalidraw.sh <input.excalidraw|.json> [output_dir] [output_prefix]" >&2
  exit 64
}

[[ $# -ge 1 ]] || usage
INPUT="$1"
OUT_DIR="${2:-$(dirname "$INPUT")}"
PREFIX="${3:-$(basename "${INPUT%.*}")}"
[[ -f "$INPUT" ]] || die "input file not found: $INPUT"
mkdir -p "$OUT_DIR"

command -v curl >/dev/null || die "curl is required"
command -v python3 >/dev/null || die "python3 is required"

# ── Request body construction ─────────────────────────────────────────────────

# Build a request JSON file for the given format (svg|png). Accepts either a
# bare scene object or an existing {scene: ...} wrapper.
build_request() {
  local format="$1" out="$2"
  python3 - "$INPUT" "$format" "$out" <<'PY'
import json, sys
src, fmt, out = sys.argv[1], sys.argv[2], sys.argv[3]
data = json.load(open(src, encoding="utf-8"))
if "scene" not in data:
    data = {"scene": data}
data["format"] = fmt
if fmt == "png":
    data.setdefault("scale", 2)
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False)
PY
}

# Scale injected from env (request file may already carry one; env wins).
apply_env_overrides() {
  local req="$1"
  python3 - "$req" "$EXCALIDRAW_SCALE" "$EXCALIDRAW_PADDING" "${EXCALIDRAW_BG:-}" <<'PY'
import json, sys
req, scale, padding, bg = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
d = json.load(open(req, encoding="utf-8"))
if d.get("format") == "png":
    d["scale"] = scale
d["padding"] = padding
if bg:
    d["viewBackgroundColor"] = bg
json.dump(d, open(req, "w", encoding="utf-8"), ensure_ascii=False)
PY
}

# ── Health probe & render ────────────────────────────────────────────────────

server_reachable() {
  local base="${1:-$EXCALIDRAW_SERVER}"
  curl -sf -m 6 -H "User-Agent: ${HTTP_UA}" "${base}/health" -o /dev/null 2>/dev/null
}

render_via() {
  local base="$1"
  local req_svg req_png
  req_svg="$(mktemp -t excalidraw-req-svg.XXXXXX)"
  req_png="$(mktemp -t excalidraw-req-png.XXXXXX)"
  TMP_FILES+=("$req_svg" "$req_png")

  build_request svg "$req_svg"; apply_env_overrides "$req_svg"
  build_request png "$req_png"; apply_env_overrides "$req_png"

  log "rendering SVG via ${base}/render"
  curl -sf -m 120 -H "User-Agent: ${HTTP_UA}" -H "Content-Type: application/json" \
    --data @"$req_svg" "${base}/render" -o "${OUT_DIR}/${PREFIX}.svg" \
    || die "SVG render failed (server ${base})"

  log "rendering PNG via ${base}/render (scale=${EXCALIDRAW_SCALE})"
  curl -sf -m 180 -H "User-Agent: ${HTTP_UA}" -H "Content-Type: application/json" \
    --data @"$req_png" "${base}/render" -o "${OUT_DIR}/${PREFIX}.png" \
    || die "PNG render failed (server ${base})"

  [[ -s "${OUT_DIR}/${PREFIX}.svg" ]] || die "SVG output is empty"
  [[ -s "${OUT_DIR}/${PREFIX}.png" ]] || die "PNG output is empty"
  log "done: ${OUT_DIR}/${PREFIX}.svg , ${OUT_DIR}/${PREFIX}.png"
  echo "${OUT_DIR}/${PREFIX}.svg"
  echo "${OUT_DIR}/${PREFIX}.png"
}

# ── Local backend (explicit opt-in only) ─────────────────────────────────────

run_local_server() {
  [[ -d "$SERVER_DIR" ]] || die "bundled render server not found at $SERVER_DIR"
  command -v node >/dev/null || die "local mode requires Node.js >= 18"
  command -v npm >/dev/null || die "local mode requires npm"

  if [[ ! -d "$SERVER_DIR/node_modules" ]]; then
    log "first local run: installing render server dependencies (npm install)…"
    (cd "$SERVER_DIR" && npm install --no-audit --no-fund >&2)
  fi
  if [[ ! -f "$SERVER_DIR/static/dist/render.js" ]]; then
    log "first local run: building renderer bundle (npm run build)…"
    (cd "$SERVER_DIR" && npm run build >&2)
  fi

  local port="$EXCALIDRAW_LOCAL_PORT"
  local srv_log
  srv_log="$(mktemp -t excalidraw-render-local.XXXXXX)"
  TMP_FILES+=("$srv_log")
  log "starting local render server on 127.0.0.1:${port} (log: ${srv_log})"
  # Launch node directly (no subshell): $! must be the real node PID so the
  # cleanup can kill it; ESM resolves deps relative to server.mjs, so no cd
  # is needed. Output goes to a log file — never inherit our pipes, or a
  # surviving process would hold them open.
  EXCALIDRAW_PORT="$port" node "${SERVER_DIR}/server.mjs" >"$srv_log" 2>&1 &
  LOCAL_SERVER_PID=$!

  local i
  for i in $(seq 1 60); do
    if server_reachable "http://127.0.0.1:${port}"; then break; fi
    if ! kill -0 "$LOCAL_SERVER_PID" 2>/dev/null; then
      tail -20 "$srv_log" >&2
      die "local render server exited early (see ${srv_log})"
    fi
    sleep 1
  done
  server_reachable "http://127.0.0.1:${port}" \
    || { tail -20 "$srv_log" >&2; die "local render server did not become healthy within 60s"; }

  render_via "http://127.0.0.1:${port}"
}

# ── Backend dispatch (remote-first) ───────────────────────────────────────────

case "$EXCALIDRAW_BACKEND" in
  server)
    if ! server_reachable; then
      warn "render service unreachable at ${EXCALIDRAW_SERVER}."
      warn "请先询问用户："
      warn "  1) 已有部署：确认/修正 EXCALIDRAW_SERVER 地址后重试；或"
      warn "  2) 本机临时启动渲染服务（local 模式，需 Node.js 与 Chromium）——"
      warn "     获得用户确认后以 EXCALIDRAW_BACKEND=local 重新调用本脚本。"
      warn "未经用户确认，不得静默切换到 local 模式。"
      exit 2
    fi
    render_via "$EXCALIDRAW_SERVER"
    ;;
  local)
    run_local_server
    ;;
  *)
    die "unknown EXCALIDRAW_BACKEND: $EXCALIDRAW_BACKEND (expected server|local)"
    ;;
esac
