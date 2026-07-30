#!/usr/bin/env python3
"""evidence-utils.py — deterministic evidence-lane orchestrator for Spec Kit.

Spec 034 / Feature 038. Contracts: contracts/evidence-utils-cli.md (C-E1..C-E11)
and contracts/findings-contract.md (C-F1..C-F14).

Five lanes: session/project/assets (Node engine subprocess, argv-array, no shell)
and runs/feedback (native Python). Zero network. Stdlib only.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 1
FINDINGS_KIND = "speckit.evidence-findings"
SEVEN_STATES = (
    "Present", "Wired", "Exercised", "Outcome-supported",
    "Missing", "Unobserved", "Not applicable",
)
LANE_NAMES = ("session", "project", "assets", "runs", "feedback")
NODE_LANES = ("session", "project", "assets")
LANE_AVAILABLE = "available"
LANE_PARTIAL = "partial"
LANE_UNAVAILABLE = "unavailable"
TARGET_RE = re.compile(r"^(skill:[a-z0-9._-]+|/speckit\.[a-z0-9._-]+|project)$")
EVIDENCE_SUBDIR = Path(".specify") / "memory" / "evidence"
ENGINE_SUBSET_REL = Path("scripts") / "js" / "better-harness"
ENGINE_SUBSET_MIRROR_REL = Path(".specify") / "scripts" / "js" / "better-harness"
NODE_TIMEOUT_SECONDS = 120
DEFAULT_MAX_AGE_DAYS = 7
NODE_ENGINE_FLOOR = (22, 20, 0)
NODE_ENGINE_CEILING_MAJOR = 25
UPSTREAM_COMMIT = "b2e621d"
PLATFORM_SESSION_STORES = {
    "qoder": "~/.qoder/projects",
    "codex": "~/.codex/sessions",
    "claude": "~/.claude/projects",
    "copilot": "~/.copilot/session-state",
    "opencode": "~/.local/share/opencode",
    "qwen": "~/.qwen/tmp",
    "hermes": "~/.hermes/sessions",
    "iflow": "~/.iflow/tmp",
}
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]
HOME_PATH_RE = re.compile(r"(/home/[^\s\"']+|/Users/[^\s\"']+|[A-Z]:\\\\[^\s\"']+)")


# --- workspace & storage helpers ---------------------------------------------

def resolve_workspace_root(explicit):
    if explicit:
        return Path(explicit).resolve()
    current = Path.cwd()
    for candidate in (current, *current.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return current


def evidence_dir(root: Path) -> Path:
    return root / EVIDENCE_SUBDIR


def index_path(root: Path) -> Path:
    return evidence_dir(root) / "index.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_text_atomic(path: Path, text: str) -> None:
    """Atomic file write (.part + os.replace) — adopted from export-session's zip commit."""
    tmp = path.with_name(path.name + ".part")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def target_slug(target: str) -> str:
    slug = target.split(":", 1)[-1].lstrip("/").replace("speckit.", "")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    return slug or "project"


def make_run_id(target: str, now: datetime, store: Path = None) -> str:
    base = f"ev-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{target_slug(target)}"
    if store is None or not (store / base).exists():
        return base
    counter = 2
    while (store / f"{base}-{counter}").exists():
        counter += 1
    return f"{base}-{counter}"


def load_index(root: Path) -> dict:
    path = index_path(root)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("entries"), list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return rebuild_index(root)


def rebuild_index(root: Path) -> dict:
    entries = []
    store = evidence_dir(root)
    if store.is_dir():
        for run_dir in sorted(store.iterdir()):
            findings_file = run_dir / "findings.json"
            if not findings_file.is_file():
                continue
            try:
                findings = json.loads(findings_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            manifest_file = run_dir / "manifest.json"
            created = ""
            if manifest_file.is_file():
                try:
                    created = json.loads(manifest_file.read_text(encoding="utf-8")).get("created", "")
                except (json.JSONDecodeError, OSError):
                    created = ""
            entries.append({
                "runId": findings.get("runId", run_dir.name),
                "target": findings.get("target", ""),
                "created": created,
                "lanesSummary": {k: v.get("status", "") for k, v in findings.get("lanes", {}).items()},
                "file": str(Path(run_dir.name) / "findings.json"),
            })
    return {"store": "evidence", "updated": iso(utc_now()), "entries": entries}


def save_index(root: Path, index: dict) -> None:
    index["updated"] = iso(utc_now())
    evidence_dir(root).mkdir(parents=True, exist_ok=True)
    index_path(root).write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --- redaction ----------------------------------------------------------------

def redact_text(value: str, root: Path) -> str:
    text = value.replace(str(root), ".")
    home = str(Path.home())
    text = text.replace(home, "~")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED-SECRET]", text)
    text = HOME_PATH_RE.sub("[REDACTED-PATH]", text)
    return text


