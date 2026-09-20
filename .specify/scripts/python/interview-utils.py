#!/usr/bin/env python3
"""Interview decision-DAG engine for `/speckit.interview` (Feature 042).

The command owns the conversation; this engine owns the deterministic parts of the
interview pattern — dependency tracking, frontier computation, cycle rejection,
conflict lookup, and retraction propagation. Graph reachability and topological
ordering are fixed-rule computations, so they belong in a program rather than in a
model (Constitution Principle XII / token-efficiency Program-First).

Pattern authority: shared/patterns/interview-pattern.md (read-only for this engine).

The store is a JSON sidecar next to the human-readable ledger, so the markdown
ledger stays the thing a human reads while the graph stays machine-queryable.

Actions:
  init      --target PATH [--mode special|informal] [--branches ...]
  add       --id D4 --question TEXT [--depends-on D1 ...] [--branch NAME]
  answer    <id> --decision TEXT [--span TEXT]
  frontier                          # askable now, dependency-ordered
  descendants <id> [--direct]       # transitive dependents
  retract   <id> [--decision TEXT] [--apply]
  conflicts --with TEXT             # settled decisions to check a new answer against
  status                            # counts + exit-gate readiness
  order                             # full topological order (deep premises first)
  render                            # regenerate the markdown ledger table

Exit codes: 0 ok | 2 input error | 3 not found | 4 validation failed (cycle/stale)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import deque
from pathlib import Path

EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_NOT_FOUND = 3
EXIT_INVALID = 4

#: Status vocabulary mirrors the pattern's ledger legend one-for-one.
OPEN = "open"
ASKED = "asked"
SETTLED = "settled"
DEFERRED = "deferred"
RETRACTED = "retracted"
STATUSES = (OPEN, ASKED, SETTLED, DEFERRED, RETRACTED)

_GLYPH = {OPEN: "⬜", ASKED: "🔄", SETTLED: "✅", DEFERRED: "⏭", RETRACTED: "↩︎"}

MODES = ("special", "informal")

#: Same shape as the pattern's `D4` examples: a letter prefix plus digits.
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")

STORE_SUFFIX = ".dag.json"


class EngineError(Exception):
    """Raised with an exit code so `main` can map failures to the CLI contract."""

    def __init__(self, message: str, code: int = EXIT_INPUT_ERROR):
        super().__init__(message)
        self.code = code


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return _dt.date.today().isoformat()


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def store_path(ledger: Path) -> Path:
    """The JSON sidecar for a markdown ledger: `interview-log.md` → `interview-log.dag.json`."""
    return ledger.with_suffix(STORE_SUFFIX)


def load(ledger: Path) -> dict:
    path = store_path(ledger)
    if not path.is_file():
        raise EngineError(f"no interview store at {path}; run `init` first", EXIT_NOT_FOUND)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EngineError(f"corrupt store {path}: {exc}", EXIT_INVALID) from exc
    data.setdefault("decisions", [])
    data.setdefault("retractions", [])
    return data


def save(ledger: Path, data: dict) -> None:
    path = store_path(ledger)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _index(data: dict) -> dict[str, dict]:
    return {d["id"]: d for d in data["decisions"]}


def _get(data: dict, decision_id: str) -> dict:
    node = _index(data).get(decision_id)
    if node is None:
        raise EngineError(f"unknown decision id: {decision_id}", EXIT_NOT_FOUND)
    return node


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def _dependents_map(data: dict) -> dict[str, list[str]]:
    """Reverse edges: premise id → ids that rest on it."""
    out: dict[str, list[str]] = {d["id"]: [] for d in data["decisions"]}
    for node in data["decisions"]:
        for premise in node.get("dependsOn", []):
            if premise in out:
                out[premise].append(node["id"])
    return out


def _would_cycle(data: dict, new_id: str, depends_on: list[str]) -> list[str] | None:
    """Return a cycle path if `new_id` depending on `depends_on` closes a loop.

    A retraction walk on a cyclic graph never terminates, and a cyclic premise set is
    unanswerable by construction — so the cycle is rejected at insertion time.
    """
    index = _index(data)
    for start in depends_on:
        if start == new_id:
            return [new_id, new_id]
        # Walk the premise chain upward; reaching new_id means new_id is already
        # (transitively) a premise of `start`, so the new edge closes a cycle.
        stack = [(start, [new_id, start])]
        seen = set()
        while stack:
            current, path = stack.pop()
            if current == new_id:
                return path
            if current in seen:
                continue
            seen.add(current)
            for premise in index.get(current, {}).get("dependsOn", []):
                stack.append((premise, path + [premise]))
    return None


def descendants(data: dict, decision_id: str, direct: bool = False) -> list[str]:
    """Ids that rest on `decision_id`, transitively unless `direct`.

    Returned in breadth-first order so a caller re-asks premises before the
    decisions that depend on them.
    """
    _get(data, decision_id)
    dependents = _dependents_map(data)
    if direct:
        return list(dependents.get(decision_id, []))
    out: list[str] = []
    seen = {decision_id}
    queue = deque(dependents.get(decision_id, []))
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        out.append(current)
        queue.extend(dependents.get(current, []))
    return out


def topological_order(data: dict) -> list[str]:
    """Kahn order, tie-broken by descendant count so deep premises come first.

    This is the `I1` ordering rule: settling a widely-depended-on premise late is
    what turns a single retraction into a session of rework.
    """
    index = _index(data)
    indegree = {i: len([p for p in n.get("dependsOn", []) if p in index])
                for i, n in index.items()}
    dependents = _dependents_map(data)
    reach = {i: len(descendants(data, i)) for i in index}

    ready = [i for i, deg in indegree.items() if deg == 0]
    out: list[str] = []
    while ready:
        # Most-depended-on first; id as a stable tiebreak.
        ready.sort(key=lambda i: (-reach[i], i))
        current = ready.pop(0)
        out.append(current)
        for dependent in dependents.get(current, []):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if len(out) != len(index):
        stuck = sorted(set(index) - set(out))
        raise EngineError(f"cycle detected among: {', '.join(stuck)}", EXIT_INVALID)
    return out


def frontier(data: dict) -> list[str]:
    """Open decisions whose every premise is settled — the askable round.

    A premise that is retracted or deferred does not count as settled, so its
    dependents correctly stay off the frontier.
    """
    index = _index(data)
    order = topological_order(data)
    out = []
    for decision_id in order:
        node = index[decision_id]
        if node["status"] != OPEN:
            continue
        premises = [p for p in node.get("dependsOn", []) if p in index]
        if all(index[p]["status"] == SETTLED for p in premises):
            out.append(decision_id)
    return out


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def act_init(ledger: Path, target: str, mode: str | None, branches: list[str],
             force: bool) -> dict:
    if mode is not None and mode not in MODES:
        raise EngineError(f"mode must be one of {', '.join(MODES)}")
    path = store_path(ledger)
    if path.is_file() and not force:
        raise EngineError(f"store already exists at {path}; resume it or pass --force")
    data = {
        "ledger": str(ledger),
        "target": target,
        "mode": mode,
        "branches": branches,
        "started": _today(),
        "decisions": [],
        "retractions": [],
    }
    save(ledger, data)
    return {"action": "init", "store": str(path), "target": target, "mode": mode}


def act_add(ledger: Path, decision_id: str, question: str, depends_on: list[str],
            branch: str | None) -> dict:
    data = load(ledger)
    if not _ID.match(decision_id):
        raise EngineError(f"invalid id {decision_id!r}: expected a letter then [A-Za-z0-9_.-]")
    index = _index(data)
    if decision_id in index:
        raise EngineError(f"id {decision_id} already exists; ids are never reused")
    unknown = [p for p in depends_on if p not in index]
    if unknown:
        raise EngineError(f"unknown premise(s): {', '.join(unknown)}", EXIT_NOT_FOUND)
    cycle = _would_cycle(data, decision_id, depends_on)
    if cycle:
        raise EngineError(f"dependency cycle: {' -> '.join(cycle)}", EXIT_INVALID)
    data["decisions"].append({
        "id": decision_id,
        "question": question,
        "dependsOn": depends_on,
        "branch": branch,
        "status": OPEN,
        "decision": None,
        "span": None,
        "supersededBy": None,
        "round": None,
        "updated": _now(),
    })
    save(ledger, data)
    return {"action": "add", "id": decision_id, "dependsOn": depends_on, "status": OPEN}


def act_answer(ledger: Path, decision_id: str, decision: str, span: str | None,
               round_no: int | None) -> dict:
    data = load(ledger)
    node = _get(data, decision_id)
    if node["status"] == RETRACTED:
        raise EngineError(f"{decision_id} is retracted; add a new id instead", EXIT_INVALID)
    index = _index(data)
    unsettled = [p for p in node.get("dependsOn", [])
                 if p in index and index[p]["status"] != SETTLED]
    if unsettled:
        raise EngineError(
            f"{decision_id} rests on unsettled premise(s): {', '.join(unsettled)}",
            EXIT_INVALID,
        )
    node.update(status=SETTLED, decision=decision, span=span, updated=_now())
    if round_no is not None:
        node["round"] = round_no
    save(ledger, data)
    return {"action": "answer", "id": decision_id, "status": SETTLED, "span": span}


def act_defer(ledger: Path, decision_id: str, reason: str) -> dict:
    data = load(ledger)
    node = _get(data, decision_id)
    node.update(status=DEFERRED, decision=f"deferred: {reason}", updated=_now())
    save(ledger, data)
    return {"action": "defer", "id": decision_id, "status": DEFERRED, "reason": reason}


def act_retract(ledger: Path, decision_id: str, decision: str | None,
                apply: bool) -> dict:
    """Plan (or apply) a retraction: classify descendants and list spans to roll back.

    Dry-run by default — the command shows the blast radius to the user before any
    artifact is touched. `--apply` records the retraction and re-opens the affected
    decisions; rolling back the artifact spans stays the caller's job, since only it
    knows how to edit the target.
    """
    data = load(ledger)
    node = _get(data, decision_id)
    if node["status"] == RETRACTED:
        raise EngineError(f"{decision_id} is already retracted", EXIT_INVALID)

    affected = descendants(data, decision_id)
    index = _index(data)
    # Only settled/asked descendants carry work that a premise change invalidates;
    # still-open ones simply stay open.
    invalidated = [i for i in affected if index[i]["status"] in (SETTLED, ASKED)]
    spans = [{"id": i, "span": index[i]["span"]} for i in invalidated
             if index[i].get("span")]
    untouched = [i for i in affected if i not in invalidated]

    plan = {
        "action": "retract",
        "id": decision_id,
        "applied": apply,
        "descendants": affected,
        "invalidated": invalidated,
        "needs_rollback": spans,
        "already_open": untouched,
        "own_span": node.get("span"),
    }

    if not apply:
        plan["note"] = "dry run — nothing written; re-run with --apply"
        return plan

    for i in invalidated:
        index[i].update(status=OPEN, decision=None, span=None, updated=_now())
    if decision is None:
        # Retracted without a replacement yet: re-open it so the round re-asks it.
        node.update(status=OPEN, decision=None, span=None, updated=_now())
    else:
        node.update(status=SETTLED, decision=decision, span=None, updated=_now())
    data["retractions"].append({
        "id": decision_id,
        "at": _now(),
        "new_decision": decision,
        "invalidated": invalidated,
    })
    save(ledger, data)
    plan["reopened"] = invalidated + ([] if decision else [decision_id])
    return plan


def act_conflicts(ledger: Path, text: str) -> dict:
    """Settled decisions sharing significant terms with `text`.

    Deliberately a *candidate* filter, not a verdict: whether two decisions truly
    conflict is a semantic judgement the model makes. The engine narrows the field
    so that judgement runs over a handful of rows instead of the whole ledger.
    """
    data = load(ledger)
    words = {w for w in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text.lower())
             if len(w) > 2}
    hits = []
    for node in data["decisions"]:
        if node["status"] != SETTLED or not node.get("decision"):
            continue
        haystack = f"{node['question']} {node['decision']}".lower()
        shared = sorted(w for w in words if w in haystack)
        if shared:
            hits.append({"id": node["id"], "decision": node["decision"],
                         "shared_terms": shared})
    hits.sort(key=lambda h: (-len(h["shared_terms"]), h["id"]))
    return {"action": "conflicts", "candidates": hits,
            "note": "candidates only — semantic conflict is the model's call"}


def act_status(ledger: Path) -> dict:
    data = load(ledger)
    counts = {s: 0 for s in STATUSES}
    for node in data["decisions"]:
        counts[node["status"]] = counts.get(node["status"], 0) + 1
    front = frontier(data)
    index = _index(data)
    # A settled decision whose premise is no longer settled is stale — the exit gate
    # must not pass while one exists.
    stale = [n["id"] for n in data["decisions"]
             if n["status"] == SETTLED
             and any(index[p]["status"] != SETTLED
                     for p in n.get("dependsOn", []) if p in index)]
    missing_span = [n["id"] for n in data["decisions"]
                    if n["status"] == SETTLED and not n.get("span")]
    return {
        "action": "status",
        "target": data.get("target"),
        "mode": data.get("mode"),
        "total": len(data["decisions"]),
        "counts": counts,
        "frontier": front,
        "stale": stale,
        "settled_without_span": missing_span,
        "retractions": len(data["retractions"]),
        "exit_gate_ready": not front and not stale and counts[OPEN] == 0
        and counts[ASKED] == 0,
    }


def render(ledger: Path) -> str:
    """Regenerate the human-readable ledger table from the graph."""
    data = load(ledger)
    lines = [
        f"# Interview Ledger: {data.get('target', '<target>')}",
        "",
        f"- **Started**: {data.get('started', '')}",
        f"- **Target artifact**: {data.get('target', '')}",
        f"- **Mode**: {data.get('mode') or '<unset>'}",
        f"- **Branches**: {', '.join(data.get('branches') or []) or '<none declared>'}",
        "- **Recording**: overwrite-style; latest round wins",
        "- **Status legend**: ⬜ open / 🔄 asked / ✅ settled / ⏭ deferred / ↩︎ retracted",
        "",
        "| ID | Round | Branch | Question | dependsOn | Status | Decision | Artifact span | Superseded by |",
        "|----|-------|--------|----------|-----------|--------|----------|---------------|---------------|",
    ]
    for decision_id in topological_order(data):
        n = _index(data)[decision_id]
        lines.append(
            "| {id} | {round} | {branch} | {q} | {dep} | {st} | {dec} | {span} | {sup} |".format(
                id=n["id"],
                round=n.get("round") or "",
                branch=n.get("branch") or "",
                q=n["question"],
                dep=", ".join(n.get("dependsOn", [])) or "—",
                st=_GLYPH.get(n["status"], n["status"]),
                dec=n.get("decision") or "",
                span=n.get("span") or "",
                sup=n.get("supersededBy") or "",
            )
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit(payload: dict | str, as_json: bool) -> None:
    if isinstance(payload, str):
        sys.stdout.write(payload)
        return
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for key, value in payload.items():
        if isinstance(value, (list, dict)) and value:
            print(f"{key}:")
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                for item in value:
                    print(f"  - {item}")
        else:
            print(f"{key}: {value if value != [] else '(none)'}")


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--ledger", required=True, help="path to the markdown ledger")
    common.add_argument("--json", action="store_true", help="machine-readable output")

    parser = argparse.ArgumentParser(
        prog="interview-utils.py",
        description="Decision-DAG engine for the interview pattern.",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_init = sub.add_parser("init", parents=[common])
    p_init.add_argument("--target", required=True)
    p_init.add_argument("--mode", default=None, choices=list(MODES))
    p_init.add_argument("--branch", action="append", default=[], dest="branches")
    p_init.add_argument("--force", action="store_true")

    p_add = sub.add_parser("add", parents=[common])
    p_add.add_argument("--id", required=True, dest="decision_id")
    p_add.add_argument("--question", required=True)
    p_add.add_argument("--depends-on", action="append", default=[], dest="depends_on")
    p_add.add_argument("--branch", default=None)

    p_answer = sub.add_parser("answer", parents=[common])
    p_answer.add_argument("decision_id")
    p_answer.add_argument("--decision", required=True)
    p_answer.add_argument("--span", default=None)
    p_answer.add_argument("--round", type=int, default=None, dest="round_no")

    p_defer = sub.add_parser("defer", parents=[common])
    p_defer.add_argument("decision_id")
    p_defer.add_argument("--reason", required=True)

    sub.add_parser("frontier", parents=[common])
    sub.add_parser("order", parents=[common])
    sub.add_parser("status", parents=[common])
    p_render = sub.add_parser("render", parents=[common])
    p_render.add_argument("--out", default=None, help="write rendered ledger to this file instead of stdout")

    p_desc = sub.add_parser("descendants", parents=[common])
    p_desc.add_argument("decision_id")
    p_desc.add_argument("--direct", action="store_true")

    p_retract = sub.add_parser("retract", parents=[common])
    p_retract.add_argument("decision_id")
    p_retract.add_argument("--decision", default=None)
    p_retract.add_argument("--apply", action="store_true")

    p_conf = sub.add_parser("conflicts", parents=[common])
    p_conf.add_argument("--with", required=True, dest="text")

    args = parser.parse_args(argv)
    ledger = Path(args.ledger)

    try:
        if args.action == "init":
            payload = act_init(ledger, args.target, args.mode, args.branches, args.force)
        elif args.action == "add":
            payload = act_add(ledger, args.decision_id, args.question,
                              args.depends_on, args.branch)
        elif args.action == "answer":
            payload = act_answer(ledger, args.decision_id, args.decision,
                                 args.span, args.round_no)
        elif args.action == "defer":
            payload = act_defer(ledger, args.decision_id, args.reason)
        elif args.action == "frontier":
            payload = {"action": "frontier", "frontier": frontier(load(ledger))}
        elif args.action == "order":
            payload = {"action": "order", "order": topological_order(load(ledger))}
        elif args.action == "status":
            payload = act_status(ledger)
        elif args.action == "render":
            payload = render(ledger)
            if getattr(args, "out", None):
                from pathlib import Path as _P
                _P(args.out).write_text(str(payload), encoding="utf-8")
                payload = {"written": args.out}
        elif args.action == "descendants":
            data = load(ledger)
            payload = {"action": "descendants", "id": args.decision_id,
                       "descendants": descendants(data, args.decision_id, args.direct)}
        elif args.action == "retract":
            payload = act_retract(ledger, args.decision_id, args.decision, args.apply)
        elif args.action == "conflicts":
            payload = act_conflicts(ledger, args.text)
        else:  # pragma: no cover - argparse guards this
            parser.error(f"unknown action {args.action}")
    except EngineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code

    _emit(payload, getattr(args, "json", False))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
