#!/usr/bin/env python3
"""search-todo.sh — SPECKIT TODO block scanner

Scans workspace text files for fenced SPECKIT TODO blocks and emits
structured JSON (--json) or human-readable key:value output.

Contract: .specify/specs/020-speckit-todo-command/contracts/search-todo-cli.md
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SPECKIT TODO block scanner")
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    p.add_argument("--root", type=str, help="Override workspace root")
    p.add_argument("--exclude", action="append", default=[], help="Append exclude pattern (repeatable)")
    p.add_argument("--no-default-excludes", action="store_true", help="Disable built-in exclude list")
    p.add_argument("--context-depth", type=int, default=8, help="Paragraph-boundary line ceiling (default: 8)")
    p.add_argument("--context-only-headings", action="store_true", help="Restrict context to heading lines only")
    p.add_argument("ROOT", nargs="?", default=None, help="Workspace root path")
    return p.parse_args()


DEFAULT_EXCLUDES = [
    r"\.git/", r"\.svn/", r"node_modules/", r"\.venv/", r"venv/",
    r"__pycache__/", r"dist/", r"build/", r"target/", r"\.idea/",
    r"\.vscode/", r"\.DS_Store", r"Thumbs\.db",
]

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB


def resolve_root(pos_root: Optional[str], root_arg: Optional[str]) -> str:
    candidates = []
    if pos_root:
        candidates.append(os.path.realpath(pos_root))
    if root_arg:
        candidates.append(os.path.realpath(root_arg))
    for p in candidates:
        if os.path.isdir(p) and os.access(p, os.R_OK):
            return p

    # Fallback: walk up from cwd for .git or .specify
    d = os.getcwd()
    while d != "/":
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(os.path.join(d, ".specify")):
            if os.access(d, os.R_OK):
                return d
        d = os.path.dirname(d)

    print("search-todo: error: cannot determine repository root", file=sys.stderr)
    sys.exit(2)


def is_eligible(abspath: str, relpath: str, exclude_patterns: List[str], excluded_files: List[str]) -> bool:
    for pat in exclude_patterns:
        if re.search(pat, relpath):
            return False
    try:
        if not os.access(abspath, os.R_OK):
            return False
        sz = os.path.getsize(abspath)
        if sz > MAX_FILE_SIZE:
            excluded_files.append(relpath)
            print(f"search-todo: warning: excluded file (too_large): {relpath}", file=sys.stderr)
            return False
        # Check encoding
        with open(abspath, "rb") as fh:
            head = fh.read(8192)
        head.decode("utf-8")
        return True
    except (OSError, PermissionError):
        return False
    except UnicodeDecodeError:
        excluded_files.append(relpath)
        print(f"search-todo: warning: excluded file (encoding_error): {relpath}", file=sys.stderr)
        return False


def scan_file(filepath: str, rel_path: str, context_depth: int, headings_only: bool) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Scan a single file for SPECKIT TODO blocks. Returns (blocks, malformed)."""
    blocks: List[Dict[str, Any]] = []
    malformed: List[Dict[str, Any]] = []

    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:
        return blocks, malformed

    in_fence = False
    is_todo = False
    fence_start = 0
    block_lines: List[str] = []
    block_idx = 0
    nearest_heading: Optional[str] = None

    for i, line in enumerate(lines):
        ln = i + 1  # 1-based

        # Track nearest heading (C-1)
        heading_match = re.match(r"^(#{1,6})\s+(.+?)(?:\s*\{#[^}]*\})?\s*$", line)
        if heading_match:
            nearest_heading = heading_match.group(2).strip()

        stripped = line.rstrip("\n\r")
        is_fence = stripped.startswith("```") or re.match(r"^~~~[~]*$", stripped)

        if is_fence and not in_fence:
            # Opening fence
            if "SPECKIT TODO" in stripped:
                is_todo = True
            else:
                is_todo = False
            in_fence = True
            fence_start = ln
            block_lines = []
            continue

        if is_fence and in_fence:
            # Closing fence
            if is_todo:
                closing_line = ln
                content = "".join(block_lines)

                # Prologue (C-2): lines above opening fence, bounded by blank/heading
                prologue_lines = []
                for j in range(fence_start - 2, -1, -1):
                    if len(prologue_lines) >= context_depth:
                        break
                    pl = lines[j].rstrip("\n\r")
                    if pl == "" or re.match(r"^#{1,6}\s", pl):
                        break
                    prologue_lines.insert(0, pl)
                prologue = "\n".join(prologue_lines)
                if headings_only:
                    prologue = nearest_heading or ""

                # Epilogue (C-3): lines below closing fence
                epilogue_lines = []
                for j in range(ln, min(len(lines), ln + context_depth)):
                    el = lines[j].rstrip("\n\r")
                    if el == "" or re.match(r"^#{1,6}\s", el):
                        break
                    epilogue_lines.append(el)
                epilogue = "\n".join(epilogue_lines)
                if headings_only:
                    epilogue = nearest_heading or ""

                blocks.append({
                    "block_id": f"{rel_path}:{fence_start}:{block_idx}",
                    "source_file": rel_path,
                    "opening_line": fence_start,
                    "closing_line": closing_line,
                    "content": content,
                    "context_heading": nearest_heading,
                    "prologue": prologue,
                    "epilogue": epilogue,
                })
                block_idx += 1

            in_fence = False
            is_todo = False
            continue

        if in_fence and is_todo:
            block_lines.append(line)

    # Unclosed fence at EOF (D-3)
    if in_fence and is_todo:
        content = "".join(block_lines)
        malformed.append({
            "source_file": rel_path,
            "opening_line": fence_start,
            "reason": "unclosed_fence",
            "content_snippet": content[:120],
            "line_after_eof": True,
        })

    return blocks, malformed