def redact_deep(node, root: Path):
    if isinstance(node, dict):
        return {k: redact_deep(v, root) for k, v in node.items()}
    if isinstance(node, list):
        return [redact_deep(v, root) for v in node]
    if isinstance(node, str):
        return redact_text(node, root)
    return node


def compute_digest(evidence: list) -> str:
    canonical = json.dumps(evidence, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- node probing ---------------------------------------------------------------

def probe_node() -> dict:
    from shutil import which
    node_bin = which("node")
    if not node_bin:
        return {"available": False, "satisfies": False}
    try:
        proc = subprocess.run([node_bin, "--version"], capture_output=True, text=True, timeout=15)
        version = proc.stdout.strip().lstrip("v")
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "satisfies": False}
    parts = tuple(int(p) for p in version.split(".")[:3] if p.isdigit())
    satisfies = bool(parts) and parts >= NODE_ENGINE_FLOOR and parts[0] < NODE_ENGINE_CEILING_MAJOR
    return {"available": True, "version": version, "satisfies": satisfies}


def engine_subset_path(root: Path):
    for rel in (ENGINE_SUBSET_REL, ENGINE_SUBSET_MIRROR_REL):
        candidate = root / rel
        if (candidate / "session-analysis.mjs").is_file():
            return candidate
    return None


SESSION_FILE_SUFFIXES = (".jsonl", ".json", ".db", ".sqlite")


def probe_session_store(store: str) -> str:
    """Three-state probe (P7-a): directory existence alone is not evidence of sessions."""
    base = Path(os.path.expanduser(store))
    if not base.exists():
        return "not-detected"
    try:
        stack = [base]
        depth = {base: 0}
        while stack:
            current = stack.pop()
            for entry in current.iterdir():
                if entry.is_file() and entry.suffix in SESSION_FILE_SUFFIXES:
                    return "detected"
                if entry.is_dir() and depth[current] < 3:
                    depth[entry] = depth[current] + 1
                    stack.append(entry)
    except OSError:
        return "detected-empty"
    return "detected-empty"


def probe_platforms() -> dict:
    platforms = {}
    for name, store in PLATFORM_SESSION_STORES.items():
        platforms[name] = {"sessionStore": probe_session_store(store)}
    return platforms


# --- doctor ----------------------------------------------------------------------

def action_doctor(args) -> dict:
    root = resolve_workspace_root(args.workspace_root)
    node = probe_node()
    subset = engine_subset_path(root)
    node_ok = node["available"] and subset is not None
    lanes = {}
    for lane in NODE_LANES:
        if not node["available"]:
            lanes[lane] = {"status": LANE_UNAVAILABLE, "reason": "node not available"}
        elif subset is None:
            lanes[lane] = {"status": LANE_UNAVAILABLE, "reason": "engine subset not found"}
        else:
            lanes[lane] = {"status": LANE_AVAILABLE}
    lanes["runs"] = (
        {"status": LANE_AVAILABLE} if (root / ".specify" / "teams").is_dir()
        else {"status": LANE_UNAVAILABLE, "reason": "no .specify/teams directory"})
    lanes["feedback"] = (
        {"status": LANE_AVAILABLE} if (root / ".specify" / "memory" / "feedback").is_dir()
        else {"status": LANE_UNAVAILABLE, "reason": "no .specify/memory/feedback directory"})
    return {
        "node": node,
        "engineSubset": {
            "present": subset is not None,
            "path": str(subset.relative_to(root)) if subset else None,
            "upstreamCommit": UPSTREAM_COMMIT if subset else None,
        },
        "platforms": probe_platforms(),
        "lanes": lanes,
        "nodeLanesOperational": node_ok,
    }


