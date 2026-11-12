#!/usr/bin/env python3
"""Remote command transport for the ssh-utils skill.

Every non-interactive invocation carries ``-o RemoteCommand=none``. OpenSSH
refuses a command line when the host's ssh_config already presets
``RemoteCommand`` ("Cannot execute command-line and remote command"), so the
neutralizer is not optional.

Exit codes: 0 remote success; 1-254 remote exit code; 2 usage error;
124 local timeout (the remote process may still be running); 255 ssh
transport failure.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HOST_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._@:-]*\Z")
USER_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")
MODE_RE = re.compile(r"\A[0-7]{3,4}\Z")
INTERPRETERS = {".py": "python3", ".sh": "bash", ".bash": "bash"}

EXIT_TIMEOUT = 124
EXIT_USAGE = 2


def quote_path(path: str) -> str:
    """POSIX-quote a remote path while keeping a leading ``~`` expandable."""
    if path == "~":
        return '"$HOME"'
    if path.startswith("~/"):
        return '"$HOME"/' + shlex.quote(path[2:])
    return shlex.quote(path)


def ssh_base(args: argparse.Namespace) -> list[str]:
    argv = [
        "ssh",
        "-o", "RemoteCommand=none",
        "-o", "ConnectTimeout=%d" % args.connect_timeout,
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=4",
        "-o", "RequestTTY=%s" % ("force" if args.tty else "no"),
        "-o", "BatchMode=%s" % ("no" if args.allow_password else "yes"),
    ]
    if args.tty:
        argv.append("-t")
    if args.config:
        argv += ["-F", args.config]
    if args.port:
        argv += ["-p", str(args.port)]
    if args.identity:
        argv += ["-i", args.identity]
    for option in args.ssh_option:
        argv += ["-o", option]
    argv.append(args.host)
    return argv


def compose_remote(args: argparse.Namespace) -> str:
    if args.cmd is not None:
        inner = args.cmd
    elif args.script:
        suffix = Path(args.script).suffix.lower()
        interpreter = args.script_interpreter or INTERPRETERS.get(suffix, "sh")
        parts = [interpreter, "-"] + [shlex.quote(a) for a in args.script_arg]
        inner = " ".join(parts)
    elif args.upload:
        remote = args.remote
        if remote.endswith("/"):
            remote += Path(args.upload).name
        inner = "cat > %s" % quote_path(remote)
        if args.mode:
            inner += " && chmod %s %s" % (args.mode, quote_path(remote))
    elif args.download:
        inner = "cat %s" % quote_path(args.download)
    else:  # pragma: no cover - argparse enforces one action
        raise SystemExit(EXIT_USAGE)
    if args.cwd:
        inner = "cd %s && %s" % (quote_path(args.cwd), inner)
    if args.user:
        return "su - %s -c %s" % (shlex.quote(args.user), shlex.quote(inner))
    return inner


def action_name(args: argparse.Namespace) -> str:
    for name in ("check", "cmd", "script", "upload", "download"):
        if getattr(args, name):
            return name
    return "unknown"


def validate(args: argparse.Namespace) -> str | None:
    if not HOST_RE.match(args.host):
        return "invalid host alias %r (expected [A-Za-z0-9][A-Za-z0-9._@:-]*)" % args.host
    if args.user and not USER_RE.match(args.user):
        return "invalid remote user %r" % args.user
    if args.mode and not MODE_RE.match(args.mode):
        return "invalid --mode %r (expected a 3-4 digit octal mode)" % args.mode
    if args.timeout < 0 or args.connect_timeout < 0:
        return "--timeout and --connect-timeout must be non-negative"
    if args.check and (args.user or args.cwd or args.script or args.upload
                       or args.download or args.mode):
        return "--check inspects ssh_config only; drop execution options"
    if args.upload and not args.remote:
        return "--upload requires --remote <path>"
    if args.download and not args.local:
        return "--download requires --local <path>"
    if args.remote and not args.upload:
        return "--remote is only valid with --upload"
    if args.local and not args.download:
        return "--local is only valid with --download"
    if args.script and not Path(args.script).is_file():
        return "script not found: %s" % args.script
    if args.upload and not Path(args.upload).is_file():
        return "upload source not found: %s" % args.upload
    if args.stdin_file and not Path(args.stdin_file).is_file():
        return "stdin file not found: %s" % args.stdin_file
    if args.download:
        parent = Path(args.local).expanduser().parent
        if not parent.is_dir():
            return "download parent directory does not exist: %s" % parent
    for option in args.ssh_option:
        key, _, value = option.partition("=")
        if key.strip().lower() == "remotecommand" and value.strip().lower() != "none":
            return ("refusing --ssh-option %r: this wrapper requires "
                    "RemoteCommand=none" % option)
    return None


def decode(data: bytes | None) -> str:
    return (data or b"").decode("utf-8", errors="replace")


def emit(args: argparse.Namespace, payload: dict, text_lines: list[str]) -> None:
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for line in text_lines:
            print(line)


def run_check(args: argparse.Namespace) -> int:
    argv = ["ssh", "-G"]
    if args.config:
        argv += ["-F", args.config]
    if args.port:
        argv += ["-p", str(args.port)]
    if args.identity:
        argv += ["-i", args.identity]
    argv.append(args.host)
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return EXIT_USAGE
    fields: dict[str, str] = {}
    identities: list[str] = []
    for line in proc.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "identityfile":
            identities.append(value.strip())
        elif key:
            fields.setdefault(key, value.strip())
    remote_command = fields.get("remotecommand", "")
    preset = bool(remote_command) and remote_command.lower() != "none"
    payload = {
        "host": args.host,
        "hostname": fields.get("hostname", ""),
        "user": fields.get("user", ""),
        "port": fields.get("port", ""),
        "identityfile": identities,
        "proxyjump": fields.get("proxyjump", ""),
        "remoteCommand": remote_command,
        "remoteCommandPreset": preset,
        "mitigation": "-o RemoteCommand=none is applied automatically on execution",
    }
    lines = [
        "host: %s" % payload["host"],
        "hostname: %s" % payload["hostname"],
        "user: %s" % payload["user"],
        "port: %s" % payload["port"],
        "identityfile: %s" % (", ".join(identities) or "-"),
        "proxyjump: %s" % (payload["proxyjump"] or "-"),
        "remotecommand: %s" % (remote_command or "-"),
    ]
    if preset:
        lines.append("warning: ssh_config presets RemoteCommand=%r; direct "
                     "`ssh host \"cmd\"` would fail. ssh-exec.py neutralizes it."
                     % remote_command)
    emit(args, payload, lines)
    return 0


def run_exec(args: argparse.Namespace) -> int:
    remote = compose_remote(args)
    argv = ssh_base(args) + [remote]
    if args.dry_run:
        payload = {
            "host": args.host,
            "action": action_name(args),
            "remoteCommand": remote,
            "argv": argv,
            "stdin": args.script or args.upload or args.stdin_file,
        }
        emit(args, payload, [" ".join(shlex.quote(part) for part in argv)])
        return 0

    stdin_fh = subprocess.DEVNULL
    stdout_fh = subprocess.PIPE
    opened_stdin = None
    opened_stdout = None
    bytes_moved = 0
    try:
        if args.script or args.upload or args.stdin_file:
            source = args.script or args.upload or args.stdin_file
            opened_stdin = open(source, "rb")
            stdin_fh = opened_stdin
            bytes_moved = Path(source).stat().st_size
        if args.download:
            opened_stdout = open(args.local, "wb")
            stdout_fh = opened_stdout
        started = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                stdin=stdin_fh,
                stdout=stdout_fh,
                stderr=subprocess.PIPE,
                timeout=args.timeout or None,
            )
        except FileNotFoundError:
            sys.stderr.write("ssh-exec: ssh client not found on PATH\n")
            return 127
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            sys.stderr.write(
                "ssh-exec: local timeout after %ss; the remote process may "
                "still be running\n" % args.timeout)
            payload = {
                "host": args.host,
                "action": action_name(args),
                "remoteCommand": remote,
                "exitCode": EXIT_TIMEOUT,
                "durationMs": duration_ms,
                "stdout": decode(exc.stdout),
                "stderr": decode(exc.stderr),
            }
            emit(args, payload, [])
            return EXIT_TIMEOUT
        duration_ms = int((time.monotonic() - started) * 1000)
    finally:
        if opened_stdin:
            opened_stdin.close()
        if opened_stdout:
            opened_stdout.close()

    returncode = proc.returncode
    if returncode < 0:
        returncode = 128 - returncode
    payload = {
        "host": args.host,
        "action": action_name(args),
        "remoteCommand": remote,
        "exitCode": returncode,
        "durationMs": duration_ms,
        "stdout": "" if args.download else decode(proc.stdout),
        "stderr": decode(proc.stderr),
    }
    if args.download:
        payload["bytesWritten"] = Path(args.local).stat().st_size
    elif args.script or args.upload:
        payload["bytesSent"] = bytes_moved
    if args.json:
        emit(args, payload, [])
    else:
        if not args.download and proc.stdout:
            sys.stdout.buffer.write(proc.stdout)
            sys.stdout.flush()
        if proc.stderr:
            sys.stderr.buffer.write(proc.stderr)
            sys.stderr.flush()
    return returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run remote commands over ssh with RemoteCommand=none "
                    "and deterministic quoting.",
    )
    parser.add_argument("--host", required=True, help="ssh alias or host")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true",
                        help="inspect the effective ssh_config (ssh -G)")
    action.add_argument("--cmd", help="remote shell command to run")
    action.add_argument("--script", help="local script streamed to the remote "
                                         "interpreter over stdin")
    action.add_argument("--upload", metavar="LOCAL",
                        help="local file streamed to --remote")
    action.add_argument("--download", metavar="REMOTE",
                        help="remote file streamed to --local")
    parser.add_argument("--user", help="remote login user (wraps with su -)")
    parser.add_argument("--cwd", help="remote working directory")
    parser.add_argument("--script-arg", action="append", default=[],
                        help="script argument (repeatable; use --script-arg=--flag)")
    parser.add_argument("--script-interpreter",
                        help="interpreter for --script (default: by suffix)")
    parser.add_argument("--stdin-file", help="stdin for --cmd")
    parser.add_argument("--remote", help="remote path for --upload")
    parser.add_argument("--local", help="local path for --download")
    parser.add_argument("--mode", help="chmod mode applied after --upload")
    parser.add_argument("--port", type=int, help="ssh port")
    parser.add_argument("--identity", help="identity file")
    parser.add_argument("--config", help="ssh_config file (-F)")
    parser.add_argument("--ssh-option", action="append", default=[],
                        help="extra -o KEY=VALUE (repeatable)")
    parser.add_argument("--connect-timeout", type=int, default=10,
                        help="ConnectTimeout seconds (default 10)")
    parser.add_argument("--timeout", type=int, default=0,
                        help="local timeout seconds for the whole run "
                             "(default 0 = no limit)")
    parser.add_argument("--allow-password", action="store_true",
                        help="allow password prompts (BatchMode=no)")
    parser.add_argument("--tty", action="store_true", help="allocate a TTY")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the ssh argv without connecting")
    parser.add_argument("--json", action="store_true", help="JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    problem = validate(args)
    if problem:
        sys.stderr.write("ssh-exec: %s\n" % problem)
        return EXIT_USAGE
    if args.check:
        return run_check(args)
    return run_exec(args)


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

_SIG_SCRIPT = '.specify/skills/ssh-utils/scripts/ssh-exec.py'
_SIG_DECLARED = ('--allow-password', '--check', '--cmd', '--config', '--connect-timeout', '--cwd', '--download', '--dry-run', '--host', '--identity', '--json', '--local', '--mode', '--port', '--remote', '--script', '--script-arg', '--script-interpreter', '--ssh-option', '--stdin-file', '--timeout', '--tty', '--upload', '--user')
_SIG_HELP = (
    'usage: ssh-exec.py [options]\n'
    'options:\n'
    '  --allow-password\n  --check\n  --cmd\n  --config\n  --connect-timeout\n  --cwd\n  --download\n  --dry-run\n  --host\n  --identity\n  --json\n  --local\n  --mode\n  --port\n  --remote\n  --script\n  --script-arg\n  --script-interpreter\n  --ssh-option\n  --stdin-file\n  --timeout\n  --tty\n  --upload\n  --user\n'
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
