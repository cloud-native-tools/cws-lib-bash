#!/usr/bin/env python3
"""git-fleet engine — multi-environment git state collection and dependency graph.

Environment-agnostic by construction: every machine-specific fact (host names,
directory roots, transports) comes from an inventory file supplied by the caller.
This script contains no absolute paths and no host inventory of its own.

Subcommands:
  scan    collect git state + dependency evidence from every environment
  report  coordination matrix + hazard verdicts (+ incremental diff)
  plan    ordered coordination steps for one logical repo
  sync    execute SAFE writes only (fetch / ff-pull / backup branch / stash protect)
  deps    build the bidirectional dependency graph + per-project documents

The probe is strictly read-only (--no-optional-locks; never fetches).
Destructive and shared-state git operations are refused by construction.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# --- record schemas ----------------------------------------------------------

# One "R" line per checkout.
REPO_FIELDS = [
    "path", "branch", "upstream", "ahead", "behind", "tracked", "untracked",
    "stashes", "sha", "committed_at", "origin", "submodule_flags", "fetch_age",
    "superproject",
]
REPO_INT_FIELDS = {"ahead", "behind", "tracked", "untracked", "stashes", "fetch_age"}
# One "M" line per declared submodule (first-hand evidence: .gitmodules + gitlink).
SUB_FIELDS = ["path", "sub_path", "sub_url", "sub_branch", "sub_sha", "sub_state"]
# One "D" line per manifest line naming an internal origin (declared, not resolved).
DEP_FIELDS = ["path", "manifest", "line"]

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    "-o", "PasswordAuthentication=no",
    "-o", "PreferredAuthentications=publickey",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "RemoteCommand=none",
    "-o", "RequestTTY=no",
]

# Both are interpolated into a remote shell command line, so both are validated.
TARGET_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")
ROOT_RE = re.compile(r"\A[A-Za-z0-9._/+-]+\Z")
PATTERN_RE = re.compile(r"\A[A-Za-z0-9._/@:-]+\Z")

STALE_FETCH_SECONDS = 3 * 24 * 3600

DEFAULT_MANIFESTS = ["go.mod", "package.json", "pom.xml", "Cargo.toml", "pyproject.toml"]

# Never executed by this engine in any mode: shared-state writes and history
# rewrites stay with the user. `stash` is allowed so `stash push` can protect a
# dirty tree; the destructive stash verbs are refused by prefix below.
REFUSED_SUBCOMMANDS = frozenset({
    "push", "reset", "merge", "rebase", "checkout", "switch", "clean",
    "gc", "prune", "filter-branch", "cherry-pick", "revert", "am", "apply",
})
REFUSED_PREFIXES = ("stash drop", "stash clear", "stash pop", "stash apply",
                    "branch -D", "branch -d", "remote remove", "remote set-url",
                    "submodule update", "submodule deinit")

# Read-only probe. POSIX sh: runs identically on macOS and Linux hosts.
PROBE_SH = r"""
: "${ROOTS:=}"
: "${DEPTH:=4}"
: "${MANIFESTS:=}"
: "${PATTERNS:=}"
NOW=$(date +%s)

file_mtime() {
  stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

emit_repo() {
  r=$1
  gd=$(git -C "$r" rev-parse --git-dir 2>/dev/null) || return 0
  case "$gd" in /*) ;; *) gd="$r/$gd" ;; esac

  br=$(git -C "$r" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')
  up=$(git -C "$r" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo '')
  behind=0
  ahead=0
  if [ -n "$up" ]; then
    ab=$(git -C "$r" rev-list --left-right --count "$up...HEAD" 2>/dev/null || echo '')
    if [ -n "$ab" ]; then
      behind=$(printf '%s' "$ab" | cut -f1)
      ahead=$(printf '%s' "$ab" | cut -f2)
    fi
  fi

  st=$(git -C "$r" --no-optional-locks status --porcelain 2>/dev/null)
  untracked=$(printf '%s\n' "$st" | grep -c '^??' 2>/dev/null || true)
  allmod=$(printf '%s\n' "$st" | grep -c '[^[:space:]]' 2>/dev/null || true)
  tracked=$((allmod - untracked))
  [ "$tracked" -lt 0 ] && tracked=0

  stashes=$(git -C "$r" stash list 2>/dev/null | wc -l | tr -d ' ')

  hd=$(git -C "$r" log -1 --format='%H %cI' 2>/dev/null || echo '')
  sha=''
  cdate=''
  if [ -n "$hd" ]; then
    sha=${hd%% *}
    cdate=${hd#* }
  fi

  origin=$(git -C "$r" config --get remote.origin.url 2>/dev/null || echo '')
  sm=$(git -C "$r" submodule status 2>/dev/null | sed -n 's/^\([+-U]\).*/\1/p' | sort -u | tr -d '\n')
  sup=$(git -C "$r" rev-parse --show-superproject-working-tree 2>/dev/null || echo '')

  fage=-1
  if [ -f "$gd/FETCH_HEAD" ]; then
    fage=$((NOW - $(file_mtime "$gd/FETCH_HEAD")))
  fi

  printf 'R\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$r" "$br" "$up" "$ahead" "$behind" "$tracked" "$untracked" \
    "$stashes" "$sha" "$cdate" "$origin" "$sm" "$fage" "$sup"
}

# Submodule edges: .gitmodules declares path+url(+branch), the gitlink pins the sha.
emit_subs() {
  r=$1
  [ -f "$r/.gitmodules" ] || return 0
  git -C "$r" config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null |
  while read -r key spath; do
    [ -n "$spath" ] || continue
    base=${key%.path}
    surl=$(git -C "$r" config -f .gitmodules --get "$base.url" 2>/dev/null || echo '')
    sbr=$(git -C "$r" config -f .gitmodules --get "$base.branch" 2>/dev/null || echo '')
    line=$(git -C "$r" submodule status -- "$spath" 2>/dev/null | head -1)
    state=$(printf '%s' "$line" | cut -c1)
    case "$state" in ' '|'') state='ok' ;; esac
    ssha=$(printf '%s' "$line" | sed 's/^.//' | awk '{print $1}')
    [ -n "$ssha" ] || ssha=$(git -C "$r" ls-tree HEAD -- "$spath" 2>/dev/null | awk '$2=="commit"{print $3}')
    printf 'M\t%s\t%s\t%s\t%s\t%s\t%s\n' "$r" "$spath" "$surl" "$sbr" "$ssha" "$state"
  done
}

