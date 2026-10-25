#!/usr/bin/env python3
"""doc-consistency-check.py — 069a document-form consistency checker.

Owner of the command surface and the four faces is
``.specify/specs/069a-flow-classification-docs-gates/contracts/doc-consistency-checker.md``
(C-1 … C-10); the finding record is owned by ``data-model.md`` E7. This module
implements the mechanical faces only — it never re-defines a value domain:

* ``reader``    — the two-line reader declaration inside the first 40 non-empty
                  lines of every explicitly named document (C-4);
* ``evidence``  — the syntax and pairing of the ``证据：`` annotation
                  (grade / as-of / source), grammar owned by
                  ``.specify/shared/workflow/expression-gates.md`` § 证据分级与 as-of (C-3);
* ``duplicate`` — cross-file hand-written fact copies against the face owners
                  (C-5), with the two detection thresholds;
* ``count``     — **delegated** to ``pre-analyze-check.py``; this checker never
                  re-implements a counting rule (C-6).

Read-only by construction: the only file this process may write is the one
named by ``--json-out`` (C-1).

Exit codes (C-8): 0 = zero findings and every requested face evaluated, 1 = at
least one finding **or** a blocking face left ``not-evaluated`` (a degraded face
is never a pass — ``--allow-degraded`` is the only opt-out), 2 = input / parse
error.

Standard library only, Python >= 3.8.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

FACES = ("reader", "evidence", "duplicate", "count")

READER_MARKERS = (
    ("readers", re.compile(r"^\s*\*\*Readers\*\*\s*[:：]\s*(.*)$")),
    ("reading_scenario", re.compile(r"^\s*\*\*Reading scenario\*\*\s*[:：]\s*(.*)$")),
)
READER_WINDOW = 40

GRADE_MARKERS = ("证据：", "证据:")
GRADE_VALUES = ("实测", "推断", "引用")
AS_OF_RE = re.compile(r"as-of\s*[:：]?\s*([^\s，,。；;）)]+)")
SOURCE_RE = re.compile(r"source\s*[:：]\s*(.*)$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# --------------------------------------------------------------------------- #
# C-2 — the three sets and the closed exclusion list.
# --------------------------------------------------------------------------- #
# S1: formal artifacts under --spec-dir.
FORMAL_NAMES = (
    "requirements.md",
    "plan.md",
    "tasks.md",
    "data-model.md",
    "research.md",
    "quickstart.md",
    "feature-ref.md",
)
FORMAL_GLOBS = ("contracts", "checklists")

# Path-level exclusions (closed set; a new entry is a contract change).
EXCLUDED_DIR_NAMES = frozenset({"notes"})
EXCLUDED_FILE_NAMES = frozenset({"review.md", "verification.md"})
MIRROR_DIR_NAME = ".specify"

# S3: the six-face owner set — the comparison side of the duplicate face only
# (C-2, C-5 rule 3). Paths only; no judgment text is copied here.
OWNER_PATHS = (
    ".specify/shared/guidelines/requirements-guidelines.md",
    ".specify/shared/guidelines/user-facing-comprehension.md",
    ".specify/shared/workflow/expression-gates.md",
    ".specify/shared/guidelines/one-source-of-truth.md",
    ".specify/skills/create-docs/SKILL.md",
    ".specify/skills/create-docs/scripts/docs-utils.py",
    ".specify/skills/internal/review-sdd-process/SKILL.md",
    ".specify/templates/review-template.md",
    ".specify/scripts/python/validate-requirements.py",
)

# The two owners of the *other* evidence value domains (data-model E6 object
# boundary): their own annotation grammar is not this face's subject.
EVIDENCE_FACE_EXCLUDED_PATHS = (
    ".specify/shared/workflow/evidence-step.md",
    ".specify/shared/guidelines/single-run-evidence.md",
)

# Line-level exclusions (closed set).
LIST_PREFIX_RE = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+|>\s*)+")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:|.-]*-[\s:|.-]*\|[\s:|.-]*$")
LINK_ONLY_RE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:<?https?://\S+>?|\[[^\]]*\]\(\s*https?://[^)]*\))\s*$"
)
DATE_VERSION_RE = re.compile(r"^(?:v?\d+(?:\.\d+)+(?:[-+._][\w.-]*)?|\d{4}-\d{2}-\d{2})$")
TRAILING_PUNCT = ".,;:!?、，。；：！？)]}）】」』\"'”’…"
ASCII_FOLD = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
)
DUPLICATE_EXACT_MIN = 24
DUPLICATE_FUZZY_MIN = 40
DUPLICATE_FUZZY_RATIO = 0.90

# C-6 — delegation target. Source-relative only: the payload-root resolution in
# ``resolve_payload`` also tries the flattened ``.specify/skills/...`` form, so a
# client project (where only the mirror exists) finds its copy without a second
# hard-coded path.
DELEGATE_PATHS = (
    ".specify/skills/sdd-loop-driver/scripts/pre-analyze-check.py",
)


class InputError(Exception):
    """Input or parse error — always exit code 2 (C-8)."""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def find_repo_root(script_path):
    """The project root that owns this checkout — never ``.specify`` itself.

    Two hats, one tree: the canonical copy lives at ``<root>/scripts/python/`` and
    the delivered copy at ``<root>/.specify/scripts/python/``; both MUST resolve
    to ``<root>``. Walking up to the nearest ancestor holding ``.specify/shared/`` and
    ``skills/`` is not enough — inside a client project (and inside this framework
    repo's own runtime mirror) ``.specify/`` itself holds both, which is the
    two-hats path-resolution trap: the mirror copy then resolves owner paths
    against a flattened tree where ``skills/external/…`` does not exist. A
    directory named ``.specify`` is therefore never a repository root.

    Anchored on the script location, never on the caller's cwd: the checker must
    behave the same from any working directory (the evidence face runs with the
    cwd of the document under test).
    """
    here = script_path.resolve()
    parents = list(here.parents)
    # 1. The source root: the nearest non-`.specify` ancestor carrying the payload.
    for parent in parents:
        if parent.name == MIRROR_DIR_NAME:
            continue
        if (parent / "shared").is_dir() and (parent / "skills").is_dir():
            return parent
    # 2. Two-hats fallback: the root is the parent of the `.specify/` we live under.
    for parent in parents:
        if parent.name == MIRROR_DIR_NAME:
            return parent.parent
    return parents[2] if len(parents) > 2 else here.parent


def root_candidates(script_path=None):
    """Payload roots to resolve framework-relative paths against, in order.

    Source root first, its ``.specify/`` mirror second: a framework checkout
    resolves everything from the source tree, while a client project — which only
    receives ``.specify/`` — resolves the same paths from the mirror. Both shapes
    are load-bearing: the wired call sites name the delivered copy.
    """
    root = find_repo_root(Path(__file__) if script_path is None else script_path)
    roots = [root]
    mirror = root / MIRROR_DIR_NAME
    if mirror.is_dir() and mirror.resolve() != root.resolve():
        roots.append(mirror)
    return roots


def payload_forms(rel):
    """Both distribution shapes of a source-relative framework path.

    ``skills/external/<name>/…`` mirrors flat into ``.specify/skills/<name>/…``
    (the host-discovery surface); ``skills/internal/<name>/…`` mirrors nested.
    """
    forms = [rel]
    parts = Path(rel).parts
    if len(parts) > 2 and parts[0] == "skills" and parts[1] == "external":
        forms.append(Path(parts[0], *parts[2:]).as_posix())
    return forms


def resolve_payload(roots, rel):
    """Resolve one framework-relative path against every root/shape pair.

    Returns ``None`` only when neither the source root nor the mirror root carries
    the path in any shape — the single condition that makes an owner genuinely
    unavailable.
    """
    for root in roots:
        for form in payload_forms(rel):
            candidate = root / form
            if candidate.is_file():
                return candidate
    return None


def display_path(path, root):
    """Repo-relative when inside the repo, absolute otherwise (E7 ``path``)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def relative_to(path, root):
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def is_excluded_path(path, root):
    parts = path.resolve().parts
    if MIRROR_DIR_NAME in parts:
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    for parent in path.resolve().parents:
        if parent.name in EXCLUDED_DIR_NAMES:
            return True
        if parent == root.resolve():
            break
    return False


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def iter_lines(path):
    """Yield ``(line_number, raw_line, in_fence)``; fence tracking is per file."""
    fence = None
    for number, line in enumerate(read_text(path).splitlines(), 1):
        stripped = line.strip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            if fence is None:
                fence = marker
                yield number, line, True
                continue
            if marker == fence:
                fence = None
                yield number, line, True
                continue
        yield number, line, fence is not None


def normalise(raw):
    """C-5 rule 1: strip list/quote prefix, collapse blanks, drop trailing
    punctuation, ASCII-casefold."""
    text = LIST_PREFIX_RE.sub("", raw.strip())
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(TRAILING_PUNCT).strip()
    return text.translate(ASCII_FOLD)


def excluded_line(norm, raw):
    """C-2 line-level exclusion list, evaluated on the normalised form."""
    if len(norm) < DUPLICATE_EXACT_MIN:
        return True
    if TABLE_SEPARATOR_RE.match(raw):
        return True
    if LINK_ONLY_RE.match(raw):
        return True
    if DATE_VERSION_RE.match(norm):
        return True
    return False


def snippet(raw, limit=120):
    text = raw.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def finding(face, rule, path, line, text, counterpart=None, fix_direction=""):
    return {
        "face": face,
        "rule": rule,
        "path": path,
        "line": line,
        "snippet": snippet(text),
        "counterpart": counterpart,
        "fix_direction": fix_direction,
    }


# --------------------------------------------------------------------------- #
# C-4 — reader face
# --------------------------------------------------------------------------- #
def check_reader(paths, root):
    """C-4: both declaration lines, non-empty, inside the first 40 non-empty lines."""
    findings = []
    for path in paths:
        declared = {}
        seen = 0
        for number, raw, in_fence in iter_lines(path):
            if not raw.strip():
                continue
            seen += 1
            if not in_fence:
                for key, pattern in READER_MARKERS:
                    if key in declared:
                        continue
                    match = pattern.match(raw)
                    if match:
                        declared[key] = (number, match.group(1).strip())
            if len(declared) >= len(READER_MARKERS) or seen >= READER_WINDOW:
                break
        missing = [key for key, _ in READER_MARKERS if key not in declared]
        empty = [key for key, (_, value) in declared.items() if not value]
        if missing or empty:
            findings.append(
                finding(
                    "reader",
                    "reader-declaration-missing",
                    display_path(path, root),
                    1,
                    "missing or empty reader declaration: %s"
                    % ", ".join(missing + empty),
                    fix_direction="补齐标注（前 40 非空行内 **Readers** / **Reading scenario** 两行且值非空）",
                )
            )
    return findings


# --------------------------------------------------------------------------- #
# C-3 — evidence face
# --------------------------------------------------------------------------- #
def evidence_allowed(path, root):
    rel = relative_to(path, root)
    if rel in EVIDENCE_FACE_EXCLUDED_PATHS:
        return False
    return True


def last_commit_date(path):
    """``git log -1 --format=%cs -- <path>`` or ``(None, reason)``.

    Never "pass": an unreadable clock is reported as not-evaluated (C-3).
    """
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(path.resolve().parent),
                "log",
                "-1",
                "--format=%cs",
                "--",
                path.name,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "git unavailable (%s)" % exc
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        return None, "not a git working tree or unreadable history: %s" % (
            detail[-1] if detail else "git log exit %d" % proc.returncode
        )
    value = proc.stdout.strip()
    if not value:
        return None, "no commit history for %s" % path.name
    if not ISO_DATE_RE.match(value):
        return None, "unexpected git date %r" % value
    return value, None


def parse_annotation(raw):
    """Return ``(grade, as_of_token, source_value)`` per the owner's grammar."""
    marker = None
    for candidate in GRADE_MARKERS:
        index = raw.find(candidate)
        if index >= 0:
            marker = (index, candidate)
            break
    if marker is None:
        return None
    index, candidate = marker
    rest = raw[index + len(candidate):]
    grade = re.split(r"[，,（(]", rest, 1)[0].strip()
    as_of_match = AS_OF_RE.search(rest)
    as_of = as_of_match.group(1).strip().rstrip(TRAILING_PUNCT) if as_of_match else None
    source_match = SOURCE_RE.search(rest)
    source = None
    if source_match:
        source = source_match.group(1).strip().rstrip(TRAILING_PUNCT + " ")
    return grade, as_of, source


def check_evidence(paths, root):
    findings = []
    degradations = []
    for path in paths:
        if not evidence_allowed(path, root):
            continue
        date_cache = {}

        def commit_date(p=path):
            if p not in date_cache:
                date_cache[p] = last_commit_date(p)
            return date_cache[p]

        for number, raw, in_fence in iter_lines(path):
            if in_fence:
                continue
            parsed = parse_annotation(raw) if any(m in raw for m in GRADE_MARKERS) else None
            if parsed is None:
                continue
            grade, as_of, source = parsed
            display = display_path(path, root)
            if not grade or not as_of:
                findings.append(
                    finding(
                        "evidence",
                        "grade-asof-unpaired",
                        display,
                        number,
                        raw,
                        fix_direction="补齐标注（等级与 as-of 成组出现）",
                    )
                )
                continue
            if grade not in GRADE_VALUES:
                findings.append(
                    finding(
                        "evidence",
                        "grade-invalid",
                        display,
                        number,
                        raw,
                        fix_direction="补齐标注（等级取封闭三值 实测 / 推断 / 引用）",
                    )
                )
            if not ISO_DATE_RE.match(as_of):
                findings.append(
                    finding(
                        "evidence",
                        "as-of-malformed",
                        display,
                        number,
                        raw,
                        fix_direction="补齐标注（as-of 写成 YYYY-MM-DD）",
                    )
                )
            else:
                commit, reason = commit_date()
                if commit is None:
                    degradations.append(
                        {
                            "face": "evidence",
                            "status": "not-evaluated",
                            "path": display,
                            "line": number,
                            "reason": reason,
                        }
                    )
                elif as_of < commit:
                    findings.append(
                        finding(
                            "evidence",
                            "as-of-stale",
                            display,
                            number,
                            raw,
                            fix_direction="补齐标注（as-of 刷新到该文件最后一次提交日期或之后）",
                        )
                    )
            if not source:
                findings.append(
                    finding(
                        "evidence",
                        "source-missing",
                        display,
                        number,
                        raw,
                        fix_direction="补齐标注（source 必填且非空）",
                    )
                )
    return findings, degradations


# --------------------------------------------------------------------------- #
# C-5 — duplicate face
# --------------------------------------------------------------------------- #
def subject_files(spec_dir, paths):
    files = []
    if spec_dir is not None:
        for name in FORMAL_NAMES:
            candidate = spec_dir / name
            if candidate.is_file():
                files.append(candidate)
        for folder in FORMAL_GLOBS:
            root = spec_dir / folder
            if not root.is_dir():
                continue
            for candidate in sorted(root.rglob("*.md")):
                if candidate.is_file():
                    files.append(candidate)
    files.extend(paths)
    unique = []
    seen = set()
    for path in files:
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def collect_records(paths, root, pool, allow_mirror=False):
    """Collect comparable lines from *paths*.

    ``allow_mirror`` is for the S3 owner set only. Mirror-side files are excluded
    from the scanned sets (C-2), but the owners are an explicit, closed path list —
    in a client project every one of them resolves inside ``.specify/``, and
    dropping them there would leave the duplicate face comparing against an empty
    comparison side, i.e. a silent pass.
    """
    records = []
    for path in paths:
        if not allow_mirror and is_excluded_path(path, root):
            continue
        display = display_path(path, root)
        for number, raw, in_fence in iter_lines(path):
            if in_fence:
                continue
            norm = normalise(raw)
            if excluded_line(norm, raw):
                continue
            records.append(
                {
                    "pool": pool,
                    "display": display,
                    "line": number,
                    "raw": raw,
                    "norm": norm,
                    "length": len(norm),
                    "counter": Counter(norm),
                }
            )
    return records


def upper_bound(left, right):
    """A cheap upper bound of ``SequenceMatcher.ratio`` (multiset overlap)."""
    total = left["length"] + right["length"]
    if not total:
        return 1.0
    small, large = (left, right) if left["length"] <= right["length"] else (right, left)
    matches = 0
    for char, count in small["counter"].items():
        other = large["counter"].get(char)
        if other:
            matches += count if count < other else other
    return 2.0 * matches / total


def fuzzy_ratio(left, right):
    return SequenceMatcher(None, left["norm"], right["norm"]).ratio()


def _pair(left, right):
    """Order the pair lexicographically by display path (C-5 rule 3)."""
    ordered = sorted((left, right), key=lambda rec: (rec["display"], rec["line"]))
    first, second = ordered[0], ordered[-1]
    return first, second


def check_duplicates(subject, owners, subject_pairs=True):
    """Report hand-written copies.

    ``subject_pairs=False`` is the *owner-scoped* measurement (``--owner-path``):
    the question is "is this owner's text copied anywhere in the subject set", so
    subject↔subject pairs are out of scope and the near-copy pool is the owners
    only. The default (``True``) keeps the S3 069a semantics: subjects are also
    compared against each other.
    """
    findings = []
    consumed = set()

    # Exact normalised equality (cheap, index-based).
    groups = {}
    for record in subject + owners:
        groups.setdefault(record["norm"], []).append(record)
    for norm, group in groups.items():
        displays = sorted({record["display"] for record in group})
        if len(displays) < 2:
            continue
        if not any(record["pool"] == "subject" for record in group):
            continue  # S3 is the comparison side only (C-2)
        if not subject_pairs:
            # Owner-scoped: the pair must actually involve a comparison-side owner.
            if not any(record["pool"] == "owner" for record in group):
                continue
            first = min(
                (record for record in group if record["pool"] == "owner"),
                key=lambda record: (record["display"], record["line"]),
            )
            second = min(
                (record for record in group if record["pool"] == "subject"),
                key=lambda record: (record["display"], record["line"]),
            )
        else:
            first = min(
                (record for record in group if record["display"] == displays[0]),
                key=lambda record: record["line"],
            )
            second = min(
                (record for record in group if record["display"] == displays[1]),
                key=lambda record: record["line"],
            )
        findings.append(
            finding(
                "duplicate",
                "duplicate-fact",
                first["display"],
                first["line"],
                first["raw"],
                counterpart="%s:%d" % (second["display"], second["line"]),
                fix_direction="改为对唯一 owner 的引用",
            )
        )
        for record in group:
            if record["pool"] == "subject":
                consumed.add(id(record))

    # Near copies (ratio >= 0.90, both lines >= 40 chars).
    candidates = [record for record in subject if id(record) not in consumed]
    pool = [record for record in owners]
    if subject_pairs:
        pool = pool + [record for record in subject]
    for record in candidates:
        if id(record) in consumed:
            continue
        if record["length"] < DUPLICATE_FUZZY_MIN:
            continue
        best = None
        for other in pool:
            if other is record or other["display"] == record["display"]:
                continue
            if other["length"] < DUPLICATE_FUZZY_MIN:
                continue
            smaller = min(record["length"], other["length"])
            larger = max(record["length"], other["length"])
            if smaller * 100 < larger * 80:
                continue
            if upper_bound(record, other) < DUPLICATE_FUZZY_RATIO:
                continue
            if fuzzy_ratio(record, other) < DUPLICATE_FUZZY_RATIO:
                continue
            if best is None or other["display"] < best["display"]:
                best = other
        if best is None:
            continue
        consumed.add(id(record))
        consumed.add(id(best))
        first, second = _pair(record, best)
        findings.append(
            finding(
                "duplicate",
                "duplicate-fact",
                first["display"],
                first["line"],
                first["raw"],
                counterpart="%s:%d" % (second["display"], second["line"]),
                fix_direction="改为对唯一 owner 的引用",
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# C-6 — count face (delegated, never re-implemented)
# --------------------------------------------------------------------------- #
def find_delegate(roots):
    for rel in DELEGATE_PATHS:
        candidate = resolve_payload(roots, rel)
        if candidate is not None:
            return candidate
    return None


def delegate_count(spec_dir, roots, root=None):
    """Return ``(findings, count_check)``; every degradation is explicit."""
    root = root if root is not None else roots[0]
    if spec_dir is None:
        return [], {
            "status": "not-run",
            "reason": "no --spec-dir; the count face needs a spec dir to delegate",
        }
    delegate = find_delegate(roots)
    if delegate is None:
        return [], {
            "status": "not-run",
            "reason": "delegation target absent: %s" % ", ".join(DELEGATE_PATHS),
        }
    if (spec_dir / "plan.md").is_file():
        stage = "plan"
    elif (spec_dir / "tasks.md").is_file():
        # The delegate itself rejects a tasks stage without plan.md (exit 2);
        # its own reason is what lands in count_check.reason.
        stage = "tasks"
    else:
        return [], {
            "status": "not-run",
            "reason": "spec dir lacks plan.md and tasks.md; count delegation needs "
                      "--stage plan or --stage tasks",
        }
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(delegate),
                "--spec-dir",
                str(spec_dir),
                "--stage",
                stage,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], {"status": "not-run", "reason": "delegation failed to start: %s" % exc}
    if proc.returncode == 2:
        detail = (proc.stderr or "").strip().splitlines()
        return [], {
            "status": "not-run",
            "reason": "delegate exit 2: %s"
                      % (detail[-1] if detail else "input error"),
        }
    try:
        record = json.loads(proc.stdout)
    except (ValueError, TypeError):
        return [], {
            "status": "not-run",
            "reason": "delegate did not return JSON on stdout (exit %d)" % proc.returncode,
        }
    findings = []
    for item in record.get("findings", []):
        if item.get("check") != "count-claim":
            continue
        rel = str(item.get("path", ""))
        absolute = spec_dir / rel
        findings.append(
            finding(
                "count",
                "count-mismatch",
                display_path(absolute, root) if absolute.exists() else rel,
                int(item.get("line") or 1),
                str(item.get("message") or "count claim disagrees with the definitions"),
                fix_direction="改为由制品导出计数（唯一 owner：pre-analyze-check.py）",
            )
        )
    return findings, {
        "status": "delegated",
        "reason": None,
        "stage": stage,
        "delegate": relative_to(delegate, root) or str(delegate),
    }


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def parse_faces(raw):
    if not raw:
        return list(FACES)
    requested = [token.strip() for token in raw.split(",") if token.strip()]
    unknown = [token for token in requested if token not in FACES]
    if unknown:
        raise InputError(
            "unknown face(s): %s (registered faces: %s)"
            % (", ".join(unknown), ", ".join(FACES))
        )
    if not requested:
        raise InputError("--faces resolved to an empty set")
    ordered = []
    for face in FACES:
        if face in requested:
            ordered.append(face)
    return ordered


def verify(spec_dir, paths, faces, root, roots=None, owner_paths=None):
    """Run the requested faces.

    ``owner_paths`` (resolved Paths) narrows the duplicate face's comparison side
    to the given owner file(s) and switches it to the owner-scoped measurement
    (``subject_pairs=False``): "is this owner's text copied into the subject set".
    The default keeps the nine-path S3 comparison side and its 069a semantics.
    """
    roots = roots or [root]
    findings = []
    degradations = []
    statuses = {}
    owner_labels = list(OWNER_PATHS)

    subjects = subject_files(spec_dir, paths)
    if owner_paths:
        comparison = {path.resolve() for path in owner_paths}
        subjects = [path for path in subjects if path.resolve() not in comparison]

    if "reader" in faces:
        if paths:
            reader_findings = check_reader(paths, root)
            findings.extend(reader_findings)
            statuses["reader"] = "fail" if reader_findings else "pass"
        else:
            statuses["reader"] = "not-applicable"

    if "evidence" in faces:
        evidence_findings, evidence_degradations = check_evidence(subjects, root)
        findings.extend(evidence_findings)
        degradations.extend(evidence_degradations)
        if evidence_findings:
            statuses["evidence"] = "fail"
        elif evidence_degradations:
            statuses["evidence"] = "not-evaluated"
        else:
            statuses["evidence"] = "pass"

    if "duplicate" in faces:
        subject_records = collect_records(subjects, root, "subject")
        owner_rels = list(OWNER_PATHS)
        if owner_paths:
            owner_records_paths = list(owner_paths)
            owner_labels = [display_path(path, root) for path in owner_records_paths]
        else:
            owner_records_paths = []
            missing_owners = []
            for rel in owner_rels:
                resolved = resolve_payload(roots, rel)
                if resolved is None:
                    missing_owners.append(rel)
                else:
                    owner_records_paths.append(resolved)
            if missing_owners:
                raise InputError(
                    "owner path not resolvable (tried %s, then the %s mirror): %s"
                    % (
                        roots[0],
                        MIRROR_DIR_NAME,
                        ", ".join(missing_owners),
                    )
                )
            owner_labels = list(OWNER_PATHS)
        # The owner set is an explicit closed list, so a mirror-resolved owner is
        # still a legitimate comparison side (see ``collect_records``).
        owner_records = collect_records(
            owner_records_paths, root, "owner", allow_mirror=True
        )
        if not owner_records:
            raise InputError(
                "owner set resolved but yielded no comparable lines: %s"
                % ", ".join(owner_labels)
            )
        duplicate_findings = check_duplicates(
            subject_records, owner_records, subject_pairs=not owner_paths
        )
        findings.extend(duplicate_findings)
        statuses["duplicate"] = "fail" if duplicate_findings else "pass"

    count_check = {"status": "not-run", "reason": "count face not requested"}
    if "count" in faces:
        count_findings, count_check = delegate_count(spec_dir, roots, root)
        findings.extend(count_findings)
        if count_check["status"] == "delegated":
            statuses["count"] = "fail" if count_findings else "pass"
        else:
            statuses["count"] = "not-evaluated"

    return findings, statuses, count_check, degradations, subjects, owner_labels


def report_payload(spec_dir, paths, files_scanned, faces, findings, count_check,
                   degradations, owners=None):
    return {
        "action": "verify",
        "checked_at": utc_now(),
        "scope": {
            "spec_dir": str(spec_dir) if spec_dir is not None else None,
            "paths": [str(path) for path in paths],
            "files_scanned": files_scanned,
            "owners": list(owners or ()),
        },
        "faces": faces,
        "findings": findings,
        "count_check": count_check,
        "degradations": degradations,
    }


def render_text(payload):
    lines = [
        "doc-consistency-check: %s" % payload["action"],
        "checked_at: %s" % payload["checked_at"],
        "faces: %s" % " ".join(
            "%s=%s" % (face, status) for face, status in payload["faces"].items()
        ),
        "files_scanned: %d" % payload["scope"]["files_scanned"],
    ]
    for item in payload.get("degradations", []):
        lines.append(
            "not-evaluated: %s at %s:%s — %s"
            % (item.get("face"), item.get("path"), item.get("line"), item.get("reason"))
        )
    count_check = payload.get("count_check") or {}
    if (
        payload["faces"].get("count") is not None
        and count_check.get("status") == "not-run"
        and count_check.get("reason")
    ):
        lines.append("count: not-run — %s" % count_check["reason"])
    for item in payload["findings"]:
        lines.append(
            "%s:%s: %s: %s"
            % (item["path"], item["line"], item["rule"], item["snippet"])
        )
        if item.get("counterpart"):
            lines.append("    counterpart: %s" % item["counterpart"])
        if item.get("fix_direction"):
            lines.append("    fix: %s" % item["fix_direction"])
    lines.append("findings: %d" % len(payload["findings"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Document-form consistency checker (069a): reader / evidence / "
                    "duplicate / count faces."
    )
    parser.add_argument("--action", default="verify", choices=("verify",))
    parser.add_argument("--spec-dir", default="")
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="a Markdown file, or a directory (all *.md recursively)",
    )
    parser.add_argument(
        "--owner-path",
        action="append",
        default=[],
        help="narrow the duplicate face's comparison side to this repo-relative owner "
             "path (repeatable); the owners are then excluded from the subject set and "
             "the measurement asks only whether their text is copied",
    )
    parser.add_argument("--faces", default="")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="deprecated alias — a not-evaluated blocking face already exits 1 by default",
    )
    parser.add_argument(
        "--allow-degraded",
        action="store_true",
        help="let a not-evaluated blocking face exit 0 (the face and its reason still "
             "appear in the payload; never use this at a blocking call site)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    try:
        faces = parse_faces(args.faces)
        spec_dir = Path(args.spec_dir).resolve() if args.spec_dir else None
        paths = []
        for item in args.path:
            path = Path(item).resolve()
            if path.is_dir():
                paths.extend(sorted(path.rglob("*.md")))
            elif path.is_file():
                paths.append(path)
            else:
                raise InputError("--path does not exist: %s" % path)
        if spec_dir is None and not paths:
            raise InputError("nothing to check: give --spec-dir and/or --path")
        if spec_dir is not None and not spec_dir.is_dir():
            raise InputError("--spec-dir is not a directory: %s" % spec_dir)

        roots = root_candidates(Path(__file__))
        root = roots[0]
        owner_paths = []
        if args.owner_path:
            missing = []
            for rel in args.owner_path:
                resolved = resolve_payload(roots, rel)
                if resolved is None:
                    missing.append(rel)
                else:
                    owner_paths.append(resolved)
            if missing:
                raise InputError(
                    "owner path not resolvable (tried %s, then the %s mirror): %s"
                    % (roots[0], MIRROR_DIR_NAME, ", ".join(missing))
                )
        findings, statuses, count_check, degradations, subjects, owner_labels = verify(
            spec_dir, paths, faces, root, roots, owner_paths
        )
    except InputError as exc:
        print("doc-consistency-check: input error: %s" % exc, file=sys.stderr)
        return 2

    findings.sort(key=lambda item: (item["path"], item["line"], item["rule"]))
    payload = report_payload(
        spec_dir,
        paths,
        len(subjects),
        statuses,
        findings,
        count_check,
        degradations,
        owner_labels,
    )

    if args.json_out:
        try:
            Path(args.json_out).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print("doc-consistency-check: cannot write --json-out: %s" % exc,
                  file=sys.stderr)
            return 2

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(render_text(payload))

    if findings:
        return 1
    # A degraded blocking face is a failure by default: "not evaluated" is not
    # "passed" (C-8). ``--allow-degraded`` is the single explicit opt-out, and
    # ``--strict`` stays accepted as an alias for the same semantics.
    degraded = any(status == "not-evaluated" for status in statuses.values())
    if "count" in faces and count_check.get("status") == "not-run":
        degraded = True
    if degraded and not args.allow_degraded:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
