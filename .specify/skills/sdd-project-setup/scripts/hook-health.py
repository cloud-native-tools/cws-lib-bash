#!/usr/bin/env python3
"""Host hook health check for unattended SDD runs (sdd-project-setup S4).

Every tool call in an unattended run (sdd-loop-driver) passes through the
host agent's hooks. A synchronous hook is a serial blocking point: at best it
adds its runtime to every call, at worst it exceeds its timeout and the agent
reports a non-blocking hook error while losing that call's telemetry.

Findings fall into two classes:

  fixable         ordinary synchronous command hooks with a tight timeout
                  (<= --max-sync-timeout, default 5s) on tool events.
                  --fix sets handler-level "async": true.
  vendor-managed  hooks owned by a self-healing telemetry agent (AITrace/r2c,
                  yunke, loongsuite, a1). Never auto-fixed: the vendor agent
                  rewrites its hook entry back to its canonical form within
                  seconds, so async/timeout edits do not persist. Reported
                  with remediation for the operator.

Exit codes: 0 clean or every fixable finding fixed; 10 unresolved risks
(report mode, vendor-managed findings, or unfixable hooks); 2 usage or
settings parse error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

TOOL_EVENTS = ("PreToolUse", "PostToolUse", "PostToolUseFailure")
DEFAULT_MAX_SYNC_TIMEOUT = 5

# Command signatures of hook agents that re-register their own entry.
# Changing such an entry (async, timeout) is reverted by the agent.
VENDOR_COMMAND_PATTERNS = (
    "/.r2c/scripts/",
    "ai-coding-trace",
    "aitrace",
    "/.loongsuite-pilot/hooks/",
    "/.yunke/",
    "a1 skill report",
)
VENDOR_MARKER_RE = re.compile(r"^_.*_managed$")


def default_settings_paths(project: Path) -> list:
    home = Path(os.path.expanduser("~"))
    candidates = [
        home / ".qoder" / "settings.json",
        project / ".qoder" / "settings.json",
        project / ".qoder" / "settings.local.json",
        home / ".claude" / "settings.json",
        project / ".claude" / "settings.json",
        project / ".claude" / "settings.local.json",
    ]
    return [p for p in candidates if p.is_file()]


def is_vendor_managed(handler: dict) -> bool:
    for key in handler:
        if isinstance(key, str) and VENDOR_MARKER_RE.match(key):
            return True
    command = handler.get("command") or ""
    return any(pattern in command for pattern in VENDOR_COMMAND_PATTERNS)


def collect_findings(settings_path: Path, max_sync_timeout: int) -> list:
    try:
        config = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"hook-health: cannot read {settings_path}: {exc}") from exc
    if not isinstance(config, dict):
        raise SystemExit(f"hook-health: {settings_path} is not a JSON object")
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return []

    findings = []
    for event, definitions in hooks.items():
        if event not in TOOL_EVENTS or not isinstance(definitions, list):
            continue
        for definition in definitions:
            if not isinstance(definition, dict):
                continue
            if definition.get("async") is True:
                continue
            matcher = definition.get("matcher") or "*"
            handlers = definition.get("hooks")
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict):
                    continue
                if handler.get("type", "command") != "command":
                    continue
                if handler.get("async") is True:
                    continue
                vendor = is_vendor_managed(handler)
                timeout = handler.get("timeout")
                if isinstance(timeout, (int, float)) and timeout > max_sync_timeout:
                    continue
                if not vendor and not isinstance(timeout, (int, float)):
                    continue
                findings.append(
                    {
                        "file": str(settings_path),
                        "event": event,
                        "matcher": matcher,
                        "command": handler.get("command") or "",
                        "timeout": timeout,
                        "class": "vendor-managed" if vendor else "fixable",
                        "reason": (
                            "vendor telemetry agent re-registers this hook; "
                            "async/timeout edits are reverted"
                            if vendor
                            else f"synchronous hook with timeout <= {max_sync_timeout}s "
                            "blocks every matching tool call"
                        ),
                    }
                )
    return findings


def apply_fix(settings_path: Path, findings: list) -> int:
    """Set async=true on fixable handlers; return the number fixed."""
    fixable = [f for f in findings if f["class"] == "fixable"]
    if not fixable:
        return 0
    config = json.loads(settings_path.read_text(encoding="utf-8"))
    wanted = {
        (f["event"], f["command"], f.get("timeout")) for f in fixable
    }
    fixed = 0
    for event, definitions in config.get("hooks", {}).items():
        if event not in TOOL_EVENTS or not isinstance(definitions, list):
            continue
        for definition in definitions:
            if not isinstance(definition, dict) or definition.get("async") is True:
                continue
            for handler in definition.get("hooks") or []:
                if not isinstance(handler, dict) or handler.get("async") is True:
                    continue
                key = (event, handler.get("command") or "", handler.get("timeout"))
                if key in wanted:
                    handler["async"] = True
                    fixed += 1
    if fixed:
        backup = settings_path.with_name(
            f"{settings_path.name}.hook-health.bak-{time.strftime('%Y%m%dT%H%M%S')}"
        )
        backup.write_bytes(settings_path.read_bytes())
        payload = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
        fd, tmp = tempfile.mkstemp(dir=str(settings_path.parent), prefix=".hook-health-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, settings_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return fixed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect synchronous host hooks that block unattended SDD runs."
    )
    parser.add_argument("--project", default=".", help="project directory whose "
                        "project-level settings are scanned (default: .)")
    parser.add_argument("--settings", action="append", default=[], metavar="PATH",
                        help="explicit settings file (repeatable); suppresses discovery")
    parser.add_argument("--max-sync-timeout", type=int, default=DEFAULT_MAX_SYNC_TIMEOUT,
                        help="flag synchronous tool-event hooks at or below this "
                             "timeout (default: 5)")
    parser.add_argument("--fix", action="store_true",
                        help="set async=true on fixable hooks (backup written first)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if args.settings:
        paths = [Path(p).expanduser() for p in args.settings]
        missing = [str(p) for p in paths if not p.is_file()]
        if missing:
            print(f"hook-health: settings not found: {', '.join(missing)}", file=sys.stderr)
            return 2
    else:
        paths = default_settings_paths(project)

    findings = []
    for path in paths:
        try:
            findings.extend(collect_findings(path, args.max_sync_timeout))
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 2

    fixed = 0
    if args.fix:
        by_file = {}
        for finding in findings:
            by_file.setdefault(finding["file"], []).append(finding)
        for file, items in by_file.items():
            fixed += apply_fix(Path(file), items)
        findings = [f for f in findings if f["class"] != "fixable"]
        for finding in findings:
            finding["reason"] += " (fix not attempted)"

    unresolved = len(findings)
    summary = {
        "files_scanned": [str(p) for p in paths],
        "findings": len(findings) + fixed,
        "fixed": fixed,
        "unresolved": unresolved,
    }

    if args.json:
        print(json.dumps({"summary": summary, "findings": findings}, indent=2,
                         ensure_ascii=False))
    else:
        print(f"hook-health: scanned {len(paths)} settings file(s), "
              f"max sync timeout {args.max_sync_timeout}s")
        if not findings and not fixed:
            print("hook-health: clean — no blocking hook risk found")
        for finding in findings:
            print(f"  [{finding['class']}] {finding['file']}")
            print(f"      {finding['event']} matcher={finding['matcher']}")
            print(f"      command: {finding['command']}")
            print(f"      timeout: {finding['timeout']}  reason: {finding['reason']}")
        if fixed:
            print(f"hook-health: fixed {fixed} hook(s) by setting async=true "
                  "(backup written next to each settings file)")
        if findings:
            print("hook-health: vendor-managed hooks cannot be fixed from settings; "
                  "options: (a) ask the vendor agent to support async, "
                  "(b) disable/stop that agent, (c) run the unattended agent with "
                  "an isolated config dir, (d) accept the timeout cost")

    return 10 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
