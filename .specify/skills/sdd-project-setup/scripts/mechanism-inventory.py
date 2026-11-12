#!/usr/bin/env python3
"""mechanism-inventory — spec-kit 安装机制的确定性盘点脚本（sdd-project-setup S1）.

只读扫描 <project>/.specify/，输出机制矩阵与状态分级；无副作用。
用法:
  mechanism-inventory.py --project <path> [--json]
退出码: 0 成功 / 2 参数或路径错误
分级判据见 references/setup-recipes.md「状态分级判据」。
"""
import argparse
import json
import os
import sys

COMPAT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "QODER.md",
    ".github/copilot-instructions.md",
]


def check_compat(project: str) -> dict:
    """兼容链接核验：指向 .specify/instructions.md 且未断。"""
    links = {}
    for name in COMPAT_FILES:
        p = os.path.join(project, name)
        if os.path.islink(p):
            target = os.path.realpath(p)
            intact = os.path.exists(target)
            links[name] = {"type": "symlink", "target": target, "intact": intact}
        elif os.path.exists(p):
            links[name] = {"type": "file"}
        else:
            links[name] = {"type": "missing"}
    return links


def grade(matrix: dict, compat: dict) -> str:
    if not matrix["specify_dir"]:
        return "absent"
    if not matrix["const"] or (not matrix["skills"] and not matrix["feat"]):
        return "degraded"
    missing = sum(
        1 for k in ("const", "feat", "skills", "tmpl") if not matrix[k]
    )
    broken_link = any(
        v.get("type") == "symlink" and not v.get("intact") for v in compat.values()
    )
    if missing >= 2 or broken_link:
        return "partial"
    if missing == 0:
        return "complete"
    return "partial"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="project root path")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    sp = os.path.join(args.project, ".specify")
    if not os.path.isdir(args.project):
        print(f"error: project not found: {args.project}", file=sys.stderr)
        return 2

    def exists(rel: str) -> bool:
        return os.path.exists(os.path.join(sp, rel))

    skills_dir = os.path.join(sp, "skills")
    skills_count = (
        len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
        if os.path.isdir(skills_dir)
        else 0
    )
    specs_dir = os.path.join(sp, "specs")
    specs_count = (
        len(os.listdir(specs_dir)) if os.path.isdir(specs_dir) else 0
    )

    src = {}
    source_path = os.path.join(sp, "source.json")
    if os.path.isfile(source_path):
        try:
            with open(source_path) as f:
                src = json.load(f)
        except (OSError, ValueError):
            src = {"parse_error": True}

    matrix = {
        "specify_dir": os.path.isdir(sp),
        "const": exists("constitution.md"),
        "feat": exists("features.md") and os.path.isdir(os.path.join(sp, "features")),
        "gloss": exists("glossary.md"),
        "fb": os.path.isdir(os.path.join(sp, ".specify/memory/feedback")),
        "reg": exists("register.md"),
        "kb": os.path.isdir(os.path.join(sp, ".specify/memory/knowledge")),
        "session": os.path.isdir(os.path.join(sp, ".specify/memory/session")),
        "tools": exists("tools.md"),
        "skills": skills_count > 0,
        "skills_count": skills_count,
        "tmpl": os.path.isdir(os.path.join(sp, "templates")),
        "specs": specs_count > 0,
        "specs_count": specs_count,
        "src": bool(src),
    }
    compat = check_compat(args.project)
    g = grade(matrix, compat)

    if args.json:
        print(json.dumps({"matrix": matrix, "compat": compat, "grade": g, "source": src}, ensure_ascii=False, indent=1))
        return 0

    dims = ["const", "feat", "gloss", "fb", "reg", "kb", "session", "tools", "skills", "tmpl", "src"]
    line = " ".join(f"{d}:{'ok' if matrix[d] else '-'}" for d in dims)
    print(f"grade={g} {line} skills={matrix['skills_count']} specs={matrix['specs_count']}")
    broken = [k for k, v in compat.items() if v.get("type") == "symlink" and not v.get("intact")]
    if broken:
        print(f"compat-broken: {','.join(broken)}")
    if src:
        v = src.get("version") or src.get("spec_kit_version") or "?"
        print(f"source: version={v} stamped={src.get('stamped_at', '?')}")
    return 0


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

_SIG_SCRIPT = '.specify/skills/sdd-project-setup/scripts/mechanism-inventory.py'
_SIG_DECLARED = ('--json', '--project')
_SIG_HELP = (
    'usage: mechanism-inventory.py [options]\n'
    'options:\n'
    '  --json\n  --project\n'
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
