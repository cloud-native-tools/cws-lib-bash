#!/usr/bin/env python3
"""integrate-lines.py — executable integration coordinator for 064.

Executes the WI-14 per-line sequence for every runnable entry of
`integration-plan`: rebase onto the trunk -> quality gate -> merge ->
integration-record -> archive-runtime -> `git worktree remove` (never --force).
Mirrors run once per batch, after all lines, never per line (WI-11).

Stdlib only.  Exit codes: 0 all merged, 2 usage/validation, 3 one or more
lines failed or the batch mirror failed.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAILED = 3
SKILL_SCRIPTS = Path(__file__).resolve().parent


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def git(repo: Path, *args: str):
    return run(["git", "-C", str(repo), *args])


def engine(reg: Path, action: str, *args: str):
    cmd = [
        sys.executable, str(SKILL_SCRIPTS / "line-registry.py"),
        "--action", action, *args,
    ]
    env = os.environ.copy()
    env["SPECIFY_LINE_REGISTRY_DIR"] = str(reg)
    proc = run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"engine {action} failed rc={proc.returncode}: {proc.stdout.strip()} {proc.stderr.strip()}"
        )
    return json.loads(proc.stdout)


def read_entry(reg: Path, line_id: str) -> dict:
    return json.loads((reg / f"{line_id}.json").read_text(encoding="utf-8"))


def git_path_exists(repo: Path, marker: str) -> bool:
    proc = git(repo, "rev-parse", "--git-path", marker)
    if proc.returncode != 0:
        return False
    path = Path(proc.stdout.strip())
    if not path.is_absolute():
        path = repo / path
    return path.exists()


def _result(line_id: str, status: str, **extra) -> dict:
    payload = {"line_id": line_id, "status": status, "archive_calls": 0}
    payload.update(extra)
    return payload


def _record_failed(reg: Path, line_id: str, reason: str) -> None:
    engine(reg, "integration-record", "--line-id", line_id, "--result", "failed",
           "--reason", reason)


def _mark_retained(reg: Path, line_id: str) -> None:
    engine(reg, "update", "--line-id", line_id, "--worktree-retained", "true")


def integrate_line(repo: Path, trunk: str, reg: Path, archive: Path, entry: dict, gate_cmd: str | None) -> dict:
    line_id = entry["line_id"]
    worktree = entry.get("worktree_path")
    if not worktree:
        _record_failed(reg, line_id, "missing-worktree")
        return _result(line_id, "failed", reason="missing-worktree")
    wt = Path(worktree)
    if not wt.exists():
        _record_failed(reg, line_id, "worktree-missing")
        return _result(line_id, "failed", reason="worktree-missing")

    if git_path_exists(wt, "rebase-merge") or git_path_exists(wt, "rebase-apply"):
        _record_failed(reg, line_id, "rebase-in-progress")
        return _result(line_id, "failed", reason="rebase-in-progress")

    rebased = git(wt, "rebase", trunk)
    if rebased.returncode != 0:
        if git_path_exists(wt, "rebase-merge") or git_path_exists(wt, "rebase-apply"):
            git(wt, "rebase", "--abort")
        _record_failed(reg, line_id, "rebase")
        return _result(line_id, "failed", reason="rebase", detail=rebased.stderr.strip())

    if gate_cmd:
        gate = run(["bash", "-c", gate_cmd], cwd=wt)
        if gate.returncode != 0:
            _record_failed(reg, line_id, "quality-gate")
            return _result(
                line_id, "failed", reason="quality-gate",
                detail=(gate.stdout + gate.stderr).strip()[-2000:],
            )

    head = git(wt, "rev-parse", "HEAD")
    if head.returncode != 0:
        _record_failed(reg, line_id, "head")
        return _result(line_id, "failed", reason="head")
    merged = git(repo, "merge", "--ff-only", head.stdout.strip())
    if merged.returncode != 0:
        if git_path_exists(repo, "MERGE_HEAD"):
            git(repo, "merge", "--abort")
        _record_failed(reg, line_id, "merge")
        return _result(line_id, "failed", reason="merge", detail=merged.stderr.strip())

    commit = git(repo, "rev-parse", "HEAD").stdout.strip()
    engine(reg, "integration-record", "--line-id", line_id, "--result", "merged",
           "--commit", commit)
    result = _result(line_id, "merged", commit=commit, worktree_removed=False)

    try:
        engine(reg, "archive-runtime", "--line-id", line_id,
               "--worktree", str(wt), "--dest", str(archive))
        result["archive_calls"] = 1
    except RuntimeError as exc:
        result.setdefault("warnings", []).append(f"archive-runtime: {exc}")
        _mark_retained(reg, line_id)
        return result

    removed = git(repo, "worktree", "remove", str(wt))
    if removed.returncode != 0:
        result.setdefault("warnings", []).append(
            f"worktree remove failed (retained): {removed.stderr.strip()}"
        )
        _mark_retained(reg, line_id)
    else:
        result["worktree_removed"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="integrate-lines.py")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--trunk", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--gate-cmd")
    parser.add_argument("--mirror-cmd")
    parser.add_argument("--lines", help="comma-separated subset; default is the full plan")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    reg = Path(args.registry).expanduser().resolve()
    archive = Path(args.archive).expanduser().resolve()
    if not repo.is_dir():
        print(json.dumps({"ok": False, "error": f"repo not found: {repo}"}))
        return EXIT_USAGE
    if not reg.is_dir():
        print(json.dumps({"ok": False, "error": f"registry not found: {reg}"}))
        return EXIT_USAGE

    current = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if current.returncode != 0 or current.stdout.strip() != args.trunk:
        print(json.dumps({
            "ok": False,
            "error": (
                f"repository is not checked out on trunk {args.trunk!r} "
                f"(actual: {current.stdout.strip() or 'unknown'}); refusing to switch branches"
            ),
        }))
        return EXIT_USAGE
    if (git_path_exists(repo, "MERGE_HEAD") or git_path_exists(repo, "rebase-merge")
            or git_path_exists(repo, "rebase-apply")):
        print(json.dumps({
            "ok": False,
            "error": "repository already has a merge/rebase in progress; refusing to integrate",
        }))
        return EXIT_USAGE

    try:
        plan = engine(reg, "integration-plan")
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return EXIT_FAILED

    selected = None
    if args.lines:
        selected = [item.strip() for item in args.lines.split(",") if item.strip()]
    entries = sorted(
        (item for item in plan if item.get("order")),
        key=lambda item: item["order"],
    )
    if selected is not None:
        unknown = sorted(set(selected) - {item["line_id"] for item in entries})
        if unknown:
            print(json.dumps({"ok": False, "error": f"lines not runnable: {unknown}"}))
            return EXIT_USAGE
        entries = [item for item in entries if item["line_id"] in selected]

    results = [
        _result(item["line_id"], "blocked", blocked_by=item.get("blocked_by") or [])
        for item in plan if not item.get("order")
    ]
    for item in entries:
        entry = read_entry(reg, item["line_id"])
        results.append(integrate_line(repo, args.trunk, reg, archive, entry, args.gate_cmd))

    mirror_calls = 0
    mirror_failed = False
    if args.mirror_cmd:
        mirror = run(["bash", "-c", args.mirror_cmd], cwd=repo)
        mirror_calls = 1
        if mirror.returncode != 0:
            mirror_failed = True
            results.append(_result("__mirrors__", "failed", reason="mirror-batch",
                                   detail=(mirror.stdout + mirror.stderr).strip()[-2000:]))

    failed = [row for row in results if row["status"] == "failed"]
    summary = {
        "ok": not failed and not mirror_failed,
        "trunk": args.trunk,
        "results": results,
        "archive_calls": sum(row["archive_calls"] for row in results),
        "mirror_calls": mirror_calls,
        "failed": len(failed),
    }
    print(json.dumps(summary, sort_keys=True))
    return EXIT_OK if summary["ok"] else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