# --- node lane runners --------------------------------------------------------------

def run_node(subset: Path, root: Path, argv: list):
    cmd = ["node", *argv]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(root),
        timeout=NODE_TIMEOUT_SECONDS, shell=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{argv[0]} exited {proc.returncode}: {proc.stderr[:400]}")
    return json.loads(proc.stdout)


def collect_session_lane(subset: Path, root: Path, args) -> tuple:
    platform = (args.platform or "qoder").split(",")[0]
    argv = [str(subset / "session-analysis.mjs"), "facts",
            "--platform", platform, "--workspace", str(root), "--format", "json"]
    if args.since:
        argv += ["--since", args.since]
    if args.until:
        argv += ["--until", args.until]
    envelope = run_node(subset, root, argv)
    items = []
    admission = envelope.get("admission", {})
    episodes = admission.get("taskEpisodes", 0)
    candidates = envelope.get("candidates", [])
    if episodes == 0 and not candidates:
        items.append({
            "lane": "session",
            "evidenceState": "Unobserved",
            "summary": f"No eligible {platform} sessions observed for this workspace in the window.",
            "evidenceRefs": [],
            "signals": {"eligibleSessions": envelope.get("scope", {}).get("eligibleSessions", 0)},
            "privacyNote": "redacted-semantic-facet",
        })
    else:
        corrections = sum(
            1 for c in candidates
            if isinstance(c, dict) and c.get("workTrace", {}).get("userCorrections"))
        items.append({
            "lane": "session",
            "evidenceState": "Exercised",
            "summary": f"{episodes} task episode(s) observed on {platform}; "
                       f"{len(candidates)} candidate(s) admitted, {corrections} with user corrections.",
            "evidenceRefs": [c.get("ref", "") for c in candidates if isinstance(c, dict) and c.get("ref")][:8],
            "signals": {
                "taskEpisodes": episodes,
                "candidates": len(candidates),
                "userCorrections": corrections,
            },
            "privacyNote": "redacted-semantic-facet",
        })
    return items, envelope


def collect_project_lane(subset: Path, root: Path, args) -> tuple:
    profile = run_node(subset, root, [str(subset / "core-change-watch" / "project-profile.mjs"), "--json"])
    history = run_node(subset, root, [str(subset / "core-change-watch" / "git-history-profile.mjs"), "--json"])
    envelope = {"projectProfile": profile, "gitHistoryProfile": history}
    languages = profile.get("projectInfo", {}).get("primaryLanguages", [])
    lang_names = [l.get("language", "?") for l in languages[:3]]
    items = [{
        "lane": "project",
        "evidenceState": "Present",
        "summary": "Project profile captured: primary languages "
                   f"{', '.join(lang_names) or 'unknown'}; git history signals collected.",
        "evidenceRefs": ["core-change-watch/project-profile", "core-change-watch/git-history-profile"],
        "signals": {
            "primaryLanguages": len(languages),
            "sourceFiles": sum(l.get("sourceFiles", 0) for l in languages),
            "testFiles": sum(l.get("testFiles", 0) for l in languages),
        },
    }]
    if args.depth == "normal":
        try:
            dep = run_node(subset, root, [str(subset / "dependency-governance" / "cli.mjs"), "--json"])
            envelope["dependencyGovernance"] = dep
            summary = dep.get("summary", {})
            items.append({
                "lane": "project",
                "evidenceState": "Present",
                "summary": f"Dependency governance: {summary.get('ecosystemCount', 0)} ecosystem(s), "
                           f"risk level {summary.get('riskLevel', 'unknown')}.",
                "evidenceRefs": ["dependency-governance/cli"],
                "signals": {
                    "ecosystems": summary.get("ecosystemCount", 0) or 0,
                    "staleDependencyFiles": summary.get("staleDependencyFiles", 0) or 0,
                },
            })
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
    return items, envelope


