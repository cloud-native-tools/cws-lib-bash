#!/usr/bin/env bash
# provision-git-server.sh — remote-side reconcile for turning a plain SSH server
# into a Git server.
#
# Ensures, on a target reachable over SSH:
#   D1  the git user exists (home = git home, shell = /bin/bash)
#   D2  bare repositories exist at <git-home>/<namespace>/<repo>.git, owned by
#       the git user, with HEAD pointing at refs/heads/<initial-branch>
#   D3  the supplied public keys are present in <git-home>/.ssh/authorized_keys
#       (deduplicated by fingerprint) with strict ownership and permissions
#
# Idempotent: re-running converges only the gaps it reports. Nothing is
# destroyed — an existing user, repository, or key is reported, never replaced.
#
# Requires admin SSH access to the target (root, or a sudo-capable user).
#
# Usage:
#   provision-git-server.sh --host <ssh-alias|user@host> [options]
#
# Options:
#   --host <target>            REQUIRED. SSH target with admin access.
#   --repo <namespace/name>    Bare repo to ensure. Repeatable. The remote path
#                              is <git-home>/<namespace/name>.git, so the git
#                              remote URL becomes git@<alias>:<namespace/name>.git
#   --pubkey <path>            Public key file to authorize. Repeatable.
#                              Defaults: the identity files ssh would offer for
#                              --host (resolved via `ssh -G`), .pub counterpart.
#   --git-user <name>          Default: git
#   --git-home <path>          Default: /home/git
#   --initial-branch <name>    Default: main
#   --check                    Observe only; report gaps, change nothing.
#                              Exit 0 = converged, 3 = gaps found.
#   --dry-run                  Print the remote script without executing it.
#   -h | --help                Show this help.

set -euo pipefail

SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"

HOST=""
GIT_USER="git"
GIT_HOME="/home/git"
INIT_BRANCH="main"
MODE="apply"
DRY_RUN=false
REPOS=()
PUBKEYS=()

die() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }
info() { printf '%s\n' "$*" >&2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --host)            HOST="${2:-}"; shift 2 ;;
    --repo)            REPOS+=("${2:-}"); shift 2 ;;
    --pubkey)          PUBKEYS+=("${2:-}"); shift 2 ;;
    --git-user)        GIT_USER="${2:-}"; shift 2 ;;
    --git-home)        GIT_HOME="${2:-}"; shift 2 ;;
    --initial-branch)  INIT_BRANCH="${2:-}"; shift 2 ;;
    --check)           MODE="check"; shift ;;
    --dry-run)         DRY_RUN=true; shift ;;
    -h|--help)         sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)                 die "unknown argument: $1 (try --help)" ;;
  esac
done

[ -n "$HOST" ] || die "--host is required"
command -v ssh >/dev/null 2>&1 || die "ssh not found in PATH"

