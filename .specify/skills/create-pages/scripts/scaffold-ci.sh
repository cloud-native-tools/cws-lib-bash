#!/usr/bin/env bash
# scaffold-ci.sh — Stage 3 (pages service): render a hosting platform's CI pipeline.
#
# Stages 1 and 2 own the content and the rendering: the docs directory is the
# content source, and scaffold-hugo.py turns it into a Hugo project that builds
# to <docs-dir>/public. This script only wires a hosting platform's pipeline to
# that build output — it never writes Hugo config, layouts, or build scripts.
#
# Usage:
#   scaffold-ci.sh --site-name <name> [options]
#
# Options:
#   --site-name <name>   Required. Deploy site name (pages-service site identifier).
#   --platform <name>    Hosting platform (default: aoneci). Templates live in
#                        .specify/scripts/ci-templates/<name>/; registry: .specify/scripts/ci-templates/README.md.
#   --branch <branch>    Production branch (default: main).
#   --image <image>      Hugo build image — environment-specific, override per environment
#                        (default: the shared ci-templates/hugo-image.txt, which stage 2's
#                        local docker builds read too, so local and CI use one Hugo).
#   --docs-dir <dir>     Docs directory name relative to project root (default: docs).
#   --root <dir>         Target project root (default: current directory).
#   --force              Overwrite the CI file if it already exists.
#   --help               Show this help.
#
# Creates exactly one file — the platform's CI pipeline, rendered from
# .specify/scripts/ci-templates/<platform>/deploy-pages.yaml.tpl:
#   aoneci -> .aoneci/deploy-pages.yaml
#   github -> .github/workflows/deploy-pages.yaml
# That CI file is the ONLY artifact this skill writes outside the docs directory:
# hosting platforms discover pipelines at a fixed repository-root path, so it
# cannot live inside docs/. Platforms without a template write nothing and warn.
# Output: JSON summary on stdout: {"created": [...], "skipped": [...], "warnings": [...]}.
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
    printf 'usage: %s\n' 'scaffold-ci.sh [arguments]'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' 'writes a CI workflow under the docs root when --action apply; a flag-only invocation writes nothing'
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
                case " --branch --docs-dir --force --image --platform --root --site-name " in
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/ci-templates"
IMAGE_FILE="$TEMPLATES_DIR/hugo-image.txt"

# The build image is shared with stage 2: scaffold-hugo.py runs local builds in this
# same image, so a local render and the CI render use one Hugo version.
resolve_default_image() {
  if [ -f "$IMAGE_FILE" ]; then
    grep -v '^[[:space:]]*#' "$IMAGE_FILE" | grep -v '^[[:space:]]*$' | head -n 1
  else
    printf '%s' "reg.docker.alibaba-inc.com/xuanji-images/hugo:latest"
  fi
}

SITE_NAME=""
BRANCH="main"
PLATFORM="aoneci"
IMAGE="$(resolve_default_image)"
DOCS_DIR="docs"
ROOT="$(pwd)"
FORCE=0

usage() { awk 'NR > 1 && !/^#/ {exit} NR > 1 {print}' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --site-name) SITE_NAME="$2"; shift 2 ;;
    --platform)  PLATFORM="$2"; shift 2 ;;
    --branch)    BRANCH="$2"; shift 2 ;;
    --image)     IMAGE="$2"; shift 2 ;;
    --docs-dir)  DOCS_DIR="$2"; shift 2 ;;
    --root)      ROOT="$2"; shift 2 ;;
    --force)     FORCE=1; shift ;;
    --help|-h)   usage; exit 0 ;;
    *) echo "ERROR: unknown option: $1" >&2; exit 2 ;;
  esac
done

[ -n "$SITE_NAME" ] || { echo "ERROR: --site-name is required (see --help)" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "ERROR: --root directory does not exist: $ROOT" >&2; exit 2; }
[ -d "$TEMPLATES_DIR/$PLATFORM" ] || {
  KNOWN=$(cd "$TEMPLATES_DIR" 2>/dev/null && ls -d */ 2>/dev/null | tr -d '/' | tr '\n' ' ')
  echo "ERROR: unknown --platform '$PLATFORM' (known: ${KNOWN:-none}; see .specify/scripts/ci-templates/README.md)" >&2
  exit 2
}

ci_target_for_platform() {
  case "$1" in
    aoneci) printf '%s' ".aoneci/deploy-pages.yaml" ;;
    github) printf '%s' ".github/workflows/deploy-pages.yaml" ;;
    *)      printf '%s' "" ;;
  esac
}

CREATED=()
SKIPPED=()
WARNINGS=()

json_list() {
  local out="" item
  for item in "$@"; do
    [ -n "$out" ] && out="$out, "
    out="$out\"$item\""
  done
  printf '[%s]' "$out"
}

sub() { # substitute placeholders in $1 (pure bash — no sed escaping issues)
  local s="$1"
  s="${s//__SITE_NAME__/$SITE_NAME}"
  s="${s//__BRANCH__/$BRANCH}"
  s="${s//__IMAGE__/$IMAGE}"
  s="${s//__DOCS_DIR__/$DOCS_DIR}"
  printf '%s' "$s"
}

cd "$ROOT"

# Stage-ordering preflight: the pipeline builds whatever stage 2 scaffolded.
if [ ! -d "$DOCS_DIR" ]; then
  WARNINGS+=("$DOCS_DIR/ does not exist — the CI guard handles absence, but stage 1 has no content yet")
elif [ ! -f "$DOCS_DIR/hugo.toml" ]; then
  WARNINGS+=("$DOCS_DIR/hugo.toml missing — run stage 2 (scaffold-hugo.py --action scaffold) or the pipeline publishes an empty site")
fi

CI_TPL="$TEMPLATES_DIR/$PLATFORM/deploy-pages.yaml.tpl"
CI_TARGET="$(ci_target_for_platform "$PLATFORM")"
if [ ! -f "$CI_TPL" ]; then
  WARNINGS+=("platform '$PLATFORM' has no template yet (see .specify/scripts/ci-templates/$PLATFORM/README.md) — nothing written; author the CI file manually")
elif [ -z "$CI_TARGET" ]; then
  WARNINGS+=("platform '$PLATFORM' has a template but no registered target path in scaffold-ci.sh — CI file not written")
elif [ -e "$CI_TARGET" ] && [ "$FORCE" -ne 1 ]; then
  SKIPPED+=("$CI_TARGET")
else
  mkdir -p "$(dirname "$CI_TARGET")"
  printf '%s\n' "$(sub "$(cat "$CI_TPL")")" > "$CI_TARGET"
  CREATED+=("$CI_TARGET")
fi

printf '{"created": %s, "skipped": %s, "warnings": %s}\n' \
  "$(json_list "${CREATED[@]+"${CREATED[@]}"}")" \
  "$(json_list "${SKIPPED[@]+"${SKIPPED[@]}"}")" \
  "$(json_list "${WARNINGS[@]+"${WARNINGS[@]}"}")"