def collect_assets_lane(subset: Path, root: Path, args) -> tuple:
    platform = (args.platform or "qoder").split(",")[0]
    argv = [str(subset / "coding-agent-practices" / "asset-baseline.mjs"),
            platform, "--workspace", str(root), "--json"]
    envelope = run_node(subset, root, argv)
    envelopes = envelope.get("envelopes", {})
    lint_findings = 0
    lint_data = envelopes.get("lint", {}).get("data") or {}
    if isinstance(lint_data, dict):
        findings_block = lint_data.get("findings")
        if isinstance(findings_block, dict):
            lint_findings = len(findings_block.get("items") or [])
        elif isinstance(findings_block, list):
            lint_findings = len(findings_block)
    inventory_status = envelopes.get("inventory", {}).get("status", "missing")
    items = [{
        "lane": "assets",
        "evidenceState": "Present" if envelope.get("status") in ("complete", "partial") else "Missing",
        "summary": f"Asset baseline ({platform}): status {envelope.get('status')}, "
                   f"{lint_findings} lint finding(s), inventory {inventory_status}.",
        "evidenceRefs": ["coding-agent-practices/asset-baseline"],
        "signals": {"lintFindings": lint_findings},
    }]
    return items, envelope


# --- python lane runners --------------------------------------------------------------

def collect_runs_lane(root: Path) -> tuple:
    teams_dir = root / ".specify" / "teams"
    if not teams_dir.is_dir():
        raise LaneUnavailable("no .specify/teams directory")
    teams = [d for d in sorted(teams_dir.iterdir())
             if d.is_dir() and not d.name.startswith(".")]
    if not teams:
        raise LaneUnavailable("no team directories under .specify/teams")
    items, raw_teams, partial = [], [], False
    for team in teams:
        run_reports = sorted((team / "runs").glob("*-report.md")) if (team / "runs").is_dir() else []
        state_file = team / "STATE.md"
        log_file = team / "run-log.jsonl"
        critiques = []
        if state_file.is_file():
            in_section = False
            for line in state_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("## Post-Run Critique"):
                    in_section = True
                    continue
                if in_section and line.startswith("## "):
                    break
                if in_section and line.strip().startswith("- "):
                    critiques.append(redact_text(line.strip()[2:], root))
        log_rows = []
        if log_file.is_file():
            for line in log_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    log_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        team_partial = not (state_file.is_file() and log_file.is_file())
        partial = partial or team_partial
        escalations = sum(int(r.get("escalations", 0) or 0) for r in log_rows)
        raw_teams.append({
            "team": team.name, "runReports": len(run_reports),
            "critiques": critiques, "logRows": len(log_rows), "partial": team_partial,
        })
        state = "Exercised" if (run_reports or log_rows) else "Unobserved"
        summary = (f"Team {team.name}: {len(run_reports)} run report(s), "
                   f"{len(log_rows)} logged cycle(s), {len(critiques)} critique note(s)"
                   + ("; artifacts incomplete (no STATE.md/run-log)" if team_partial else "") + ".")
        items.append({
            "lane": "runs",
            "evidenceState": state,
            "summary": summary,
            "evidenceRefs": [str(p.relative_to(root)) for p in run_reports[:5]],
            "signals": {
                "runReports": len(run_reports),
                "loggedCycles": len(log_rows),
                "escalations": escalations,
                "critiqueNotes": len(critiques),
            },
        })
    envelope = {"teams": raw_teams}
    return items, envelope, (LANE_PARTIAL if partial else LANE_AVAILABLE), {"teamsScanned": len(teams)}