def output_keyvalue(
    blocks: List[Dict[str, Any]],
    malformed: List[Dict[str, Any]],
    excluded_files: List[str],
    total_files: int,
    scanned_at: str,
    branch: str,
    workspace_root: str,
) -> None:
    print(f"BRANCH:          {branch}")
    print(f"REPO_ROOT:       {workspace_root}")
    print(f"TOTAL_FILES:     {total_files}")
    print(f"TOTAL_BLOCKS:    {len(blocks)}")
    print(f"MALFORMED:       {len(malformed)}")
    print(f"EXCLUDED_FILES:  {len(excluded_files)}")
    print(f"SCANNED_AT:      {scanned_at}")

    for idx, b in enumerate(blocks):
        hd = "null"
        if b["context_heading"]:
            hd = f'"{b["context_heading"]}"'
        print(f"BLOCK[{idx}]:        {b['source_file']}:{b['opening_line']}:{b['closing_line']}:heading {hd}")

    for idx, m in enumerate(malformed):
        print(f"MALFORMED[{idx}]:    {m['source_file']}:{m['opening_line']}:{m['reason']}")


def output_json(
    blocks: List[Dict[str, Any]],
    malformed: List[Dict[str, Any]],
    excluded_files: List[str],
    total_files: int,
    scanned_at: str,
    branch: str,
    workspace_root: str,
) -> None:
    result = {
        "repository": workspace_root,
        "branch": branch,
        "scanned_at": scanned_at,
        "counters": {
            "total_files_scanned": total_files,
            "total_blocks_found": len(blocks),
            "malformed_blocks": len(malformed),
            "excluded_files_count": len(excluded_files),
        },
        "blocks": blocks,
        "malformed": malformed,
        "excluded_files": excluded_files,
    }
    print(json.dumps(result, ensure_ascii=False))


def main() -> None:
    args = parse_args()

    workspace_root = resolve_root(args.ROOT, args.root)
    excluded_files: List[str] = []

    exclude_patterns: List[str] = []
    if not args.no_default_excludes:
        exclude_patterns = list(DEFAULT_EXCLUDES)
    exclude_patterns.extend(args.exclude)

    # Collect eligible files
    file_list = []
    for dirpath, dirnames, filenames in os.walk(workspace_root):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, workspace_root)
            if is_eligible(fp, rel, exclude_patterns, excluded_files):
                file_list.append(fp)

    total_files = len(file_list)
    file_list.sort()

    all_blocks = []
    all_malformed = []

    start = time.time()
    for fp in file_list:
        rel = os.path.relpath(fp, workspace_root)
        blks, malf = scan_file(fp, rel, args.context_depth, args.context_only_headings)
        all_blocks.extend(blks)
        all_malformed.extend(malf)
    elapsed = time.time() - start

    scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get branch
    branch = "unknown"
    try:
        import subprocess
        result = subprocess.run(
            ["git", "-C", workspace_root, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except Exception:
        pass

    if args.json:
        output_json(all_blocks, all_malformed, excluded_files, total_files, scanned_at, branch, workspace_root)
    else:
        output_keyvalue(all_blocks, all_malformed, excluded_files, total_files, scanned_at, branch, workspace_root)

    print(f"search-todo: info: scanned {total_files} files in {elapsed:.1f} seconds", file=sys.stderr)


if __name__ == "__main__":
    main()