# Manifest-declared dependencies, filtered to caller-supplied internal patterns.
# Declared only -- never resolved to a repo here; the graph grades it accordingly.
emit_deps() {
  r=$1
  [ -n "$MANIFESTS" ] || return 0
  [ -n "$PATTERNS" ] || return 0
  for m in $MANIFESTS; do
    [ -f "$r/$m" ] || continue
    for p in $PATTERNS; do
      grep -F -- "$p" "$r/$m" 2>/dev/null | head -40 | while IFS= read -r l; do
        l=$(printf '%s' "$l" | tr '\t' ' ' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | cut -c1-200)
        [ -n "$l" ] || continue
        printf 'D\t%s\t%s\t%s\n' "$r" "$m" "$l"
      done
    done
  done
}

for root in $ROOTS; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth "$DEPTH" \
    \( -name node_modules -o -name .venv -o -name vendor -o -name target \) -prune -o \
    -name .git -prune -print 2>/dev/null
done | while IFS= read -r g; do
  r=$(dirname "$g")
  emit_repo "$r"
  emit_subs "$r"
  emit_deps "$r"
done
"""


# --- inventory ---------------------------------------------------------------

def require_yaml():
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")


def load_inventory(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(
            f"inventory not found: {path}\n"
            "This engine is environment-agnostic and cannot guess your machines.\n"
            "Supply an inventory (see references/inventory-schema.md)."
        )
    require_yaml()
    inv = yaml.safe_load(path.read_text(errors="replace")) or {}
    if not inv.get("envs"):
        raise SystemExit(f"inventory has no 'envs': {path}")
    return inv


def state_dir_for(inventory: Path, override: str | None) -> Path:
    d = Path(override) if override else inventory.parent
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- probe execution ---------------------------------------------------------

def parse_probe(stdout: str) -> dict:
    repos: list[dict] = []
    subs: list[dict] = []
    deps: list[dict] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        kind, rest = parts[0], parts[1:]
        if kind == "R" and len(rest) == len(REPO_FIELDS):
            rec = dict(zip(REPO_FIELDS, rest))
            for k in REPO_INT_FIELDS:
                try:
                    rec[k] = int(rec[k])
                except (TypeError, ValueError):
                    rec[k] = 0
            repos.append(rec)
        elif kind == "M" and len(rest) == len(SUB_FIELDS):
            subs.append(dict(zip(SUB_FIELDS, rest)))
        elif kind == "D" and len(rest) == len(DEP_FIELDS):
            deps.append(dict(zip(DEP_FIELDS, rest)))
    return {"repos": repos, "submodules": subs, "manifest_deps": deps}


def probe_env(name: str, spec: dict, inv: dict, timeout: int) -> dict:
    kind = spec.get("kind", "?")
    declared = spec.get("roots") or []
    bad = [r for r in declared if not ROOT_RE.match(str(r))]
    if bad:
        return {"status": "config-error", "kind": kind, "repos": [], "submodules": [],
                "manifest_deps": [], "error": f"unsafe root path(s) rejected: {bad}"}
    if not declared:
        return {"status": "config-error", "kind": kind, "repos": [], "submodules": [],
                "manifest_deps": [], "error": "no roots configured"}

    patterns = [p for p in (inv.get("internal_origin_patterns") or []) if PATTERN_RE.match(str(p))]
    manifests = [m for m in (inv.get("manifests") or DEFAULT_MANIFESTS) if ROOT_RE.match(str(m))]
    env_vars = {
        "ROOTS": " ".join(declared),
        "DEPTH": str(spec.get("depth", 4)),
        "MANIFESTS": " ".join(manifests),
        "PATTERNS": " ".join(patterns),
    }

    transport = spec.get("transport") or ("local" if name == "local" else "ssh")
    try:
        if transport == "local":
            proc = subprocess.run(["sh", "-s"], input=PROBE_SH, capture_output=True,
                                  text=True, timeout=timeout,
                                  env={**os.environ, **env_vars})
        elif transport == "ssh":
            target = spec.get("target") or name
            if not TARGET_RE.match(str(target)):
                return {"status": "config-error", "kind": kind, "repos": [], "submodules": [],
                        "manifest_deps": [], "error": f"unsafe ssh target rejected: {target!r}"}
            remote = " ".join(f"{k}={shlex.quote(v)}" for k, v in env_vars.items()) + " sh -s"
            proc = subprocess.run(["ssh", *SSH_OPTS, str(target), remote], input=PROBE_SH,
                                  capture_output=True, text=True, timeout=timeout)
        else:
            return {"status": "config-error", "kind": kind, "repos": [], "submodules": [],
                    "manifest_deps": [], "error": f"unknown transport {transport!r}"}
    except subprocess.TimeoutExpired:
        return {"status": "unreachable", "kind": kind, "repos": [], "submodules": [],
                "manifest_deps": [], "error": f"timeout after {timeout}s"}
    except OSError as exc:
        return {"status": "unreachable", "kind": kind, "repos": [], "submodules": [],
                "manifest_deps": [], "error": str(exc)}

    if proc.returncode != 0 and not proc.stdout.strip():
        return {"status": "unreachable", "kind": kind, "repos": [], "submodules": [],
                "manifest_deps": [],
                "error": (proc.stderr or "").strip()[:300] or f"exit {proc.returncode}"}
    return {"status": "ok", "kind": kind, **parse_probe(proc.stdout)}


# --- snapshots ---------------------------------------------------------------

def snapshots_dir(state: Path) -> Path:
    d = state / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_snapshots(state: Path) -> list[Path]:
    return sorted(snapshots_dir(state).glob("*.json"))


def latest_snapshot(state: Path, explicit: str | None) -> tuple[dict, Path]:
    if explicit:
        p = Path(explicit)
    else:
        snaps = list_snapshots(state)
        if not snaps:
            raise SystemExit("no snapshot yet — run: git_fleet.py scan")
        p = snaps[-1]
    return json.loads(p.read_text()), p


def cmd_scan(args) -> int:
    inv_path = Path(args.inventory)
    inv = load_inventory(inv_path)
    state = state_dir_for(inv_path, args.state_dir)
    envs = dict(inv["envs"])
    if args.envs:
        wanted = {e.strip() for e in args.envs.split(",") if e.strip()}
        missing = wanted - set(envs)
        if missing:
            print(f"unknown env(s): {sorted(missing)}", file=sys.stderr)
            return 2
        envs = {k: v for k, v in envs.items() if k in wanted}

    print(f"[scan] inventory={inv_path} envs={len(envs)} workers={args.jobs}", file=sys.stderr)
    results: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(probe_env, n, s, inv, args.timeout): n for n, s in envs.items()}
        for fut in concurrent.futures.as_completed(futs):
            name = futs[fut]
            try:
                results[name] = fut.result()
            except Exception as exc:  # one bad env must not kill the sweep
                results[name] = {"status": "error", "error": repr(exc), "repos": [],
                                 "submodules": [], "manifest_deps": []}
            r = results[name]
            print(f"  {name:<66} {r['status']:<13} repos={len(r['repos'])} "
                  f"subs={len(r.get('submodules', []))}"
                  + (f" ({(r.get('error') or '')[:70]})" if r.get("error") else ""),
                  file=sys.stderr)

    snap = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "inventory": str(inv_path),
        "envs": dict(sorted(results.items())),
    }
    out = Path(args.out) if args.out else snapshots_dir(state) / f"{datetime.now():%Y-%m-%dT%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n")
    ok = sum(1 for r in results.values() if r["status"] == "ok")
    print(f"[scan] wrote {out}  ({ok}/{len(results)} envs reachable, "
          f"{sum(len(r['repos']) for r in results.values())} checkouts)", file=sys.stderr)
    return 0


# --- identity & grouping -----------------------------------------------------

def norm_origin(url: str) -> str:
    """Normalize a git remote URL into a cross-environment / cross-repo join key."""
    u = (url or "").strip()
    if not u:
        return ""
    u = re.sub(r"\.git\Z", "", u)
    u = re.sub(r"\A[a-z+]+://", "", u)          # ssh:// https:// git://
    u = re.sub(r"\A[^@/]+@", "", u)             # user@
    if ":" in u.split("/")[0]:
        u = u.replace(":", "/", 1)              # scp-style host:path
    u = re.sub(r"/{2,}", "/", u)
    return u.strip("/").lower()


def group_checkouts(snap: dict) -> dict[str, list[dict]]:
    """Group checkouts of the same logical repo across environments.

    A submodule is keyed separately from a standalone clone of the same origin:
    its HEAD is pinned by its parent, so comparing the two yields noise rather
    than a coordination signal.
    """
    groups: dict[str, list[dict]] = {}
    for env, data in snap.get("envs", {}).items():
        for repo in data.get("repos", []):
            key = norm_origin(repo.get("origin", "")) or f"(no-origin) {Path(repo['path']).name}"
            sup = repo.get("superproject") or ""
            if sup:
                key = f"{key} ⊂{Path(sup).name}"
            groups.setdefault(key, []).append({**repo, "env": env})
    return groups


# --- hazard verdicts ---------------------------------------------------------

def verdicts(checkouts: list[dict]) -> list[tuple[str, str, str]]:
    """Return [(severity, code, detail)] for one logical repo across environments."""
    out: list[tuple[str, str, str]] = []
    dirty = [c for c in checkouts if c["tracked"] + c["untracked"] > 0]
    unpushed = [c for c in checkouts if c["ahead"] > 0]

    def tag(c: dict) -> str:
        return f"{c['env']}:{Path(c['path']).name}"

    def spans_envs(cos: list[dict]) -> bool:
        return len({c["env"] for c in cos}) >= 2

    if spans_envs(dirty):
        out.append(("P0", "MULTI_DIRTY", "未提交改动同时存在于 "
                    + ", ".join(f"{tag(c)}({c['tracked']}+{c['untracked']})" for c in dirty)))
    elif len(dirty) >= 2:
        out.append(("P3", "SAME_ENV_CLONES",
                    f"同一环境有 {len(dirty)} 份同源检出均为脏（并行克隆，非跨环境冲突）："
                    + ", ".join(tag(c) for c in dirty)))

    if len(unpushed) >= 2 and spans_envs(unpushed):
        branches = {c["branch"] for c in unpushed}
        sev, code = ("P0", "DIVERGENT_UNPUSHED") if len(branches) == 1 else ("P1", "PARALLEL_UNPUSHED")
        out.append((sev, code, "未推送提交并存于 "
                    + ", ".join(f"{tag(c)}:{c['branch']}+{c['ahead']}" for c in unpushed)))
    elif len(unpushed) == 1:
        c = unpushed[0]
        out.append(("P1", "UNPUSHED", f"{tag(c)} 有 {c['ahead']} 个提交只存在于该环境"))

    # HEAD divergence is fetch-independent evidence, but only across environments:
    # within one environment, differing clones are deliberate.
    by_branch: dict[str, list[dict]] = {}
    for c in checkouts:
        if c["sha"] and c["branch"] not in ("HEAD", "?", ""):
            by_branch.setdefault(c["branch"], []).append(c)
    for br, cos in by_branch.items():
        if len({c["sha"] for c in cos}) > 1 and spans_envs(cos):
            out.append(("P1", "HEAD_DIVERGED", f"分支 {br} 在各环境 HEAD 不同："
                        + ", ".join(f"{tag(c)}@{c['sha'][:8]}" for c in cos)))

    for c in checkouts:
        t = tag(c)
        if c["behind"] > 0 and c["tracked"] + c["untracked"] > 0:
            out.append(("P2", "BEHIND_DIRTY", f"{t} 落后 {c['behind']} 且工作区脏（需先保护再同步）"))
        elif c["behind"] > 0:
            out.append(("P3", "BEHIND", f"{t} 落后 {c['behind']}（可 ff 同步）"))
        if c["stashes"] > 0:
            out.append(("P2", "STASH", f"{t} 有 {c['stashes']} 条 stash（易遗忘的隐藏改动）"))
        if c["branch"] in ("HEAD", "?"):
            out.append(("P2", "DETACHED", f"{t} 处于 detached HEAD"))
        elif not c["upstream"]:
            out.append(("P3", "NO_UPSTREAM", f"{t} 分支 {c['branch']} 无 upstream"))
        if any(f in (c.get("submodule_flags") or "") for f in ("+", "U")):
            out.append(("P1", "SUBMODULE_DRIFT",
                        f"{t} 子模块 gitlink 与检出不一致 '{c['submodule_flags']}'"
                        "（编辑子模块交由 git-submodule-edit）"))
        if c["fetch_age"] < 0:
            out.append(("P3", "NEVER_FETCHED", f"{t} 从未 fetch，ahead/behind 不可信"))
        elif c["fetch_age"] > STALE_FETCH_SECONDS:
            out.append(("P3", "STALE_REFS",
                        f"{t} 上次 fetch 距今 {c['fetch_age'] // 86400}d，ahead/behind 不可信"))
    return out


def diff_snapshots(prev: dict, cur: dict) -> list[str]:
    def index(snap):
        return {(env, r["path"]): r
                for env, data in snap.get("envs", {}).items()
                for r in data.get("repos", [])}

    pi, ci = index(prev), index(cur)
    lines = []
    for key in sorted(set(ci) | set(pi)):
        env, path = key
        a, b = pi.get(key), ci.get(key)
        name = f"{env}:{path}"
        if b and not a:
            lines.append(f"+ 新增检出 {name}")
        elif a and not b:
            lines.append(f"- 消失 {name}（环境不可达或已删除）")
        else:
            ch = []
            if a["sha"] != b["sha"]:
                ch.append(f"HEAD {a['sha'][:8] or '-'}→{b['sha'][:8] or '-'}")
            if a["branch"] != b["branch"]:
                ch.append(f"branch {a['branch']}→{b['branch']}")
            da, db = a["tracked"] + a["untracked"], b["tracked"] + b["untracked"]
            if da != db:
                ch.append(f"脏文件 {da}→{db}")
            for f in ("ahead", "behind"):
                if a[f] != b[f]:
                    ch.append(f"{f} {a[f]}→{b[f]}")
            if ch:
                lines.append(f"~ {name}: " + ", ".join(ch))
    return lines


def cmd_report(args) -> int:
    inv_path = Path(args.inventory)
    state = state_dir_for(inv_path, args.state_dir)
    cur, cur_path = latest_snapshot(state, args.snapshot)
    groups = group_checkouts(cur)

    scored = []
    for key, cos in groups.items():
        if args.repo and args.repo.lower() not in key.lower():
            continue
        vs = verdicts(cos)
        scored.append((min((v[0] for v in vs), default="P9"), key, cos, vs))
    scored.sort(key=lambda t: (t[0], t[1]))

    envs = cur.get("envs", {})
    ok = [e for e, d in envs.items() if d["status"] == "ok"]
    bad = {e: d for e, d in envs.items() if d["status"] != "ok"}
    lines = [f"# git 协调报告 — {cur.get('generated_at', '?')}", "",
             f"- 快照：`{cur_path}`",
             f"- 环境：{len(ok)}/{len(envs)} 可达，共 "
             f"{sum(len(d['repos']) for d in envs.values())} 个检出，{len(groups)} 个逻辑仓库", ""]

    if bad:
        lines.append("## 不可达环境（沿用上次已知状态）")
        snaps = list_snapshots(state)
        prior: dict[str, tuple[str, int]] = {}
        for old in reversed(snaps):
            if old == cur_path:
                continue
            o = json.loads(old.read_text())
            for e, d in o.get("envs", {}).items():
                if e in bad and e not in prior and d["status"] == "ok":
                    prior[e] = (o.get("generated_at", "?"), len(d["repos"]))
        for e, d in sorted(bad.items()):
            note = (f"上次可达 {prior[e][0]}，{prior[e][1]} 个检出" if e in prior else "无历史快照")
            lines.append(f"- `{e}` — {d['status']}：{(d.get('error') or '')[:100]} · {note}")
        lines.append("")

    flagged = [s for s in scored if s[3]]
    lines.append(f"## 需协调的仓库（{len(flagged)}）")
    if not flagged:
        lines += ["", "全部一致，无需协调。"]
    for worst, key, cos, vs in flagged:
        lines += ["", f"### [{worst}] {key}", "",
                  "| 环境 | 路径 | 分支 | 脏(改/未跟踪) | ahead/behind | stash | HEAD |",
                  "|---|---|---|---|---|---|---|"]
        for c in sorted(cos, key=lambda x: x["env"]):
            lines.append(f"| {c['env']} | `{c['path']}` | {c['branch']} | "
                         f"{c['tracked']}/{c['untracked']} | {c['ahead']}/{c['behind']} | "
                         f"{c['stashes']} | {c['sha'][:8] or '-'} |")
        lines.append("")
        lines += [f"- **{sev} {code}** — {detail}" for sev, code, detail in sorted(vs)]

    if args.diff and not args.snapshot:
        snaps = list_snapshots(state)
        if len(snaps) >= 2:
            prev = json.loads(snaps[-2].read_text())
            lines += ["", f"## 与上次快照的增量（{prev.get('generated_at', '?')}）", ""]
            lines += diff_snapshots(prev, cur) or ["无变化。"]

    text = "\n".join(lines) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"[report] wrote {out}", file=sys.stderr)
    else:
        print(text)
    return 10 if flagged else 0


# --- coordination plan / safe sync -------------------------------------------

def build_plan(cos: list[dict]) -> list[tuple[str, str, str]]:
    """Ordered [(gate, env, command)] steps. gate is SAFE or GATED.

    Unique work lands first: commits that exist in exactly one environment must
    reach the shared remote before any other environment moves.
    """
    steps: list[tuple[str, str, str]] = []
    for c in sorted(cos, key=lambda x: x["env"]):
        steps.append(("SAFE", c["env"], f"git -C {shlex.quote(c['path'])} fetch --all --prune"))

    dirty = [c for c in cos if c["tracked"] + c["untracked"] > 0]
    unpushed = [c for c in cos if c["ahead"] > 0]

    for c in sorted(unpushed, key=lambda x: -x["ahead"]):
        if c in dirty:
            steps.append(("GATED", c["env"],
                          f"# 先审阅并提交脏改动：git -C {shlex.quote(c['path'])} status"))
        steps.append(("GATED", c["env"],
                      f"git -C {shlex.quote(c['path'])} push  # 共享状态写入，需确认"))
    for c in dirty:
        if c not in unpushed:
            steps.append(("GATED", c["env"],
                          f"# 审阅未提交改动：git -C {shlex.quote(c['path'])} status --porcelain"))

    for c in sorted(cos, key=lambda x: x["env"]):
        q = shlex.quote(c["path"])
        if c["behind"] > 0 and c["ahead"] == 0:
            if c["tracked"] + c["untracked"] > 0:
                steps.append(("SAFE", c["env"], f"git -C {q} stash push -u -m git-fleet"))
            steps.append(("SAFE", c["env"], f"git -C {q} pull --ff-only"))
        elif c["behind"] > 0 and c["ahead"] > 0:
            steps.append(("GATED", c["env"],
                          f"# 真分叉（ahead {c['ahead']}/behind {c['behind']}）：交由 git-workflow 决策"))
    return steps


def cmd_plan(args) -> int:
    inv_path = Path(args.inventory)
    state = state_dir_for(inv_path, args.state_dir)
    cur, _ = latest_snapshot(state, args.snapshot)
    hits = {k: v for k, v in group_checkouts(cur).items() if args.repo.lower() in k.lower()}
    if not hits:
        print(f"no logical repo matches {args.repo!r}", file=sys.stderr)
        return 2
    for key, cos in sorted(hits.items()):
        print(f"\n## {key}")
        for gate, env, cmd in build_plan(cos):
            print(f"  [{gate:<5}] {env:<50} {cmd}")
    print("\nSAFE 步骤可由 `sync --apply` 执行；GATED 步骤必须由你确认后执行。")
    return 0


def run_git(target: str, transport: str, path: str, gitargs: list[str],
            apply: bool, timeout: int) -> tuple[int, str]:
    joined = " ".join(gitargs)
    subcmd = gitargs[0] if gitargs else ""
    if subcmd in REFUSED_SUBCOMMANDS or any(joined.startswith(p) for p in REFUSED_PREFIXES):
        return 99, f"REFUSED（超出安全写边界，需人工确认）: git {joined}"
    if not ROOT_RE.match(path):
        return 99, f"REFUSED (unsafe path): {path}"
    cmd = ["git", "-C", path, *gitargs]
    if not apply:
        return 0, "DRY-RUN " + (f"ssh {target} " if transport == "ssh" else "") + " ".join(cmd)
    if transport == "local":
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    else:
        if not TARGET_RE.match(target):
            return 99, f"REFUSED (unsafe ssh target): {target}"
        proc = subprocess.run(["ssh", *SSH_OPTS, target,
                               " ".join(shlex.quote(c) for c in cmd)],
                              capture_output=True, text=True, timeout=timeout)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()[:400]


def cmd_sync(args) -> int:
    inv_path = Path(args.inventory)
    inv = load_inventory(inv_path)
    state = state_dir_for(inv_path, args.state_dir)
    cur, _ = latest_snapshot(state, None)
    groups = group_checkouts(cur)
    if args.repo:
        groups = {k: v for k, v in groups.items() if args.repo.lower() in k.lower()}
        if not groups:
            print(f"no logical repo matches {args.repo!r}", file=sys.stderr)
            return 2

    def route(env: str) -> tuple[str, str]:
        spec = inv["envs"].get(env, {})
        transport = spec.get("transport") or ("local" if env == "local" else "ssh")
        return transport, str(spec.get("target") or env)

    print(f"[sync] {'APPLY' if args.apply else 'DRY-RUN'} — "
          "仅执行 SAFE 步骤（fetch / 备份分支 / stash 保护 / ff-pull）\n")
    failures = 0
    for key, cos in sorted(groups.items()):
        plan = [s for s in build_plan(cos) if s[0] == "SAFE"]
        if not plan:
            continue
        print(f"## {key}")
        for _gate, env, cmd in plan:
            argv = shlex.split(cmd)
            path, gitargs = argv[2], argv[3:]
            transport, target = route(env)
            if gitargs[:1] == ["pull"] and args.backup:
                stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
                rc, out = run_git(target, transport, path,
                                  ["branch", f"fleet-backup/{stamp}", "HEAD"],
                                  args.apply, args.timeout)
                print(f"  [{'ok' if rc == 0 else 'ERR'}] {env}: backup branch — {out}")
            rc, out = run_git(target, transport, path, gitargs, args.apply, args.timeout)
            failures += rc != 0
            print(f"  [{'ok' if rc == 0 else 'ERR'}] {env}: {' '.join(gitargs)} — {out}")
        print()
    print(f"[sync] done, {failures} failure(s)."
          + ("" if args.apply else "  加 --apply 才会真正执行。"))
    return 10 if failures else 0


# --- dependency graph --------------------------------------------------------

EVIDENCE_MEASURED = "实测"
EVIDENCE_SEMI = "半实测"


def build_graph(snap: dict) -> dict:
    """Build the bidirectional inter-repo dependency graph from probe evidence.

    Evidence grading follows the project convention: an edge is only recorded when
    it was actually observed. `submodule` edges are 实测 (declared in .gitmodules
    AND pinned by a gitlink); `manifest` edges are 半实测 (declared in a manifest,
    not resolved to a checkout). Nothing is inferred from names or descriptions.
    """
    # path -> logical key, per environment, so edges can be resolved locally.
    path_key: dict[tuple[str, str], str] = {}
    nodes: dict[str, dict] = {}
    for env, data in snap.get("envs", {}).items():
        for r in data.get("repos", []):
            key = norm_origin(r.get("origin", "")) or f"(no-origin) {Path(r['path']).name}"
            sup = r.get("superproject") or ""
            display = key
            if sup:
                display = f"{key} ⊂{Path(sup).name}"
            path_key[(env, r["path"])] = display
            node = nodes.setdefault(key, {"key": key, "checkouts": [], "origin": r.get("origin", "")})
            node["checkouts"].append({"env": env, "path": r["path"], "branch": r["branch"],
                                      "sha": r["sha"], "submodule_of": sup})

    edges: list[dict] = []
    seen: set[tuple] = set()

    for env, data in snap.get("envs", {}).items():
        for m in data.get("submodules", []):
            parent = norm_origin(
                next((r.get("origin", "") for r in data.get("repos", [])
                      if r["path"] == m["path"]), ""))
            child = norm_origin(m.get("sub_url", ""))
            if not parent or not child:
                continue
            sig = ("submodule", parent, child, m.get("sub_path", ""))
            if sig in seen:
                continue
            seen.add(sig)
            edges.append({
                "type": "submodule", "evidence": EVIDENCE_MEASURED,
                "from": parent, "to": child,
                "mount_path": m.get("sub_path", ""),
                "pinned_branch": m.get("sub_branch", ""),
                "pinned_sha": m.get("sub_sha", ""),
                "state": m.get("sub_state", ""),
                "observed_in": env,
            })

        for d in data.get("manifest_deps", []):
            parent = norm_origin(
                next((r.get("origin", "") for r in data.get("repos", [])
                      if r["path"] == d["path"]), ""))
            if not parent:
                continue
            sig = ("manifest", parent, d.get("manifest", ""), d.get("line", ""))
            if sig in seen:
                continue
            seen.add(sig)
            edges.append({
                "type": "manifest", "evidence": EVIDENCE_SEMI,
                "from": parent, "to": None,
                "manifest": d.get("manifest", ""),
                "declared": d.get("line", ""),
                "observed_in": env,
            })

    # Resolve manifest edges to known nodes when the declaration names one.
    # A repo naming its OWN origin (go.mod `module`, package.json repository.url)
    # is a self-declaration, not a dependency: such edges are dropped.
    for e in edges:
        if e["type"] != "manifest" or e["to"]:
            continue
        decl = (e.get("declared") or "").lower()
        best = None
        for key in nodes:
            if key and key in decl:
                if best is None or len(key) > len(best):
                    best = key
        e["to"] = best
    edges = [e for e in edges
             if not (e["type"] == "manifest" and e["to"] == e["from"])]

    for key in nodes:
        nodes[key]["depends_on"] = []
        nodes[key]["depended_on_by"] = []
    for e in edges:
        if e["from"] in nodes:
            nodes[e["from"]]["depends_on"].append(e)
        if e["to"] and e["to"] in nodes:
            nodes[e["to"]]["depended_on_by"].append(e)

    return {"generated_at": snap.get("generated_at"), "nodes": nodes, "edges": edges}


def topo_order(graph: dict) -> tuple[list[str], list[list[str]]]:
    """Dependency-first order (a repo appears after everything it depends on)."""
    nodes = graph["nodes"]
    deps = {k: {e["to"] for e in n["depends_on"] if e["to"] in nodes} for k, n in nodes.items()}
    order: list[str] = []
    done: set[str] = set()
    while True:
        ready = sorted(k for k in nodes if k not in done and deps[k] <= done)
        if not ready:
            break
        order.extend(ready)
        done.update(ready)
    cycles = sorted(set(nodes) - done)
    return order, [cycles] if cycles else []


def cmd_deps(args) -> int:
    inv_path = Path(args.inventory)
    state = state_dir_for(inv_path, args.state_dir)
    cur, cur_path = latest_snapshot(state, args.snapshot)
    graph = build_graph(cur)

    gpath = state / "dependency-graph.json"
    gpath.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n")
    print(f"[deps] wrote {gpath}", file=sys.stderr)

    order, cycles = topo_order(graph)
    nodes = graph["nodes"]
    sub_edges = [e for e in graph["edges"] if e["type"] == "submodule"]
    man_edges = [e for e in graph["edges"] if e["type"] == "manifest"]
    print(f"[deps] {len(nodes)} 个仓库，{len(sub_edges)} 条 submodule 边（实测），"
          f"{len(man_edges)} 条 manifest 边（半实测）", file=sys.stderr)
    if cycles:
        print(f"[deps] WARNING 检测到依赖环，未能拓扑排序：{cycles}", file=sys.stderr)

    if args.docs:
        docs = state / "projects"
        docs.mkdir(parents=True, exist_ok=True)
        written = 0
        for key, node in sorted(nodes.items()):
            if args.repo and args.repo.lower() not in key.lower():
                continue
            (docs / (re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("_") + ".md")).write_text(
                render_project_doc(key, node, graph, cur_path, args.cross_reference, docs))
            written += 1
        print(f"[deps] wrote {written} 个项目说明文档到 {docs}", file=sys.stderr)

    if not args.docs:
        print(f"\n## 依赖优先顺序（{len(order)}）\n")
        for i, k in enumerate(order, 1):
            n = nodes[k]
            print(f"{i:3}. {k}  (依赖 {len(n['depends_on'])} / 被依赖 {len(n['depended_on_by'])})")
    return 0


def render_project_doc(key: str, node: dict, graph: dict, snap_path: Path,
                       cross_ref: str | None, docs_dir: Path | None = None) -> str:
    """Per-project document with BOTH dependency directions stored explicitly."""
    lines = [f"# {key}", "",
             "> 本文档由 git-fleet `deps` 子命令从**工作区一手证据**生成"
             "（`.gitmodules` + gitlink + manifest 声明）。",
             f"> 证据快照：`{snap_path.name}` · 生成于 {graph.get('generated_at', '?')}",
             "> 证据分级：实测（.gitmodules 声明且 gitlink 锁定）/ 半实测（manifest 声明未解析到检出）。",
             "> **无证据不入图**——不依据仓库命名或描述推断依赖。", ""]
    if cross_ref:
        segs = [s for s in key.split("/") if s]
        resolved = cross_ref.replace("{group}", segs[-2] if len(segs) >= 2 else "")
        # Only cite a curated view that exists; most groups have none.
        target = re.search(r"`([^`]+)`", resolved)
        exists = True
        if target and docs_dir is not None:
            exists = (docs_dir / target.group(1)).exists()
        if exists:
            lines += [f"> 人工策展的更丰富关系视图见：{resolved}", ""]

    lines += ["## 检出位置", "",
              "| 环境 | 路径 | 分支 | HEAD | 形态 |", "|---|---|---|---|---|"]
    for c in sorted(node["checkouts"], key=lambda x: (x["env"], x["path"])):
        form = f"子模块 ⊂ {Path(c['submodule_of']).name}" if c["submodule_of"] else "独立检出"
        lines.append(f"| {c['env']} | `{c['path']}` | {c['branch']} | {c['sha'][:8] or '-'} | {form} |")

    lines += ["", "## 依赖（本项目依赖的项目）", ""]
    dep = node["depends_on"]
    if not dep:
        lines.append("无已取证的对外依赖。")
    else:
        lines += ["| 被依赖项目 | 类型 | 证据 | 挂载路径 | 锁定分支 | 锁定 commit |",
                  "|---|---|---|---|---|---|"]
        for e in sorted(dep, key=lambda x: (x["type"], x.get("to") or "")):
            if e["type"] == "submodule":
                lines.append(f"| {e['to']} | submodule | {e['evidence']} | "
                             f"`{e['mount_path']}` | {e['pinned_branch'] or '-'} | "
                             f"{(e['pinned_sha'] or '')[:8] or '-'} |")
            else:
                lines.append(f"| {e['to'] or '（未解析）'} | manifest:{e['manifest']} | "
                             f"{e['evidence']} | - | - | `{e['declared'][:60]}` |")

    lines += ["", "## 被依赖（依赖本项目的项目）", ""]
    rev = node["depended_on_by"]
    if not rev:
        lines.append("无已取证的下游消费方。")
    else:
        lines += ["| 消费方项目 | 类型 | 证据 | 挂载路径 | 锁定 commit |",
                  "|---|---|---|---|---|"]
        for e in sorted(rev, key=lambda x: (x["type"], x["from"])):
            if e["type"] == "submodule":
                lines.append(f"| {e['from']} | submodule | {e['evidence']} | "
                             f"`{e['mount_path']}` | {(e['pinned_sha'] or '')[:8] or '-'} |")
            else:
                lines.append(f"| {e['from']} | manifest:{e['manifest']} | {e['evidence']} | - | - |")
        lines += ["", "> 改动本项目前先看这张表：它就是 git-submodule-edit 要求 PR "
                  "「列出受影响消费方」的数据源。"]
    return "\n".join(lines) + "\n"


# --- cli ---------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inventory", default=os.environ.get("GIT_FLEET_INVENTORY"),
                   help="environment inventory YAML (or $GIT_FLEET_INVENTORY)")
    p.add_argument("--state-dir", default=os.environ.get("GIT_FLEET_STATE"),
                   help="where snapshots/reports/graph live (default: inventory's directory)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="collect state + dependency evidence from every environment")
    s.add_argument("--envs", help="comma-separated env subset")
    s.add_argument("--jobs", type=int, default=8)
    s.add_argument("--timeout", type=int, default=90)
    s.add_argument("--out")
    s.set_defaults(func=cmd_scan)

    r = sub.add_parser("report", help="coordination matrix + hazard verdicts")
    r.add_argument("--snapshot")
    r.add_argument("--repo", help="filter by logical repo substring")
    r.add_argument("--out")
    r.add_argument("--diff", action="store_true", help="append incremental diff vs previous snapshot")
    r.set_defaults(func=cmd_report)

    pl = sub.add_parser("plan", help="ordered coordination steps for one repo")
    pl.add_argument("repo")
    pl.add_argument("--snapshot")
    pl.set_defaults(func=cmd_plan)

    sy = sub.add_parser("sync", help="execute SAFE steps only (dry-run unless --apply)")
    sy.add_argument("--repo")
    sy.add_argument("--apply", action="store_true")
    sy.add_argument("--no-backup", dest="backup", action="store_false", default=True)
    sy.add_argument("--timeout", type=int, default=120)
    sy.set_defaults(func=cmd_sync)

    dp = sub.add_parser("deps", help="dependency graph + per-project documents")
    dp.add_argument("--snapshot")
    dp.add_argument("--repo", help="limit generated docs to matching repos")
    dp.add_argument("--docs", action="store_true", help="write per-project documents")
    dp.add_argument("--cross-reference", help="link to a curated relations view, cited in each doc")
    dp.set_defaults(func=cmd_deps)

    args = p.parse_args()
    if not args.inventory:
        p.error("--inventory is required (or set $GIT_FLEET_INVENTORY)")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