def collect_feedback_lane(root: Path) -> tuple:
    store = root / ".specify" / "memory" / "feedback"
    if not store.is_dir():
        raise LaneUnavailable("no .specify/memory/feedback directory")
    index_file = store / "index.json"
    status = LANE_AVAILABLE
    entries = []
    if index_file.is_file():
        try:
            entries = json.loads(index_file.read_text(encoding="utf-8")).get("entries", [])
        except (json.JSONDecodeError, OSError):
            entries = []
    if not entries:
        status = LANE_PARTIAL if index_file.is_file() else LANE_PARTIAL
        entries = [{"file": p.name, "unit_id": "", "created": ""}
                   for p in sorted(store.glob("*.md"))]
    if not entries:
        raise LaneUnavailable("feedback store empty")

    point_topics = {}
    for entry in entries:
        entry_file = store / str(entry.get("file", ""))
        if not entry_file.is_file():
            continue
        in_points = False
        for line in entry_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("## Optimization Points"):
                in_points = True
                continue
            if in_points and line.startswith("## "):
                break
            if in_points and line.strip().startswith("- "):
                topic = normalize_topic(line.strip()[2:])
                if topic:
                    point_topics.setdefault(topic, []).append(entry_file.name)
    items = []
    recurring = {t: files for t, files in point_topics.items() if len(files) >= 2}
    for topic, files in sorted(recurring.items(), key=lambda kv: -len(kv[1]))[:10]:
        items.append({
            "lane": "feedback",
            "evidenceState": "Exercised",
            "summary": f"Recurring optimization theme across {len(files)} feedback entries: "
                       f"{redact_text(topic[:160], root)}",
            "evidenceRefs": [str(EVIDENCE_FEEDBACK_REL / f) for f in sorted(set(files))[:6]],
            "signals": {"recurrence": len(files)},
        })
    items.append({
        "lane": "feedback",
        "evidenceState": "Present",
        "summary": f"Feedback store scanned: {len(entries)} entr(y/ies), "
                   f"{len(recurring)} recurring optimization theme(s).",
        "evidenceRefs": [str(EVIDENCE_FEEDBACK_REL / "index.json")],
        "signals": {"entries": len(entries), "recurringThemes": len(recurring)},
    })
    envelope = {"entries": len(entries), "recurringThemes": {k: len(v) for k, v in recurring.items()}}
    return items, envelope, status, {"entries": len(entries)}


EVIDENCE_FEEDBACK_REL = Path(".specify") / "memory" / "feedback"

STOPWORDS = {"the", "a", "an", "of", "for", "to", "in", "and", "or", "is", "are", "with", "on", "at"}


def normalize_topic(text: str) -> str:
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]{2,}", text.lower())
    words = [w for w in words if w not in STOPWORDS][:6]
    return " ".join(words)


class LaneUnavailable(Exception):
    pass


# --- collect orchestration ---------------------------------------------------------

