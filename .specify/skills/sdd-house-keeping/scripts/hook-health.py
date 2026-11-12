#!/usr/bin/env python3
"""Host hook health check for unattended SDD runs (sdd-house-keeping H4).

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


#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
_VERSION_SOURCE = "pyproject.toml"
_VERSION_QUOTES = chr(39) + chr(34)
_MAX_UPWARD_LEVELS = 12


def _bridge_version(start):
    _here = start.resolve()
    for _ in range(_MAX_UPWARD_LEVELS + 1):
        if (_here / _VERSION_SOURCE).is_file() and (_here / ".git").exists():
            try:
                _text = (_here / _VERSION_SOURCE).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return "unknown"
            _in_project = False
            for _raw in _text.splitlines():
                _line = _raw.strip()
                if not _line or _line.startswith("#"):
                    continue
                if _line.startswith("[") and _line.endswith("]"):
                    _in_project = _line == "[project]"
                    continue
                if not _in_project:
                    continue
                _key, _sep, _value = _line.partition("=")
                if _sep and _key.strip() == "version":
                    _value = _value.strip()
                    if len(_value) >= 2 and _value[0] == _value[-1] and _value[0] in _VERSION_QUOTES:
                        _value = _value[1:-1]
                    return _value or "unknown"
            return "unknown"
        if _here.parent == _here:
            return "unknown"
        _here = _here.parent
    return "unknown"

def _bridge_main():
    import sys as _bridge_sys
    from pathlib import Path as _bridge_path

    _argv = list(_bridge_sys.argv[1:])
    if "--version" not in _argv:
        return
    if "--" in _argv and _argv.index("--version") > _argv.index("--"):
        return
    _invoked = _bridge_sys.argv[0] if _bridge_sys.argv[0] else "."
    _name = _bridge_path(_invoked).name or "script"
    print("%s %s" % (_name, _bridge_version(_bridge_path(_invoked).resolve().parent)))
    raise SystemExit(0)


_bridge_main()
del _bridge_main
# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its executable form by
# `.specify/scripts/python/script_interface_cli.py`. This block owns no rule of its own.)
import sys as _sig_sys
import pathlib as _sig_pathlib

_SIG_OWNER = _sig_pathlib.Path(__file__).resolve().parent
while not ((_SIG_OWNER / 'pyproject.toml').is_file()
           and (_SIG_OWNER / '.git').exists()) and _SIG_OWNER.parent != _SIG_OWNER:
    _SIG_OWNER = _SIG_OWNER.parent
_SIG_OWNER = str(_SIG_OWNER / 'scripts' / 'python')
if _SIG_OWNER not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_OWNER)

_SIG_SCRIPT = '.specify/skills/sdd-house-keeping/scripts/hook-health.py'
_SIG_DECLARED = ('--fix', '--json', '--max-sync-timeout', '--project', '--settings')
_SIG_HELP = (
    'usage: hook-health.py [options]\n'
    'options:\n'
    '  --fix\n  --json\n  --max-sync-timeout\n  --project\n  --settings\n'
    '  -h, --help    print this help and exit\n'
    '  --version     print the script name and the framework version, then exit\n'
    +
    'side-effects:' + ' ' + 'writes only through the options it documents; a flag-only invocation writes nothing' + '\n'
    +
    'exit-codes:' + ' ' + '0 success; 1 a documented check failed; 2 argument or environment error' + '\n'
)


def _sig_guard(argv):
    # Answer the flags and reject an undeclared option before any parsing or write.
    # RULES are asked of the owner (script_interface_cli.guard_argv), never restated:
    # the declared vocabulary and the flag forms are its, and C-9 (a recognized option
    # never rescues an unrecognized one) is its judgement. What stays local is the help
    # BODY, because its operand sentence is this script's own.
    try:
        import script_interface_cli as _sig  # noqa: E402 -- deferred: a copied script may lack it
    except ImportError:  # skill-local or sandbox copy: the module's own parser still runs
        return list(argv)
    line = list(argv)
    try:
        _sig.guard_argv(line, declared=_SIG_DECLARED)
    except SystemExit as answered:  # what guard_argv raises; _sig_sys.exit IS SystemExit
        if answered.code == 0:
            raise
        # The owner prints the rejection line and this script's help body is appended after
        # it, so the reader sees the vocabulary and not only the refusal.
        _sig_sys.stderr.write(_SIG_HELP)
        raise _sig_sys.exit(answered.code)
    stop = line.index('--') if '--' in line else len(line)
    if '-h' in line[:stop] or '--help' in line[:stop]:
        _sig_sys.stdout.write(_SIG_HELP)
        raise _sig_sys.exit(0)
    return line

if __name__ == "__main__":
    _sig_sys.argv = [_sig_sys.argv[0]] + _sig_guard(_sig_sys.argv[1:])
# script-interface:86:end

if __name__ == "__main__":
    sys.exit(main())
