#!/usr/bin/env python3
"""Deterministic mechanical guard for Feature 079 bilingual-expression.

Behavior contract: ``.specify/specs/079-bilingual-expression/contracts/checker.md``
(C-001..C-012). Rule owner (signals / coverage faces / unique form / exemption
faces): ``.specify/shared/guidelines/bilingual-expression.md`` — read at runtime; no
rule enumeration is embedded in this script (One Source Of Truth).

Actions::

    scan --path <file|dir> [--scope full|changed] [--base <commit>] [--json]
    coverage [--json]
    census [--json]

Exit codes (closed, C-002): 0 = no findings; 1 = findings; 2 = usage / IO /
malformed-input errors (unknown action, missing or nonexistent path, ``--path``
on ``coverage``/``census``, unreadable file, owner document missing or
malformed, glossary missing). Exit semantics never vary with finding or file
counts.

Finding codes (closed set of four, C-009): ``full-width-parens``,
``same-language-bracket``, ``missing-bilingual``, ``coverage-missing``.

Mechanical boundary (C-012; owner document § 定义处与可判定信号 的机械判定边界段):
only bracket segments whose two sides are of opposite scripts are evaluated as
bilingual-form attempts. Same-script parentheticals (Chinese 夹注 such as
「（封闭集）」) and ID-reference parentheticals (「（F-01）」「（E2/E3）」) are
out of mechanical scope, as are path/command/URL-shaped bracket contents
(exemption faces, FR-004). ``missing-bilingual`` mechanically fires on S1
glossary body rows whose Canonical contains CJK yet carries no bracket form at
all; heading/bold signal lines are evaluated only when such a bracket segment
is present. The guard never judges semantics; a green run is not evidence of
content correctness (A7 / C-012).

The module exposes ``sample_lines(lines)`` (measurement contract C-004):
deterministic every-k-th-line selection with k = ceil(n/10), consumed by the
review-stage sampling task — reviewers MUST NOT hand-pick samples.

Stdlib only. Read-only with respect to scanned inputs; the only write is the
append-only E6 legacy-divergence record produced by ``scan --scope full``
(owner document § 迁移边界与存量差异).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

OWNER_DOC_REL = ".specify/shared/guidelines/bilingual-expression.md"
GLOSSARY_REL = ".specify/glossary.md"
GLOSSARY_UTILS_REL = ".specify/scripts/python/glossary-utils.py"
E6_REL = ".specify/specs/079-bilingual-expression/test-evidence/us10-e6-legacy-divergence.txt"

COVERAGE_HEADING = "## 覆盖定义面（封闭集）"
SIGNAL_HEADING = "## 定义处与可判定信号"
REGISTRATION_MARKER = "唯一登记行"

FENCE_RE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN_RE = re.compile(r"``[^`]*``|`[^`]*`")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
BOLD_BRACKET_RE = re.compile(r"\*\*[^*]+\*\*\s*[（(]")
HALF_SEG_RE = re.compile(r"([^()（\n|]+)\(([^()\n]+)\)")
FULL_SEG_RE = re.compile(r"([^()（\n|]+)（([^（）\n]+)）")
REF_ANNOTATION_RE = re.compile(r"^[A-Za-z]{1,4}-?\d{1,4}[a-z]?$")
PUNCT_ONLY_RE = re.compile(r"^[\W\d_]+$")
ANNOTATION_PUNCT = ("，", ",", "；", ";", "：", ":")
PRIMARY_DECL_RE = re.compile(
    r"(?:主语言|primary\s+language)\s*[:：]?\s*(zh|en|中文|英文|Chinese|English)"
    r"|\((zh|en|中文|英文)\s*(?:主语言|primary)\)",
    re.IGNORECASE,
)
PATH_TOKEN_RE = re.compile(r"(?:/|\.md$)")
BILINGUAL_CANONICAL_RE = re.compile(r"^[^\s|]+\([^()]+\)$")
CJK_RE = re.compile(r"[一-鿿]")
LATIN_RE = re.compile(r"[A-Za-z]")

FINDING_CODES = (
    "full-width-parens",
    "same-language-bracket",
    "missing-bilingual",
    "coverage-missing",
)


class CheckError(Exception):
    """Usage / IO / malformed-input failure (exit code 2)."""


def _cjk_count(text: str) -> int:
    return len(CJK_RE.findall(text))


def _latin_count(text: str) -> int:
    return len(LATIN_RE.findall(text))


def script_class(text: str) -> str:
    """Mechanical script class: 'cjk' or 'latin' (letters win ties by count)."""
    cjk = _cjk_count(text)
    latin = _latin_count(text)
    if cjk == 0 and latin == 0:
        return "latin"
    return "cjk" if cjk >= latin else "latin"


def sample_lines(lines: List[str]) -> List[str]:
    """Deterministic every-k-th-line sample, k = ceil(n/10) (C-004)."""
    if not lines:
        return []
    k = max(1, math.ceil(len(lines) / 10))
    return lines[k - 1 :: k]


# --------------------------------------------------------------------------- #
# Owner document (rule owner, read at runtime)
# --------------------------------------------------------------------------- #

def load_owner_doc() -> Tuple[List[str], "re.Pattern[str]", List[str]]:
    """Read the owner document; return (lines, registered form regex, coverage items).

    Malformed owner document (missing file, missing signal/coverage section,
    unregistered or uncompilable form regex) raises CheckError (rc 2, C-07).
    """
    path = REPO_ROOT / OWNER_DOC_REL
    if not path.is_file():
        raise CheckError(f"owner document missing: {OWNER_DOC_REL}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CheckError(f"owner document unreadable: {exc}")
    if not any(line.strip() == SIGNAL_HEADING for line in lines):
        raise CheckError(f"owner document malformed: {SIGNAL_HEADING} section absent")
    registration = [line for line in lines if REGISTRATION_MARKER in line]
    if len(registration) != 1:
        raise CheckError(
            f"owner document malformed: form-regex registration lines = {len(registration)} (must be 1)"
        )
    match = re.search(r"`([^`]+)`", registration[0])
    if not match:
        raise CheckError("owner document malformed: registration line carries no regex literal")
    try:
        form_re = re.compile(match.group(1))
    except re.error as exc:
        raise CheckError(f"owner document malformed: registered regex uncompilable: {exc}")
    items: List[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if in_section and stripped.startswith("## "):
                break
            if stripped == COVERAGE_HEADING:
                in_section = True
            continue
        if in_section and line.startswith("- "):
            items.append(line[2:].strip())
    if not items:
        raise CheckError(f"owner document malformed: no coverage items under {COVERAGE_HEADING}")
    return lines, form_re, items


def coverage_paths(items: List[str]) -> List[Path]:
    """Resolve path tokens in coverage items; append command/skill carriers."""
    paths: List[Path] = []
    for item in items:
        for token in re.findall(r"`([^`]+)`", item):
            p = REPO_ROOT / token
            if p.exists():
                paths.append(p)
    for carrier in (".specify/templates/commands", ".specify/templates/skills", "skills"):
        p = REPO_ROOT / carrier
        if p.is_dir():
            paths.append(p)
    seen: List[Path] = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    return seen


def iter_markdown(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_file() and p.suffix == ".md":
            files.append(p)
        elif p.is_dir():
            files.extend(f for f in sorted(p.rglob("*.md")) if f.is_file())
    seen: List[Path] = []
    for f in files:
        if f not in seen:
            seen.append(f)
    return seen


# --------------------------------------------------------------------------- #
# Line processing (exemption faces, C-004)
# --------------------------------------------------------------------------- #

def process_lines(text: str) -> List[str]:
    """Strip fenced blocks, inline code spans, link/image targets (C-004)."""
    out: List[str] = []
    in_fence = False
    for raw in text.splitlines():
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
            continue
        line = CODE_SPAN_RE.sub("", raw)
        line = IMAGE_RE.sub("", line)
        line = LINK_TARGET_RE.sub("]", line)
        out.append(line)
    return out


def _segment_candidates(line: str) -> List[Tuple[str, str, bool, bool]]:
    """Extract bracket segments: (outside, content, is_fullwidth, tight)."""
    segs: List[Tuple[str, str, bool, bool]] = []
    for match in HALF_SEG_RE.finditer(line):
        outside = match.group(1).strip().strip("*").strip()
        segs.append((outside, match.group(2).strip(), False, True))
    for match in FULL_SEG_RE.finditer(line):
        raw_outside = match.group(1)
        tight = bool(raw_outside) and not raw_outside[-1].isspace()
        outside = raw_outside.strip().strip("*").strip()
        segs.append((outside, match.group(2).strip(), True, tight))
    return segs


def _skip_content(content: str) -> bool:
    """Mechanical filters: reference IDs, punctuation lists, paths/commands."""
    if not content:
        return True
    if REF_ANNOTATION_RE.match(content) or PUNCT_ONLY_RE.match(content):
        return True
    if any(p in content for p in ANNOTATION_PUNCT):
        return True
    if "/" in content or "\\" in content or "://" in content or "@" in content:
        return True
    return False


def judge_segments(line: str) -> List[Tuple[str, str, str]]:
    """Evaluate bracket segments of a signal line.

    Returns findings as (code, detail, segment) tuples. Full-width tight
    opposite-script segments take line priority (C-009); half-width
    same-script segments are ``same-language-bracket`` (C-007).
    """
    for outside, content, is_full, tight in _segment_candidates(line):
        if not is_full or not tight or _skip_content(content):
            continue
        if script_class(outside) != script_class(content):
            return [("full-width-parens", f"全角括号紧贴词条: {content}", content)]
    for outside, content, is_full, tight in _segment_candidates(line):
        if is_full or _skip_content(content):
            continue
        if not outside:
            continue
        if script_class(outside) == script_class(content):
            return [("same-language-bracket", f"括号语言与词条同向: {content}", content)]
    return []


def detect_primary_language(text: str) -> str:
    """S4: declaration first; default = higher CJK/Latin letter ratio."""
    decl = PRIMARY_DECL_RE.search(text)
    if decl:
        token = next(g for g in decl.groups() if g).lower()
        if token in ("zh", "中文", "chinese"):
            return "cjk"
        return "latin"
    return script_class(text)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- #
# scan
# --------------------------------------------------------------------------- #

def scan_file(path: Path, is_glossary: bool) -> List[Dict[str, Any]]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"file unreadable: {rel(path)}: {exc}")
    lines = process_lines(raw_text)
    primary = detect_primary_language(raw_text)
    findings: List[Dict[str, Any]] = []

    def emit(line_no: int, code: str, message: str) -> None:
        findings.append({
            "path": rel(path),
            "line": line_no,
            "code": code,
            "message": message,
            "severity": "error",
            "primary_language": primary,
        })

    if is_glossary:
        # S1: glossary table body rows (Canonical registration face).
        in_table = False
        header_re = re.compile(r"^\|\s*Canonical\s*\|", re.IGNORECASE)
        separator_re = re.compile(r"^\|[\s:|-]+\|?\s*$")
        for line_no, line in enumerate(lines, 1):
            if header_re.match(line):
                # Header detection must require the full entry column set:
                # the real glossary also carries a two-column
                # ``| Canonical | <meaning> |`` row inside its
                # ``## Column Definitions`` table: treating that row as the
                # S1 header stops the scan at the next heading before the
                # real entry table (review-stage regression leg
                # test_scan_glossary_shape_skips_column_definitions_decoy).
                header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(header_cells) >= 5:
                    in_table = True
                continue
            if not in_table or separator_re.match(line):
                continue
            if not line.strip().startswith("|"):
                if line.strip():
                    break
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5:
                continue
            canonical = cells[0]
            if not canonical or canonical.lower() == "none yet.":
                continue
            segs = [s for s in _segment_candidates(canonical) if not _skip_content(s[1])]
            judged = [s for s in segs if script_class(s[0]) != script_class(s[1])]
            full_hits = [s for s in judged if s[2] and s[3]]
            if full_hits:
                emit(line_no, "full-width-parens", f"Canonical 全角括号紧贴词条: {canonical}")
                continue
            half_same = [
                s for s in segs
                if not s[2] and s[0] and script_class(s[0]) == script_class(s[1])
            ]
            if half_same:
                emit(line_no, "same-language-bracket", f"Canonical 括号语言与词条同向: {canonical}")
                continue
            if not segs and _cjk_count(canonical) > 0:
                emit(line_no, "missing-bilingual", f"Canonical 含中文但无括号双语形态: {canonical}")
            continue

    for line_no, line in enumerate(lines, 1):
        if is_glossary and line.strip().startswith("|"):
            continue  # S1 rows already judged above
        if not line.startswith("## ") and not BOLD_BRACKET_RE.search(line):
            continue  # S2 (level-2 heading) / S3 (bold-led bracket) only, C-005
        stripped = line.replace("**", "")
        for code, message, _seg in judge_segments(stripped):
            emit(line_no, code, message)
            break
    return findings


def changed_paths(base: Optional[str]) -> List[Path]:
    """--scope changed: union of git diff <base>..HEAD and git status."""
    if base is None:
        base = merge_base()
    paths: set = set()
    if base:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base}..HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if proc.returncode != 0:
            raise CheckError(f"git diff failed: {proc.stderr.strip()}")
        paths.update(p for p in proc.stdout.splitlines() if p.strip())
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise CheckError(f"git status failed: {proc.stderr.strip()}")
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        paths.add(line[3:].strip().strip('"'))
    out = []
    for p in sorted(paths):
        f = REPO_ROOT / p
        if f.is_file() and f.suffix == ".md":
            out.append(f)
    return out


def merge_base() -> Optional[str]:
    for trunk in ("master", "main"):
        proc = subprocess.run(
            ["git", "merge-base", "HEAD", trunk],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    return None


def append_e6_record(findings: List[Dict[str, Any]], files_scanned: int) -> None:
    """Append-only E6 legacy-divergence record (owner doc § 迁移边界)."""
    from datetime import datetime, timezone

    target = REPO_ROOT / E6_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "",
        f"<!-- run: {stamp} files_scanned={files_scanned} findings={len(findings)} -->",
    ]
    if findings:
        lines.extend(f"{f['path']}:{f['line']} [{f['code']}] {f['message']}" for f in findings)
    else:
        lines.append("(no findings)")
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# coverage / census
# --------------------------------------------------------------------------- #

def _face_nonempty(path: Path) -> bool:
    if path.is_file():
        try:
            return path.stat().st_size > 0
        except OSError:
            return False
    if path.is_dir():
        try:
            return any(p.is_file() for p in path.rglob("*"))
        except OSError:
            return False
    return False


def action_coverage(items: List[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for item in items:
        tokens = [t for t in re.findall(r"`([^`]+)`", item) if PATH_TOKEN_RE.search(t)]
        if tokens:
            missing = [t for t in tokens if not _face_nonempty(REPO_ROOT / t)]
            if missing:
                findings.append({
                    "path": OWNER_DOC_REL,
                    "line": None,
                    "code": "coverage-missing",
                    "message": f"覆盖定义面缺失或为空: {item} (missing: {', '.join(missing)})",
                    "severity": "error",
                })
        else:
            carriers = [REPO_ROOT / c for c in (".specify/templates/commands", ".specify/templates/skills", "skills")]
            if not any(_face_nonempty(c) for c in carriers):
                findings.append({
                    "path": OWNER_DOC_REL,
                    "line": None,
                    "code": "coverage-missing",
                    "message": f"覆盖定义面缺失或为空: {item}",
                    "severity": "error",
                })
    return findings


def _load_glossary_utils():
    spec = importlib.util.spec_from_file_location(
        "glossary_utils_for_bilingual_check", REPO_ROOT / GLOSSARY_UTILS_REL
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _term_sides(canonical: str) -> Tuple[str, str]:
    """(chinese_side, english_side) — the CJK-heavy side and the other side."""
    match = re.match(r"^(.*?)\(([^()]*)\)$", canonical.strip())
    first, second = match.group(1), match.group(2)
    if _cjk_count(first) >= _cjk_count(second):
        return first, second
    return second, first


def action_census(items: List[str]) -> Tuple[List[Dict[str, Any]], int]:
    glossary_path = REPO_ROOT / GLOSSARY_REL
    if not glossary_path.is_file():
        raise CheckError(f"glossary missing: {GLOSSARY_REL}")
    try:
        text = glossary_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"glossary unreadable: {exc}")
    gu = _load_glossary_utils()
    bilingual = [
        e for e in gu.parse_entries(text) if BILINGUAL_CANONICAL_RE.match(e["canonical"].strip())
    ]
    terms = [(e, *_term_sides(e["canonical"])) for e in bilingual]
    variants = {e["canonical"].strip(): set(e.get("variants", [])) for e in bilingual}

    findings: List[Dict[str, Any]] = []
    for path in iter_markdown(coverage_paths(items)):
        try:
            raw_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CheckError(f"file unreadable: {rel(path)}: {exc}")
        lines = process_lines(raw_text)
        for line_no, line in enumerate(lines, 1):
            if not line.startswith("## ") and not BOLD_BRACKET_RE.search(line):
                continue
            stripped = line.replace("**", "")
            for outside, content, _full, _tight in _segment_candidates(stripped):
                if _skip_content(content):
                    continue
                for entry, zh, en in terms:
                    if content != en and outside != en:
                        continue
                    cjk_side = outside if _cjk_count(outside) > _cjk_count(content) else content
                    if cjk_side != zh and cjk_side not in variants.get(entry["canonical"].strip(), set()):
                        findings.append({
                            "path": rel(path),
                            "line": line_no,
                            "code": "missing-bilingual",
                            "message": (
                                f"中文侧与 Canonical 不一致: 行内 '{cjk_side}' != 词汇表 '{zh}' "
                                f"({entry['canonical']})"
                            ),
                            "severity": "error",
                        })
                        break
    return findings, len(bilingual)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bilingual expression mechanical guard (078)")
    _sig_configure(parser)

    parser.add_argument("--action", required=True, choices=["scan", "coverage", "census"])
    parser.add_argument("--path", default=None, help="scan: file or directory")
    parser.add_argument("--scope", default=None, choices=["full", "changed"])
    parser.add_argument("--base", default=None, help="scan --scope changed: diff base commit")
    parser.add_argument("--json", action="store_true", help="emit pure JSON summary")
    return parser


def emit_summary(summary: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    for finding in summary["findings"]:
        print(f"{finding['path']}:{finding['line']} [{finding['code']}] {finding['message']}")
    print(json.dumps(summary, ensure_ascii=False))


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

def main(argv: Optional[List[str]] = None) -> int:
    _sig_guard(argv, declared=['--action', '--path', '--scope', '--base', '--json'])  # answer --version / reject an undeclared option
    args = build_parser().parse_args(argv)
    try:
        _owner_lines, form_re, items = load_owner_doc()
        summary: Dict[str, Any] = {
            "action": args.action,
            "files_scanned": 0,
            "findings_count": 0,
            "findings": [],
        }
        if args.action == "scan":
            if args.path:
                target = REPO_ROOT / args.path
                if not (REPO_ROOT / args.path).exists() and not Path(args.path).exists():
                    raise CheckError(f"path does not exist: {args.path}")
                target = Path(args.path)
                if not target.is_absolute():
                    target = (REPO_ROOT / args.path).resolve()
                if not target.exists():
                    raise CheckError(f"path does not exist: {args.path}")
                files = iter_markdown([target])
                summary["scope"] = "path"
            elif args.scope == "changed":
                files = changed_paths(args.base)
                summary["scope"] = "changed"
            else:
                files = iter_markdown(coverage_paths(items))
                summary["scope"] = "full"
            glossary_path = (REPO_ROOT / GLOSSARY_REL).resolve()
            for path in files:
                findings = scan_file(path, is_glossary=(path.resolve() == glossary_path))
                summary["findings"].extend(findings)
                summary["files_scanned"] += 1
            if summary["scope"] == "full":
                append_e6_record(summary["findings"], summary["files_scanned"])
        elif args.action == "coverage":
            if args.path:
                raise CheckError("coverage does not accept --path (scope = owner-document coverage list)")
            if args.scope or args.base:
                raise CheckError("coverage does not accept --scope/--base")
            summary["scope"] = "owner-doc"
            summary["findings"] = action_coverage(items)
            summary["files_scanned"] = len(items)
        else:  # census
            if args.path:
                raise CheckError("census does not accept --path (scope = owner-document coverage list)")
            if args.scope or args.base:
                raise CheckError("census does not accept --scope/--base")
            summary["scope"] = "owner-doc"
            findings, total = action_census(items)
            summary["findings"] = findings
            summary["census_total"] = total
            summary["files_scanned"] = len(items)
        summary["findings_count"] = len(summary["findings"])
        # The registered form regex is read from the owner document; surface its
        # identity in the summary so consumers can verify the runtime registration.
        summary["form_regex"] = form_re.pattern
        emit_summary(summary, args.json)
        return 1 if summary["findings"] else 0
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
