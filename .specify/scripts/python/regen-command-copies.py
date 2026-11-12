#!/usr/bin/env python3
"""Regenerate per-tool /speckit.* command copies from .specify/templates/commands/*.md.

Single-source fan-out: ``.specify/templates/commands/<stem>.md`` is the source of truth.
This script regenerates every per-tool runtime copy (.claude/commands/,
.github/prompts/, .qoder/commands/, .opencode/command/, ...)
using the canonical generator in ``src/specify_cli`` — the same code path as
``specify init`` — so hand-syncing copies is never required. Only tools whose
command directory already exists in the repo are regenerated.

Usage:
  python3 .specify/scripts/python/regen-command-copies.py           # regenerate in place
  python3 .specify/scripts/python/regen-command-copies.py --check   # report drift, write nothing, exit 1 on drift
"""
from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Guard: running the .specify/scripts/python/ mirror copy resolves parents[2]
# to `.specify`, producing doubled `.specify/.specify/` paths downstream.
# Fail fast with a pointer to the canonical copy instead of crashing mid-run.
if REPO_ROOT.name == ".specify":
    sys.stderr.write(
        "regen-command-copies.py: running from the .specify/scripts/python/ mirror; "
        f"use the canonical copy instead: {REPO_ROOT.parent / 'scripts' / 'python' / Path(__file__).name}\n"
    )
    sys.exit(2)
sys.path.insert(0, str(REPO_ROOT / "src"))

import specify_cli  # noqa: E402
from specify_cli import (  # noqa: E402
    _ASSISTANT_ARG_FORMATS,
    _ASSISTANT_COMMAND_DIRS,
    _ASSISTANT_EXTENSIONS,
    generate_commands,
)

# Repo-anchor: in a dev checkout the package resource dir does not exist, and
# get_resource_path() returns None (generate_commands then no-ops). Point it at
# the repo root so .specify/templates/commands/ resolves to the working tree.
specify_cli.get_resource_path = lambda: REPO_ROOT


def _tool_dirs() -> dict[str, Path]:
    """Existing per-tool command directories in this repo."""
    out = {}
    for agent, rel in _ASSISTANT_COMMAND_DIRS.items():
        d = REPO_ROOT / rel
        if d.is_dir():
            out[agent] = d
    return out


def _generate_all(base: Path) -> list[Path]:
    """Run the canonical generator for every present tool into dirs under base."""
    written = []
    for agent, live_dir in _tool_dirs().items():
        out_dir = base / agent
        generate_commands(
            agent,
            _ASSISTANT_EXTENSIONS[agent],
            _ASSISTANT_ARG_FORMATS.get(agent, "$ARGUMENTS"),
            out_dir,
            "sh",
        )
        written.extend(sorted(out_dir.glob("speckit.*")))
    return written


# --version, wired through the one version source (C-8)
#
# `guard_argv()` answers `--version` (and rejects an undeclared option) BEFORE any parser
# reads the line, so it works for a flat argparse parser, for one whose subcommands are
# required, and for the two modules that read sys.argv by hand. It writes nothing and
# resolves `<script-name> <framework-version>` from the nearest pyproject.toml at run
# time — this file carries no version literal. `--help` is left to the module's own body.
import sys as _sig_sys  # noqa: E402
import pathlib as _sig_pathlib

_SIG_DIR = str(_sig_pathlib.Path(__file__).resolve().parent)
if _SIG_DIR not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_DIR)
try:  # the helper owns the rule; an engine copied WITHOUT it still runs its actions
    from script_interface_cli import configure_parser as _sig_configure  # noqa: E402
    from script_interface_cli import guard_argv as _sig_guard  # noqa: E402
except ImportError:  # a sandbox/handler copy carries the engine but not the helper
    def _sig_configure(parser, **_kwargs):
        return parser

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None

def main() -> int:
    _sig_guard(declared=['--check'])  # answer --version / reject an undeclared option
    ap = argparse.ArgumentParser(description=__doc__)
    _sig_configure(ap)

    ap.add_argument("--check", action="store_true", help="report drift without writing")
    args = ap.parse_args()

    drift: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        gen = _generate_all(Path(tmp))
        for gen_file in gen:
            agent = gen_file.parent.name
            live = _tool_dirs()[agent] / gen_file.name
            if not live.exists():
                drift.append(f"{live.relative_to(REPO_ROOT)} (missing)")
            elif not filecmp.cmp(gen_file, live, shallow=False):
                drift.append(str(live.relative_to(REPO_ROOT)))
        # stale copies whose template was removed/renamed
        expected = {
            (agent, f.name) for agent in _tool_dirs() for f in (Path(tmp) / agent).glob("speckit.*")
        }
        for agent, live_dir in _tool_dirs().items():
            for f in sorted(live_dir.glob("speckit.*")):
                if (agent, f.name) not in expected:
                    drift.append(f"{f.relative_to(REPO_ROOT)} (stale, no source template)")

    if args.check:
        if drift:
            print("DRIFT detected:")
            for d in drift:
                print(f"  {d}")
            return 1
        print("OK: all per-tool command copies match the source templates.")
        return 0

    # write mode
    # Pre-pass: drop non-writable (e.g. root-owned) stale targets; the
    # directories are user-writable, so remove-then-regenerate succeeds where
    # an in-place open() would fail.
    import os

    for live_dir in list(_tool_dirs().values()):
        for f in live_dir.glob("*"):
            if f.is_file() and not os.access(f, os.W_OK):
                os.remove(f)
                print(f"removed non-writable stale file: {f.relative_to(REPO_ROOT)}")

    for agent, live_dir in _tool_dirs().items():
        generate_commands(
            agent,
            _ASSISTANT_EXTENSIONS[agent],
            _ASSISTANT_ARG_FORMATS.get(agent, "$ARGUMENTS"),
            live_dir,
            "sh",
        )

    print(f"Regenerated command copies for {len(_tool_dirs())} tools.")
    if drift:
        print("Fixed drift:")
        for d in drift:
            print(f"  {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
