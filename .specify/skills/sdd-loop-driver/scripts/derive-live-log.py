#!/usr/bin/env python3
"""Derive an incrementally growing live log from a raw stream-json NDJSON feed.

Each meaningful non-terminal event yields one prefixed progress line carrying
its raw event sequence and receive timestamp. The terminal ``result`` text is
appended verbatim at EOF, so the last non-empty line equals the stage sentinel
only when the CLI emitted a terminal result. Malformed lines are tolerated and
never fabricate progress or completion.

``--finish`` reads the raw stream once and prints only the terminal result text
(exit 1 when no result exists), for runner recovery after a derivation failure.

Python >= 3.8, standard library only.
"""

import argparse
import json
import sys
import time


def one_line(text):
    return " ".join(str(text).split())


def progress_text(event):
    event_type = event.get("type")
    if event_type == "system":
        return "system:%s" % (event.get("subtype") or "event")
    if event_type == "assistant":
        message = event.get("message")
        texts = []
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
            elif isinstance(content, str):
                texts.append(content)
            if not texts:
                texts.append(json.dumps(message, ensure_ascii=False))
        return "assistant: %s" % one_line(" ".join(str(item) for item in texts))
    if event_type in ("tool_use", "tool_result"):
        name = event.get("name") or event.get("tool_name") or ""
        return "%s: %s" % (event_type, one_line(name))
    if event_type:
        return one_line(event_type)
    return ""


def result_text_of(event):
    text = event.get("result")
    return text if isinstance(text, str) else None


def read_lines(stream):
    while True:
        line = stream.readline()
        if line == "":
            return
        yield line


def derive(stream, out):
    sequence = 0
    result = None
    for raw in read_lines(stream):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        sequence += 1
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result":
            text = result_text_of(event)
            if text is not None:
                result = text
            continue
        line = progress_text(event)
        if not line:
            continue
        out.write("[evt=%d at=%.3f] %s\n" % (sequence, time.time(), line))
        out.flush()
    if result is not None:
        out.write(result)
        if not result.endswith("\n"):
            out.write("\n")
        out.flush()


def finish(stream, out):
    result = None
    for raw in read_lines(stream):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            text = result_text_of(event)
            if text is not None:
                result = text
    if result is None:
        return 1
    out.write(result)
    if not result.endswith("\n"):
        out.write("\n")
    out.flush()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Derive a compact live log from a raw stream-json NDJSON stream.")
    parser.add_argument("--events", help="raw NDJSON file (default: stdin)")
    parser.add_argument("--out", help="live log output file (default: stdout)")
    parser.add_argument("--finish", action="store_true",
                        help="print only the terminal result text from the raw stream")
    args = parser.parse_args(argv)

    close_in = close_out = False
    source = sys.stdin
    sink = sys.stdout
    try:
        if args.events:
            source = open(args.events, "r", encoding="utf-8", errors="replace")
            close_in = True
        if args.out:
            sink = open(args.out, "w", encoding="utf-8")
            close_out = True
        if args.finish:
            return finish(source, sink)
        derive(source, sink)
        return 0
    except OSError as error:
        print("derive-live-log: %s" % error, file=sys.stderr)
        return 2
    finally:
        if close_in:
            source.close()
        if close_out:
            sink.close()


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

_SIG_SCRIPT = '.specify/skills/sdd-loop-driver/scripts/derive-live-log.py'
_SIG_DECLARED = ('--events', '--finish', '--out')
_SIG_HELP = (
    'usage: derive-live-log.py [options]\n'
    'options:\n'
    '  --events\n  --finish\n  --out\n'
    '  -h, --help    print this help and exit\n'
    '  --version     print the script name and the framework version, then exit\n'
    +
    'side-effects:' + ' ' + 'writes only through the options it documents; a flag-only invocation writes nothing' + '\n'
    +
    'exit-codes:' + ' ' + '0 success; 1 a documented check failed; 2 argument or environment error' + '\n'
)


def _sig_guard(argv):
    # Deferred on purpose: the module's TOP-LEVEL imports stay standard-library only
    # (the runner's live-log derivation must remain self-contained); the helper is the
    # rule's owner and is used only when a flag is actually judged.
    import script_interface_cli as _sig  # noqa: E402 -- the rule's only Python owner
    # Answer the flags and reject an undeclared option before any parsing or write.
    # RULES are asked of the owner (script_interface_cli.guard_argv), never restated:
    # the declared vocabulary and the flag forms are its, and C-9 (a recognized option
    # never rescues an unrecognized one) is its judgement. What stays local is the help
    # BODY, because its operand sentence is this script's own.
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