# --- default the public keys to what ssh would already offer for this host.
# Rationale: the git alias will authenticate with the same identity files, so
# authorizing exactly those guarantees the later `git ls-remote` succeeds.
if [ ${#PUBKEYS[@]} -eq 0 ]; then
  while IFS= read -r idf; do
    [ -n "$idf" ] || continue
    # ssh -G prints IdentityFile values unexpanded ('~/.ssh/id_rsa'). Quote the
    # '~' in the case pattern — an unquoted ${var#~/} would tilde-expand the
    # pattern to $HOME/ and silently fail to strip the literal '~/' prefix.
    case "$idf" in
      /*)     : ;;                       # already absolute
      '~/'*)  idf="${HOME}/${idf:2}" ;;  # literal ~/ prefix
      '~'*)   : ;;                       # ~otheruser — leave for ssh to resolve
      *)      idf="${HOME}/${idf}" ;;    # relative to home
    esac
    if [ -f "${idf}.pub" ]; then
      PUBKEYS+=("${idf}.pub")
    fi
  done < <(ssh -G "$HOST" 2>/dev/null | awk '/^identityfile /{print $2}')
fi
[ ${#PUBKEYS[@]} -gt 0 ] || die "no public keys resolved; pass --pubkey <path> explicitly"

# --- validate and fingerprint every key locally, before touching the remote.
KEY_PAYLOAD=()
for pk in "${PUBKEYS[@]}"; do
  [ -f "$pk" ] || die "public key not found: $pk"
  fp=$(ssh-keygen -lf "$pk" 2>/dev/null | awk '{print $2}') || die "unreadable key: $pk"
  [ -n "$fp" ] || die "cannot fingerprint: $pk"
  # base64 keeps arbitrary key content/comment safe across the ssh transport
  b64=$(base64 < "$pk" | tr -d '\n')
  KEY_PAYLOAD+=("${fp}|${b64}|${pk}")
  info "key: ${fp}  <- ${pk}"
done

for r in ${REPOS[@]+"${REPOS[@]}"}; do
  case "$r" in
    */*) ;;
    *)   die "--repo must be namespaced as <namespace>/<name>, got: $r" ;;
  esac
  case "$r" in
    /*|*.git|*..*) die "--repo must be a relative, non-.git-suffixed path: $r" ;;
  esac
done

# --- build the generated header carrying the resolved inputs.
HEADER=$(cat <<GEN
GIT_USER=$(printf '%q' "$GIT_USER")
GIT_HOME=$(printf '%q' "$GIT_HOME")
INIT_BRANCH=$(printf '%q' "$INIT_BRANCH")
MODE=$(printf '%q' "$MODE")
REPOS=($(printf '%q ' ${REPOS[@]+"${REPOS[@]}"}))
KEY_PAYLOAD=($(printf '%q ' "${KEY_PAYLOAD[@]}"))
GEN
)

# --- static remote body. Quoted heredoc: no local expansion happens here.
BODY=$(cat <<'REMOTE_EOF'
set -uo pipefail

GAPS=0
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else
    echo "FATAL: remote user '$(id -un)' is not root and sudo is unavailable"; exit 2
  fi
fi

emit() { printf '%-5s %s\n' "$1" "$2"; }
gap()  { GAPS=$((GAPS + 1)); emit "GAP" "$1"; }
act()  { emit "DONE" "$1"; }
ok()   { emit "OK" "$1"; }

GIT_GROUP="$GIT_USER"

echo "== target: $(hostname 2>/dev/null || uname -n)  (mode=$MODE, as $(id -un))"

# ---------- D1: git user ----------
if getent passwd "$GIT_USER" >/dev/null 2>&1; then
  ACTUAL_HOME=$(getent passwd "$GIT_USER" | cut -d: -f6)
  ACTUAL_SHELL=$(getent passwd "$GIT_USER" | cut -d: -f7)
  ok "user '$GIT_USER' exists (uid=$(id -u "$GIT_USER"), home=$ACTUAL_HOME, shell=$ACTUAL_SHELL)"
  GIT_GROUP=$(id -gn "$GIT_USER")
  [ "$ACTUAL_HOME" = "$GIT_HOME" ] || gap "user home is $ACTUAL_HOME, expected $GIT_HOME (not auto-corrected)"
else
  if [ "$MODE" = apply ]; then
    $SUDO useradd --create-home --home-dir "$GIT_HOME" --shell /bin/bash "$GIT_USER" \
      && act "created user '$GIT_USER' (uid=$(id -u "$GIT_USER"), home=$GIT_HOME)" \
      || { echo "FATAL: useradd failed"; exit 2; }
    GIT_GROUP=$(id -gn "$GIT_USER")
  else
    gap "user '$GIT_USER' does not exist"
  fi
fi

# ---------- git availability ----------
if command -v git >/dev/null 2>&1; then
  ok "git $(git --version | awk '{print $3}')"
else
  echo "FATAL: git not installed on target"; exit 2
fi

# ---------- D3a: home + .ssh skeleton ----------
if [ -d "$GIT_HOME" ]; then
  ok "$GIT_HOME exists"
else
  if [ "$MODE" = apply ]; then
    $SUDO mkdir -p "$GIT_HOME" && act "created $GIT_HOME"
  else
    gap "$GIT_HOME missing"
  fi
fi

SSHDIR="$GIT_HOME/.ssh"
AK="$SSHDIR/authorized_keys"

if [ "$MODE" = apply ]; then
  $SUDO mkdir -p "$SSHDIR"
  $SUDO touch "$AK"
  # sshd StrictModes: home and .ssh must not be group/world writable,
  # authorized_keys must be 600 and owned by the git user.
  $SUDO chown "$GIT_USER:$GIT_GROUP" "$GIT_HOME" "$SSHDIR" "$AK"
  $SUDO chmod 700 "$GIT_HOME" "$SSHDIR"
  $SUDO chmod 600 "$AK"
  ok "permissions: $GIT_HOME=700 $SSHDIR=700 authorized_keys=600 ($GIT_USER:$GIT_GROUP)"
else
  [ -d "$SSHDIR" ] && ok "$SSHDIR exists" || gap "$SSHDIR missing"
  [ -f "$AK" ] && ok "$AK exists" || gap "$AK missing"
  if [ -f "$AK" ]; then
    PERM=$(stat -c '%a %U:%G' "$AK" 2>/dev/null || stat -f '%Lp %Su:%Sg' "$AK" 2>/dev/null)
    ok "authorized_keys perms: $PERM"
  fi
fi

# ---------- D3b: authorize keys (dedup by fingerprint) ----------
if [ -f "$AK" ]; then
  EXISTING=$($SUDO ssh-keygen -lf "$AK" 2>/dev/null | awk '{print $2}' || true)
else
  EXISTING=""
fi

TO_ADD=()
for entry in ${KEY_PAYLOAD[@]+"${KEY_PAYLOAD[@]}"}; do
  FP="${entry%%|*}"
  REST="${entry#*|}"
  B64="${REST%%|*}"
  SRC="${REST#*|}"
  if printf '%s\n' "$EXISTING" | grep -qxF "$FP"; then
    ok "key already authorized: $FP ($SRC)"
  else
    TO_ADD+=("$B64")
    gap "key not authorized: $FP ($SRC)"
  fi
done

if [ ${#TO_ADD[@]} -gt 0 ] && [ "$MODE" = apply ]; then
  TMP=$(mktemp)
  $SUDO cp "$AK" "$TMP" 2>/dev/null || : > "$TMP"
  for b64 in "${TO_ADD[@]}"; do
    printf '%s\n' "$b64" | base64 -d >> "$TMP"
  done
  # install(1) writes atomically and re-applies owner+mode in one step
  $SUDO install -o "$GIT_USER" -g "$GIT_GROUP" -m 600 "$TMP" "$AK"
  rm -f "$TMP"
  act "authorized ${#TO_ADD[@]} key(s) into $AK"
fi

# ---------- D2: bare repositories ----------
if [ ${#REPOS[@]} -eq 0 ]; then
  ok "no --repo requested; user+keys only"
fi

# Ensure every path component between GIT_HOME and the repository directory is
# owned by the git user. `mkdir -p` runs under sudo, so without this the
# namespace directory is left root-owned: the repo itself works, but the git
# user can no longer create sibling repositories in that namespace.
chown_namespace_chain() {
  local chain="$1" p
  [ "$chain" = "$GIT_HOME" ] && return 0
  p="$chain"
  while [ "$p" != "$GIT_HOME" ] && [ "$p" != "/" ] && [ -n "$p" ]; do
    if [ -d "$p" ]; then
      OWNER=$(stat -c '%U:%G' "$p" 2>/dev/null || stat -f '%Su:%Sg' "$p" 2>/dev/null)
      if [ "$OWNER" != "$GIT_USER:$GIT_GROUP" ]; then
        # count the drift in both modes so the summary stays honest about what
        # this run actually changed (same convention as key authorization)
        gap "namespace dir owned by $OWNER, expected $GIT_USER:$GIT_GROUP: $p"
        if [ "$MODE" = apply ]; then
          $SUDO chown "$GIT_USER:$GIT_GROUP" "$p" && act "namespace owner $OWNER -> $GIT_USER:$GIT_GROUP  $p"
        fi
      else
        ok "namespace dir $p ($OWNER)"
      fi
    fi
    p=$(dirname "$p")
  done
}

for repo in ${REPOS[@]+"${REPOS[@]}"}; do
  DIR="$GIT_HOME/$repo.git"
  PARENT=$(dirname "$DIR")
  if [ -d "$DIR" ] && [ -f "$DIR/HEAD" ]; then
    chown_namespace_chain "$PARENT"
    HEAD_REF=$(cat "$DIR/HEAD" 2>/dev/null)
    ok "repo exists: $DIR (HEAD=$HEAD_REF)"
    if [ "$HEAD_REF" != "ref: refs/heads/$INIT_BRANCH" ]; then
      if [ "$MODE" = apply ]; then
        $SUDO git --git-dir="$DIR" symbolic-ref HEAD "refs/heads/$INIT_BRANCH" \
          && act "repo HEAD -> refs/heads/$INIT_BRANCH: $DIR"
      else
        gap "repo HEAD is '$HEAD_REF', expected 'ref: refs/heads/$INIT_BRANCH': $DIR"
      fi
    fi
    if [ "$MODE" = apply ]; then
      $SUDO chown -R "$GIT_USER:$GIT_GROUP" "$DIR"
    fi
  else
    if [ "$MODE" = apply ]; then
      $SUDO mkdir -p "$PARENT"
      chown_namespace_chain "$PARENT"
      # -b needs git >= 2.28; fall back to init + symbolic-ref on older targets
      if $SUDO git init --bare -b "$INIT_BRANCH" "$DIR" >/dev/null 2>&1; then
        :
      else
        $SUDO git init --bare "$DIR" >/dev/null 2>&1 \
          && $SUDO git --git-dir="$DIR" symbolic-ref HEAD "refs/heads/$INIT_BRANCH"
      fi
      $SUDO chown -R "$GIT_USER:$GIT_GROUP" "$DIR"
      act "created bare repo: $DIR (HEAD=refs/heads/$INIT_BRANCH)"
    else
      gap "bare repo missing: $DIR"
    fi
  fi
done

echo "== summary: mode=$MODE gaps=$GAPS"
if [ "$MODE" = check ]; then
  [ "$GAPS" -eq 0 ] && { echo "CONVERGED"; exit 0; } || { echo "NOT-CONVERGED"; exit 3; }
fi
[ "$GAPS" -eq 0 ] && echo "CONVERGED (nothing to do)" || echo "CONVERGED ($GAPS gap(s) closed)"
exit 0
REMOTE_EOF
)

REMOTE_FULL="${HEADER}"$'\n'"${BODY}"

if [ "$DRY_RUN" = true ]; then
  printf '%s\n' "$REMOTE_FULL"
  exit 0
fi

info "== executing on $HOST (mode=$MODE)"
printf '%s\n' "$REMOTE_FULL" | ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" 'bash -s'