def action_collect(args) -> dict:
    root = resolve_workspace_root(args.workspace_root)
    if not TARGET_RE.match(args.target or ""):
        raise CliError(f"invalid --target: {args.target!r} (expected skill:<name>, /speckit.<cmd>, or project)")
    requested = LANE_NAMES if args.lanes in (None, "", "all") else tuple(
        lane.strip() for lane in args.lanes.split(",") if lane.strip())
    for lane in requested:
        if lane not in LANE_NAMES:
            raise CliError(f"unknown lane: {lane}")

    now = utc_now()
    run_id = make_run_id(args.target, now, evidence_dir(root))
    run_dir = evidence_dir(root) / run_id
    lanes_dir = run_dir / "lanes"
    node = probe_node()
    subset = engine_subset_path(root)

    lane_status = {}
    lane_meta = {}
    evidence = []
    envelopes = {}

    for lane in LANE_NAMES:
        if lane not in requested:
            lane_status[lane] = {"status": LANE_UNAVAILABLE, "reason": "lane not requested"}
            continue
        if lane in NODE_LANES:
            if not node["available"]:
                lane_status[lane] = {"status": LANE_UNAVAILABLE, "reason": "node not available"}
                evidence.append(unobserved_item(lane, "Node runtime unavailable; lane not collected."))
                continue
            if subset is None:
                lane_status[lane] = {"status": LANE_UNAVAILABLE, "reason": "engine subset not found"}
                evidence.append(unobserved_item(lane, "Engine subset not found; lane not collected."))
                continue
        try:
            if lane == "session":
                items, envelope = collect_session_lane(subset, root, args)
                status, meta = LANE_AVAILABLE, {}
            elif lane == "project":
                items, envelope = collect_project_lane(subset, root, args)
                status, meta = LANE_AVAILABLE, {}
            elif lane == "assets":
                items, envelope = collect_assets_lane(subset, root, args)
                status, meta = LANE_AVAILABLE, {}
            elif lane == "runs":
                items, envelope, status, meta = collect_runs_lane(root)
            else:
                items, envelope, status, meta = collect_feedback_lane(root)
            lane_status[lane] = {"status": status, **meta}
            lane_meta[lane] = meta
            envelopes[lane] = envelope
            evidence.extend(items)
        except LaneUnavailable as exc:
            lane_status[lane] = {"status": LANE_UNAVAILABLE, "reason": str(exc)}
            evidence.append(unobserved_item(lane, f"Lane unavailable: {exc}."))
        except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            lane_status[lane] = {"status": LANE_UNAVAILABLE,
                                 "reason": redact_text(str(exc)[:300], root)}
            evidence.append(unobserved_item(lane, "Lane collection failed; see manifest reason."))

    evidence = [redact_deep(item, root) for item in evidence]
    for pos, item in enumerate(evidence, start=1):
        item_ordered = {"id": f"ev-{pos:03d}"}
        item_ordered.update(item)
        evidence[pos - 1] = item_ordered

    digest = compute_digest(evidence)
    platforms = sorted({(args.platform or "qoder").split(",")[0]}) if any(
        lane_status.get(l, {}).get("status") != LANE_UNAVAILABLE for l in ("session", "assets")) else []

    findings = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": FINDINGS_KIND,
        "target": args.target,
        "runId": run_id,
        "window": {"since": args.since, "until": args.until},
        "platforms": platforms,
        "lanes": lane_status,
        "evidence": evidence,
        "findingsDigest": digest,
    }
    manifest = {
        "runId": run_id,
        "target": args.target,
        "created": iso(now),
        "lanes": lane_status,
        "engine": {
            "engineSubsetPath": str(subset.relative_to(root)) if subset else None,
            "upstreamCommit": UPSTREAM_COMMIT,
            **({"nodeVersion": node.get("version")} if node.get("available") else {}),
        },
        "findingsDigest": digest,
    }

    run_dir.mkdir(parents=True, exist_ok=True)
    write_text_atomic(run_dir / "findings.json",
        json.dumps(findings, ensure_ascii=False, indent=2) + "\n")
    write_text_atomic(run_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for lane, envelope in envelopes.items():
        lanes_dir.mkdir(parents=True, exist_ok=True)
        write_text_atomic(lanes_dir / f"{lane}.json",
            json.dumps(redact_deep(envelope, root), ensure_ascii=False, indent=2) + "\n")

    index = load_index(root)
    index["entries"].append({
        "runId": run_id,
        "target": args.target,
        "created": iso(now),
        "lanesSummary": {k: v.get("status", "") for k, v in lane_status.items()},
        "file": str(Path(run_id) / "findings.json"),
    })
    save_index(root, index)

    return {
        "runId": run_id,
        "path": str(run_dir.relative_to(root)),
        "lanes": {k: v.get("status") for k, v in lane_status.items()},
        "evidenceCount": len(evidence),
        "findingsDigest": digest,
    }


def unobserved_item(lane: str, summary: str) -> dict:
    item = {
        "lane": lane,
        "evidenceState": "Unobserved",
        "summary": summary,
        "evidenceRefs": [],
        "signals": {},
    }
    if lane == "session":
        item["privacyNote"] = "redacted-semantic-facet"
    return item


# --- list / latest / compare ----------------------------------------------------------

def action_list(args) -> dict:
    root = resolve_workspace_root(args.workspace_root)
    index = load_index(root)
    entries = index["entries"]
    if args.target:
        entries = [e for e in entries if e.get("target") == args.target]
    entries = sorted(entries, key=lambda e: e.get("created", ""), reverse=True)
    return {"entries": entries[: args.limit]}


def action_latest(args) -> dict:
    root = resolve_workspace_root(args.workspace_root)
    if not args.target:
        raise CliError("--target is required for latest")
    index = load_index(root)
    entries = sorted(
        (e for e in index["entries"] if e.get("target") == args.target),
        key=lambda e: e.get("created", ""), reverse=True)
    if not entries:
        return {"found": False}
    entry = entries[0]
    created = entry.get("created", "")
    age_days = None
    stale = False
    try:
        created_dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_days = (utc_now() - created_dt).days
        stale = age_days > args.max_age_days
    except ValueError:
        stale = True
    result = {
        "found": True,
        "runId": entry["runId"],
        "path": str(EVIDENCE_SUBDIR / entry["file"]),
        "created": created,
        "ageDays": age_days,
        "stale": stale,
    }
    if stale:
        result["warning"] = (
            f"Evidence run {entry['runId']} exceeds the freshness threshold "
            f"({args.max_age_days} days); consider re-collecting before consuming.")
    return result


def load_run(root: Path, run_id: str) -> dict:
    run_dir = evidence_dir(root) / run_id
    findings_file = run_dir / "findings.json"
    if not findings_file.is_file():
        raise CliError(f"run not found: {run_id}")
    return json.loads(findings_file.read_text(encoding="utf-8"))


def signal_map(findings: dict) -> dict:
    signals = {}
    for item in findings.get("evidence", []):
        for key, value in item.get("signals", {}).items():
            signals[(item.get("lane"), key)] = signals.get((item.get("lane"), key), 0) + value
    return signals


def action_compare(args) -> dict:
    root = resolve_workspace_root(args.workspace_root)
    if not args.target:
        raise CliError("--target is required for compare")
    index = load_index(root)
    entries = sorted(
        (e for e in index["entries"] if e.get("target") == args.target),
        key=lambda e: e.get("created", ""))
    baseline_id = args.baseline
    current_id = args.current
    if not current_id:
        if not entries:
            raise CliError(f"no runs recorded for target {args.target}")
        current_id = entries[-1]["runId"]
    if not baseline_id:
        if len(entries) < 2:
            raise CliError(f"need at least two runs for target {args.target} (or pass --baseline)")
        baseline_id = entries[-2]["runId"]

    baseline = load_run(root, baseline_id)
    current = load_run(root, current_id)
    base_signals = signal_map(baseline)
    curr_signals = signal_map(current)
    deltas = []
    for key in sorted(set(base_signals) | set(curr_signals)):
        before = base_signals.get(key, 0)
        after = curr_signals.get(key, 0)
        if before != after:
            deltas.append({"lane": key[0], "signalKey": key[1], "before": before, "after": after})

    base_summaries = {i["summary"] for i in baseline.get("evidence", [])}
    curr_summaries = {i["summary"] for i in current.get("evidence", [])}
    new_evidence = [i["id"] for i in current.get("evidence", []) if i["summary"] not in base_summaries]
    resolved = [i["id"] for i in baseline.get("evidence", []) if i["summary"] not in curr_summaries]

    result = {
        "baseline": baseline_id,
        "current": current_id,
        "signalDeltas": deltas,
        "newEvidence": new_evidence,
        "resolvedEvidence": resolved,
    }

    intervention_file = evidence_dir(root) / baseline_id / "intervention.json"
    if intervention_file.is_file():
        intervention = json.loads(intervention_file.read_text(encoding="utf-8"))
        target_finding = intervention.get("targetFinding")
        if not any(i.get("id") == target_finding for i in baseline.get("evidence", [])):
            raise CliError(f"intervention targetFinding {target_finding!r} not present in baseline findings")
        expected = intervention.get("expectedSignal", {})
        signal_key = expected.get("signalKey")
        direction = expected.get("direction")
        verdict = "Unobserved"
        matching = [d for d in deltas if d["signalKey"] == signal_key]
        if matching:
            delta = matching[0]
            if direction == "reduce" and delta["after"] < delta["before"]:
                verdict = "Outcome-supported"
            elif direction == "improve" and delta["after"] > delta["before"]:
                verdict = "Outcome-supported"
        else:
            has_signal = any(k[1] == signal_key for k in set(base_signals) | set(curr_signals))
            verdict = "Unobserved" if not has_signal else "Unobserved"
        intervention["verdict"] = verdict
        intervention_file.write_text(
            json.dumps(intervention, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["intervention"] = {
            "targetFinding": target_finding,
            "expectedSignal": expected,
            "verdict": verdict,
        }
    return result


# --- entrypoint ------------------------------------------------------------------------

class CliError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spec Kit evidence-lane orchestrator")
    parser.add_argument("--action", required=True,
                        choices=["doctor", "collect", "list", "latest", "compare"])
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--lanes", default="all")
    parser.add_argument("--since", default=None)
    parser.add_argument("--until", default=None)
    parser.add_argument("--depth", choices=["quick", "normal"], default="normal")
    parser.add_argument("--platform", default="qoder")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--current", default=None)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    actions = {
        "doctor": action_doctor,
        "collect": action_collect,
        "list": action_list,
        "latest": action_latest,
        "compare": action_compare,
    }
    try:
        if args.action == "collect" and not args.target:
            raise CliError("--target is required for collect")
        result = actions[args.action](args)
    except CliError as exc:
        json.dump({"error": str(exc)}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
