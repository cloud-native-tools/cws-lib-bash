#!/usr/bin/env python3
"""ssh_config_insert.py — insert a Host entry into an ssh config respecting
first-match-wins ordering.

Why this needs a program and not eyeballing
-------------------------------------------
ssh_config resolves every option independently by **first obtained value**:
when several `Host`/`Match` blocks match the same alias, the value from the
block that appears *earliest in read order* wins and later same-name options
are silently discarded. A `Host <alias>` block placed after a wildcard such as

    Host workspace_*
      User root

resolves to `user root`, not the `User git` written inside the specific block.
The failure is silent — the connection still succeeds, just as the wrong user.

This script therefore computes the insertion point from the block order, and
verifies the outcome with `ssh -G` (the only authoritative view of the
effective configuration) rather than by re-reading the file.

Read order across `Include`
---------------------------
`Include` directives are expanded in place, so a conflicting block in the main
config or in an earlier-included file outranks anything this script writes into
a later file. That cannot be fixed by reordering within one file; `--verify`
detects it and reports which value won so the operator can act.

Usage
-----
    ssh_config_insert.py --config PATH --alias NAME --hostname HOST [options]

Modes: default = converge (insert when absent), --check = observe only,
--verify = assert the effective resolution, --dry-run = print without writing.
"""
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

_SIG_SCRIPT = '.specify/skills/git-utils/scripts/ssh_config_insert.py'
_SIG_DECLARED = ('--alias', '--check', '--comment', '--config', '--dry-run', '--hostname', '--identities-only', '--identity-file', '--indent', '--option', '--port', '--update', '--user', '--verify')
_SIG_HELP = (
    'usage: ssh_config_insert.py [options]\n'
    'options:\n'
    '  --alias\n  --check\n  --comment\n  --config\n  --dry-run\n  --hostname\n  --identities-only\n  --identity-file\n  --indent\n  --option\n  --port\n  --update\n  --user\n  --verify\n'
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


import argparse
import fnmatch
import os
import re
import subprocess
import sys

BLOCK_RE = re.compile(r'^\s*(Host|Match)\s+(.*?)\s*$', re.IGNORECASE)
OPTION_RE = re.compile(r'^\s*([A-Za-z]+)\s*(.*?)\s*$')

# Options that ACCUMULATE across every matching block instead of taking the
# first obtained value. `IdentityFile` is the one that matters here: ssh_config(5)
# says "It is possible to have multiple identity files specified in
# configuration files; all these identities will be tried in sequence", and
# `ssh -G` prints one line per accumulated value.
#
# Consequence: a block declaring only these options is NOT an ordering
# conflict, and verification must treat them as sets, not scalars.
# Anything not listed here is assumed first-value-wins — the safe direction,
# since over-detecting a conflict only makes us insert earlier (higher priority).
LIST_OPTIONS = frozenset([
    'identityfile', 'certificatefile', 'localforward', 'remoteforward',
    'dynamicforward', 'sendenv', 'setenv', 'globalknownhostsfile',
    'userknownhostsfile',
])


def parse_blocks(lines):
    """Split config lines into (kind, patterns, start_idx, end_idx, options).

    kind is 'Host', 'Match', or 'preamble'. end_idx is exclusive.
    options maps lowercased option name -> list of raw values.
    """
    blocks = []
    starts = [i for i, ln in enumerate(lines) if BLOCK_RE.match(ln)]
    if not starts:
        return blocks

    if starts[0] > 0:
        blocks.append({
            'kind': 'preamble', 'patterns': [], 'start': 0,
            'end': starts[0], 'options': {}, 'raw': lines[0:starts[0]],
        })

    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else len(lines)
        m = BLOCK_RE.match(lines[s])
        kind, pat = m.group(1), m.group(2)
        opts = {}
        for ln in lines[s + 1:e]:
            stripped = ln.strip()
            if not stripped or stripped.startswith('#'):
                continue
            om = OPTION_RE.match(ln)
            if om:
                opts.setdefault(om.group(1).lower(), []).append(om.group(2))
        blocks.append({
            'kind': kind.lower(), 'patterns': pat.split(), 'start': s,
            'end': e, 'options': opts, 'raw': lines[s:e],
        })
    return blocks


def host_pattern_matches(patterns, alias):
    """ssh Host pattern semantics: match if any positive glob matches and no
    negated (!) glob matches."""
    positives = [p for p in patterns if not p.startswith('!')]
    negatives = [p[1:] for p in patterns if p.startswith('!')]
    if any(fnmatch.fnmatchcase(alias, n) for n in negatives):
        return False
    return any(fnmatch.fnmatchcase(alias, p) for p in positives)


def match_block_may_apply(block, alias):
    """Conservative verdict for `Match` blocks.

    A Match block with no `host` criterion can apply to any alias. When a `host`
    criterion is present, test it as a glob list. `exec`/`canonical`/`all` and
    other criteria cannot be evaluated statically, so the block is treated as
    potentially applying — inserting earlier is always safe under
    first-match-wins, and a false positive only costs specificity.
    """
    hosts = block['options'].get('host')
    if not hosts:
        return True
    for value in hosts:
        if host_pattern_matches(value.split(), alias):
            return True
    return False


def block_matches_alias(block, alias):
    if block['kind'] == 'host':
        return host_pattern_matches(block['patterns'], alias)
    if block['kind'] == 'match':
        return match_block_may_apply(block, alias)
    return False


def find_exact_block(blocks, alias):
    """A block whose pattern list contains the literal alias (an exact entry
    already exists — never create a second one)."""
    for b in blocks:
        if b['kind'] == 'host' and alias in b['patterns']:
            return b
    return None


def block_comment_start(lines, idx):
    """Walk back over the comment lines attached to the block starting at idx.

    A block's leading comments belong to that block: inserting between the
    comment and its `Host` line silently re-parents the comment onto the new
    entry, which is how an explanatory note like "this wildcard must stay last"
    ends up sitting above an unrelated host.

    Stops at a blank line, a non-comment line, or the top of file. When the run
    reaches line 0 the comments are a file header, not a block comment, so the
    original index is returned to keep the header at the top.
    """
    j = idx - 1
    start = idx
    while j >= 0 and lines[j].strip().startswith('#'):
        start = j
        j -= 1
    return idx if start == 0 else start


def find_insert_index(blocks, alias, declared_options):
    """Return the line index to insert before: the earliest block that matches
    the alias AND declares at least one *first-value-wins* option we also
    declare.

    List-type options (see LIST_OPTIONS) are excluded: they accumulate across
    all matching blocks, so their relative order cannot make our value lose.

    Returns None when nothing conflicts (append at end of file).
    """
    wanted = {o.lower() for o in declared_options} - LIST_OPTIONS
    if not wanted:
        return None
    for b in blocks:
        if b['kind'] == 'preamble':
            continue
        if not block_matches_alias(b, alias):
            continue
        if wanted & (set(b['options'].keys()) - LIST_OPTIONS):
            return b['start']
    return None


def render_entry(alias, options, comment=None, indent='  '):
    lines = []
    if comment:
        for c in comment:
            lines.append('# %s' % c)
    lines.append('Host %s' % alias)
    for key, value in options:
        lines.append('%s%s %s' % (indent, key, value))
    return lines


def ssh_g(alias):
    """Effective configuration as ssh itself resolves it — authoritative.

    Returns (resolved, err). `resolved` maps lowercased keyword -> list of
    values, preserving order, because list-type options (IdentityFile etc.)
    legitimately appear several times.
    """
    try:
        out = subprocess.run(
            ['ssh', '-G', alias], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    if out.returncode != 0:
        return None, (out.stderr or out.stdout).strip()
    resolved = {}
    for ln in out.stdout.splitlines():
        parts = ln.split(' ', 1)
        if len(parts) == 2:
            resolved.setdefault(parts[0].lower(), []).append(parts[1])
    return resolved, None


def expand_home(value):
    """`ssh -G` prints IdentityFile values unexpanded ('~/.ssh/id_rsa')."""
    if value.startswith('~/'):
        return os.path.join(os.path.expanduser('~'), value[2:])
    return value


def main():
    ap = argparse.ArgumentParser(
        description='Insert a Host entry into an ssh config respecting '
                    'first-match-wins ordering.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True, help='ssh config file path')
    ap.add_argument('--alias', required=True, help='Host alias to create')
    ap.add_argument('--hostname', help='Hostname value (required when inserting)')
    ap.add_argument('--user', default=None, help='User value (e.g. git)')
    ap.add_argument('--port', default=None, help='Port value')
    ap.add_argument('--identity-file', action='append', default=[],
                    help='IdentityFile value (repeatable)')
    ap.add_argument('--identities-only', default=None, help='IdentitiesOnly value')
    ap.add_argument('--option', action='append', default=[], metavar='K=V',
                    help='extra option, repeatable (e.g. --option ServerAliveInterval=30)')
    ap.add_argument('--comment', action='append', default=[],
                    help='comment line above the Host entry (repeatable)')
    ap.add_argument('--indent', default='  ', help='indentation inside the block')
    ap.add_argument('--check', action='store_true', help='observe only, write nothing')
    ap.add_argument('--update', action='store_true',
                    help='also converge options of an already-present exact block')
    ap.add_argument('--verify', action='store_true',
                    help='assert effective resolution via `ssh -G`')
    ap.add_argument('--dry-run', action='store_true', help='print result, do not write')
    args = ap.parse_args()

    cfg = os.path.expanduser(args.config)
    if not os.path.isfile(cfg):
        print('ERROR: config not found: %s' % cfg, file=sys.stderr)
        return 2

    # Desired options, in the order they should be written.
    wanted = []
    if args.hostname:
        wanted.append(('Hostname', args.hostname))
    if args.port:
        wanted.append(('Port', args.port))
    if args.user:
        wanted.append(('User', args.user))
    if args.identities_only:
        wanted.append(('IdentitiesOnly', args.identities_only))
    for idf in args.identity_file:
        wanted.append(('IdentityFile', idf))
    for extra in args.option:
        if '=' not in extra:
            print('ERROR: --option must be K=V, got: %s' % extra, file=sys.stderr)
            return 2
        k, v = extra.split('=', 1)
        wanted.append((k, v))

    with open(cfg, 'r', encoding='utf-8') as fh:
        content = fh.read()
    lines = content.splitlines()
    blocks = parse_blocks(lines)

    exact = find_exact_block(blocks, args.alias)
    declared = [k for k, _ in wanted]

    print('config : %s' % cfg)
    print('alias  : %s' % args.alias)

    if exact:
        print('state  : exact Host block already present (lines %d-%d)'
              % (exact['start'] + 1, exact['end']))
        drift = []
        for key, value in wanted:
            have = exact['options'].get(key.lower())
            if have is None:
                drift.append('%s missing (want %s)' % (key, value))
            elif value not in have:
                drift.append('%s = %s (want %s)' % (key, ', '.join(have), value))
        if drift:
            print('drift  :')
            for d in drift:
                print('           - %s' % d)
            if not args.update:
                print('action : none (--update not given; existing block left intact)')
            elif args.check or args.dry_run:
                print('action : would converge %d option(s)' % len(drift))
            else:
                print('action : converging existing block in place')
                new_raw = []
                for ln in exact['raw']:
                    stripped = ln.strip()
                    if stripped and not stripped.startswith('#'):
                        om = OPTION_RE.match(ln)
                        if om and om.group(1).lower() in {k.lower() for k, _ in wanted}:
                            continue
                    new_raw.append(ln)
                for key, value in wanted:
                    new_raw.append('%s%s %s' % (args.indent, key, value))
                lines[exact['start']:exact['end']] = new_raw
                _write(cfg, lines, args.dry_run)
        else:
            print('drift  : none — declared options already match')
            print('action : none (idempotent)')
    else:
        idx = find_insert_index(blocks, args.alias, declared)
        if not wanted:
            print('ERROR: nothing to write — pass --hostname/--user/... ', file=sys.stderr)
            return 2
        if idx is None:
            print('state  : no conflicting block; appending at end of file')
            position = len(lines)
        else:
            owner = blocks_at(blocks, idx)
            print('state  : inserting BEFORE line %d  (%s %s)'
                 % (idx + 1, owner['kind'], ' '.join(owner['patterns'])))
            overlap = sorted(o for o in owner['options']
                             if o in {d.lower() for d in declared}
                             and o not in LIST_OPTIONS)
            print('reason : that block matches "%s" and declares %s — under '
                  'first-match-wins it would override ours'
                  % (args.alias, ', '.join(overlap)))
            # keep the conflicting block's own leading comments attached to it
            position = block_comment_start(lines, idx)
            if position != idx:
                print('note   : moved up to line %d so the %d comment line(s) '
                      'belonging to that block stay attached to it'
                      % (position + 1, idx - position))
            else:
                position = idx

        entry = render_entry(args.alias, wanted, args.comment or None, args.indent)
        if args.check or args.dry_run:
            print('action : would insert %d line(s) at line %d'
                  % (len(entry) + 1, position + 1))
            print('--- preview ---')
            for ln in entry:
                print(ln)
            print('---------------')
        else:
            new_lines = lines[:position] + entry + [''] + lines[position:]
            _write(cfg, new_lines, False)
            print('action : inserted at line %d' % (position + 1))

    if args.verify:
        return _verify(args)
    return 0


def blocks_at(blocks, idx):
    for b in blocks:
        if b['start'] == idx:
            return b
    return {'kind': '?', 'patterns': [], 'options': {}}


def _write(cfg, lines, dry_run):
    text = '\n'.join(lines)
    if not text.endswith('\n'):
        text += '\n'
    if dry_run:
        print('--- full result (dry-run, not written) ---')
        sys.stdout.write(text)
        return
    with open(cfg, 'w', encoding='utf-8') as fh:
        fh.write(text)


def _verify(args):
    """Assert the effective resolution. `ssh -G` is the only trustworthy view:
    it accounts for the whole Include chain and Match exec evaluation.

    Scalar options are compared against the FIRST value ssh reports (that is
    the one in force). List-type options are compared as sets, because every
    accumulated value is in force.
    """
    resolved, err = ssh_g(args.alias)
    if resolved is None:
        print('VERIFY : FAILED — `ssh -G %s` errored: %s' % (args.alias, err))
        return 4

    want = {}
    if args.hostname:
        want['hostname'] = args.hostname
    if args.user:
        want['user'] = args.user
    if args.port:
        want['port'] = str(args.port)
    if args.identities_only:
        want['identitiesonly'] = args.identities_only.lower()

    bad = []
    for key, value in sorted(want.items()):
        got_list = resolved.get(key) or []
        got = got_list[0] if got_list else None
        mark = 'OK  ' if got == value else 'FAIL'
        print('VERIFY : %s %-16s effective=%-28s wanted=%s'
              % (mark, key, got, value))
        if got != value:
            bad.append(key)

    effective_idf = [expand_home(v) for v in resolved.get('identityfile') or []]
    print('VERIFY : INFO %-16s effective=%s'
          % ('identityfile', ', '.join(effective_idf) or '(none)'))
    if args.identity_file:
        wanted_idf = {expand_home(v) for v in args.identity_file}
        missing = sorted(wanted_idf - set(effective_idf))
        if missing:
            print('VERIFY : FAIL identityfile — declared key(s) absent from the '
                  'effective list: %s' % ', '.join(missing))
            print('         IdentityFile accumulates across all matching blocks '
                  '(it is NOT first-value-wins), so an absent value means the '
                  'entry was not written, or a `Match`/negated `Host !pattern` '
                  'block excluded this alias.')
            bad.append('identityfile')
        else:
            print('VERIFY : OK   %-16s all declared key(s) present (list-type '
                  'option, order does not lose value)' % 'identityfile')

    if bad:
        print('VERIFY : NOT-CONVERGED (%s)' % ', '.join(bad))
        return 3
    print('VERIFY : CONVERGED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
