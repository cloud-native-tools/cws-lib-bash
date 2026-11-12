#!/usr/bin/env python3
"""Seal engine for `/speckit.seal` (requirement 099) — CLI skeleton (work package P2).

Owner of the six-action closed set, the three-value exit domain and the write-path
allowlist. The action bodies land in later work packages on top of this surface.

Actions (exactly six; a seventh MUST NOT appear):
  merge-plan     read-only   slice set, per-artifact actions, ID maps and conflicts
  merge-apply    write       deterministic merge into the parent spec, merge-manifest.json,
                             one `**Merged into**` line per slice
  seal           write       judgment first (read-only), then one atomic write batch:
                             seal.md + registry row + feature detail
  archive-gate   read-only   archive admission verdict (0 allow / 1 refuse / 2 input error)
  archive-plan   read-only   slice-archive precondition, classification and manifest preview
  archive-apply  write       batch move into the parent spec's slices/ plus manifest write

Exit codes (exactly three; a fourth MUST NOT appear):
  0 success or idempotent (already-sealed included; an allowed archive-gate)
  1 a precondition refused (a read-only report is still complete)
  2 input or environment error (state-drift included; never read as a pass)

Two hats (C-009): the mirror position is decided by the LITERAL `.specify` component at
a fixed structural index of the engine's own resolved path — never by walking up to the
nearest `.specify` ancestor, a heuristic that self-matches in this repository. A mirror
copy refuses write actions (exit 2, reason `mirror-copy`): writing through the mirror
would break the byte-identical source/mirror pair.

Contract: `.specify/specs/099-speckit-seal/contracts/seal-engine.contract.md` (C-001…C-010)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

ENGINE_NAME = "seal-utils.py"

#: C-001 / 100 C-101: the action set is closed at exactly six values.
ACTIONS = ("merge-plan", "merge-apply", "seal", "archive-gate",
           "archive-plan", "archive-apply")
#: C-005: the two-phase declaration — which actions are pure judgments and which write.
READ_ONLY_ACTIONS = ("merge-plan", "archive-gate", "archive-plan")
WRITE_ACTIONS = ("merge-apply", "seal", "archive-apply")

#: C-002: the exit domain is closed at exactly three values.
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_INPUT_ERROR = 2
EXIT_CODES = (EXIT_OK, EXIT_REFUSED, EXIT_INPUT_ERROR)

#: C-010: the verdict a payload carries, and the exit code each verdict maps to.
VERDICTS = ("ok", "refused", "error")

#: C-009: the spec contract file that makes a directory a spec directory.
SPEC_CONTRACT_FILE = "requirements.md"

#: C-008: the write surface, as data. Any path the engine may write, relative to the
#: resolved roots; a new entry is a contract change, never an implementation detail.
WRITE_PATH_ALLOWLIST = (
    "{spec_dir}/seal.md",                 # E2 seal record
    "{spec_dir}/merge-manifest.json",     # E3 merge manifest
    "{spec_dir}/{merged_artifact}",       # E5 merged artifacts (file-level units)
    "{slice_dir}/requirements.md",        # E14 exactly one `**Merged into**` line
    "{factory_doc}",                      # C-017 recorded reference resolutions only
)

#: Stable condition codes for the engine-level (non-action) errors.
MIRROR_CODE = "mirror-copy"
SPEC_DIR_CODE = "spec-dir-invalid"

#: C-030 / E11: the archive gate's closed reason vocabulary — two admitted outcomes,
#: two refusals, two input/environment errors. A new reason is a contract change.
ARCHIVE_GATE_REASONS = (
    "sealed",                   # allowed: the status pair reads Sealed, receipt readable
    "legacy-completed-ruled",   # allowed: legacy Completed + the C-044 ruling on both carriers
    "not-sealed",               # refused: any other status pair
    "legacy-completed-unruled", # refused: legacy Completed without the C-044 ruling
    "state-drift",              # error: the carriers disagree or one is missing
    "seal-receipt-invalid",     # error: Sealed without a readable receipt
)

#: C-004: the full declared option vocabulary (the pre-parse guard judges against it).
DECLARED_OPTIONS = ("--action", "--spec-dir", "--repo", "--feature-detail",
                    "--feature-registry", "--json")


# ---------------------------------------------------------------------------
# The guard helper (C-003): `--help` / `--version` zero-side-effect, unknown
# options rejected with 2 before any action. The rule lives in the helper.
# ---------------------------------------------------------------------------

def _import_guard():
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        from script_interface_cli import (add_version_argument, configure_parser,
                                          guard_argv, version_text)
        return configure_parser, guard_argv, add_version_argument, version_text
    except ImportError:  # a bare copy without the helper still runs its actions
        def _configure(parser, **_kwargs):
            return parser

        def _guard(_argv=None, declared=None, **_kwargs):
            return None

        def _add_version(parser):
            return parser

        def _version_text(script_name, _start=None):
            return "%s %s" % (Path(script_name).name, "unknown")

        return _configure, _guard, _add_version, _version_text


_sig_configure, _sig_guard, _sig_add_version, _sig_version_text = _import_guard()


# ---------------------------------------------------------------------------
# Report rendering (C-006 / C-010): one payload, two renderings, stdout only
# ---------------------------------------------------------------------------

def _condition(code: str, evidence: str, fix_path: str, rerun: str) -> Dict[str, str]:
    return {"code": code, "evidence": evidence, "fix_path": fix_path, "rerun": rerun}


def _payload(action: Optional[str], spec_dir: Optional[Path], verdict: str,
             exit_code: int, conditions=None) -> Dict[str, Any]:
    return {
        "action": action,
        "spec_dir": str(spec_dir) if spec_dir is not None else None,
        "verdict": verdict,
        "exit_code": exit_code,
        "conditions": list(conditions or []),
    }


def render(payload: Dict[str, Any], as_json: bool) -> None:
    """Print the one judgment; the machine form is canonical (C-010)."""
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return
    print("%s %s: %s (exit %d)" % (
        ENGINE_NAME, payload["action"], payload["verdict"], payload["exit_code"]))
    plan = payload.get("plan")
    if isinstance(plan, dict) and "slices" in plan:
        basis = plan["slices"][0]["order_basis"] if plan["slices"] else "-"
        print("  slices: %d (order_basis=%s)" % (len(plan["slices"]), basis))
        for entry in plan["slices"]:
            print("    %d. %s" % (entry["order"], entry["slug"]))
        print("  artifacts: %d rows" % len(plan["artifacts"]))
        for row in plan["artifacts"]:
            print("    %-14s %s" % (row["action"], row["name"]))
        print("  id_maps: %d entries" % sum(
            len(entries) for entries in plan["id_maps"].values()))
        print("  factory_doc_refs: %d" % len(plan["factory_doc_refs"]))
        print("  conflicts: %d open" % len(
            [item for item in plan["conflicts"] if item.get("status") == "open"]))
    applied = payload.get("apply")
    if isinstance(applied, dict):
        print("  manifest: %s" % applied["manifest"])
        print("  idempotent: %s" % ("yes" if applied["idempotent"] else "no"))
        print("  slices: %s" % (", ".join(applied["slices"]) or "-"))
        print("  writes: %d" % len(applied["writes"]))
        checks = applied.get("checks", {})
        print("  checks: id_continuity=%s open_rows=%s duplicate_ids=%s "
              "dangling_refs=%s dated_records_stable=%s" % (
                  checks.get("id_continuity", "-"), checks.get("open_rows", "-"),
                  checks.get("duplicate_ids", "-"), checks.get("dangling_refs", "-"),
                  checks.get("dated_record_hashes_stable", "-")))
    sealed = payload.get("seal")
    if isinstance(sealed, dict):
        print("  outcome: %s" % sealed.get("outcome", "-"))
        if sealed.get("receipt"):
            print("  receipt: %s" % sealed["receipt"])
        print("  status: %s -> %s" % (sealed.get("from_status", "-"),
                                      sealed.get("to_status", "-")))
        print("  writes: %d" % len(sealed.get("writes") or []))
    gate = payload.get("gate")
    if isinstance(gate, dict):
        print("  allowed: %s (reason=%s)" % ("yes" if gate["allowed"] else "no",
                                             gate["reason"]))
        print("  status: %s" % (gate["status"] if gate["status"] else "-"))
        print("  pointer: %s" % gate["pointer"])
    archive = payload.get("archive")
    if isinstance(archive, dict):
        print("  outcome: %s" % (payload.get("outcome") or "-"))
        if archive.get("basis"):
            print("  basis: %s" % archive["basis"])
        for move in archive.get("moves") or []:
            print("  move: %s -> %s (%d files)"
                  % (move["from"], move["to"], move["file_count"]))
        manifest = archive.get("manifest") or {}
        checks = manifest.get("checks") if isinstance(manifest, dict) else None
        if isinstance(checks, dict):
            print("  references: live=%s dated=%s unclassified=%s unresolved=%s"
                  % (checks["live_rewrite"], checks["dated_preserved"],
                     checks["unclassified"], checks["unresolved_before"]))
        if archive.get("merge_amendments"):
            print("  merge-manifest amendments: %d"
                  % len(archive["merge_amendments"]))
    for condition in payload["conditions"]:
        print("  - %s: %s" % (condition["code"], condition["evidence"]))
        print("    fix: %s" % condition["fix_path"])
        print("    rerun: %s" % condition["rerun"])


# ---------------------------------------------------------------------------
# Path resolution (C-009): explicit paths only, fixed structural signal
# ---------------------------------------------------------------------------

def is_mirror_copy(self_path: Optional[Path] = None) -> bool:
    """Whether this engine is the `<repo>/.specify/scripts/python/` mirror copy.

    The signal is the literal `.specify` component at the fixed index that the mirror
    position dictates (`.specify/scripts/python/<name>.py` sits directly under it). Walking up
    to the nearest `.specify` ancestor is forbidden: the worktree itself may live under
    `.specify/.tmp/...`, and that heuristic would misclassify the framework source.
    """
    path = Path(self_path if self_path is not None else __file__).resolve()
    parents = path.parents
    return len(parents) >= 3 and parents[2].name == ".specify"


def resolve_spec_dir(raw: str) -> Optional[Path]:
    """Resolve `--spec-dir` against the invocation cwd; require a spec directory shape.

    The shape is `requirements.md` presence only — never a `^\\d{3}-` name prefix.
    """
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not path.is_dir():
        return None
    if not (path / SPEC_CONTRACT_FILE).is_file():
        return None
    return path


# ---------------------------------------------------------------------------
# Merge-plan surface (C-011 … C-018). Everything below reads or returns data;
# the plan action writes nothing.
# ---------------------------------------------------------------------------

#: C-013: the merge candidate universe is this closed list of fifteen names.
CANDIDATES = (
    "requirements.md", "plan.md", "tasks.md", "data-model.md", "contracts",
    "research.md", "quickstart.md", "feature-ref.md", "verification.md",
    "review.md", "code-review.md", "checklists", "checkpoints", "test-evidence",
    "notes",
)
#: C-013: directory candidates merge by file-level unit.
DIRECTORY_CANDIDATES = ("contracts", "checklists", "checkpoints", "test-evidence", "notes")
#: C-020: dated records live under these directories; they are pointed at, never copied.
DATED_RECORD_DIRS = ("checkpoints", "test-evidence")
#: C-013 mandatory floor: with a non-empty slice set these parent views are produced.
POINTER_VIEW_CANDIDATES = ("verification.md", "review.md", "code-review.md")
#: C-015: declarative ID families — a slice id must declare its parent target.
SEMANTIC_FAMILIES = ("FR", "SC", "STR")
#: C-015: mechanical ID families — collisions renumber by merge order.
MECHANICAL_FAMILIES = ("T", "C", "E")
FAMILIES = SEMANTIC_FAMILIES + MECHANICAL_FAMILIES
#: C-017: framework-source and mirror roots scanned for factory-doc references.
FACTORY_DOC_ROOTS = (
    "skills", "templates", "shared", "scripts", "agents",
    ".specify/skills", ".specify/templates", ".specify/shared",
    ".specify/scripts", ".specify/agents",
    ".claude/commands", ".github/prompts", ".opencode/command", ".qoder/commands",
)
ARTIFACT_ACTIONS = ("merge", "create", "keep", "not-applicable")
SLICE_CODE = "slice-candidate-unconfirmed"

_DEFINITION_RE = re.compile(r"^-\s+\*\*(FR|SC)-(\d{3})\*\*")
_TASK_ROW_RE = re.compile(r"^-\s+\[(.)\]\s+(T\d{3})\b")
_CLAUSE_RE = re.compile(r"^\*\*(C-\d{1,3})\*\*")
#: A slice task list groups its rows under `## Phase ...` headings; the merged
#: parent keeps those headings so story labels stay inside a story phase.
SLICE_PHASE_RE = re.compile(r"^##\s+Phase\b", re.IGNORECASE)
_ENTITY_RE = re.compile(r"^\|\s*(E\d+)\s*\|")
_STR_REF_RE = re.compile(r"\[\[(STR-\d{3})\]\]")
_DATE_RE = re.compile(r"\d{4}-?\d{2}-?\d{2}")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _rel_path(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _section(text: str, heading_pattern: str):
    """Return (body_lines, zero_based_heading_index) of the first `## ` section."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^##\s+", line) and re.search(heading_pattern, line):
            body = []
            for inner in lines[index + 1:]:
                if re.match(r"^##\s+", inner):
                    break
                body.append(inner)
            return body, index
    return None, None


def _canonical_id(cell: str) -> Optional[str]:
    match = re.match(r"^\s*`?((?:FR|SC|STR)-\d{3}|T\d{3}|C-\d{1,3}|E\d+)`?\s*$", cell)
    return match.group(1) if match else None


def _target_id(cell: str) -> Optional[str]:
    match = re.search(r"(FR|SC|STR)[- ]?(\d{3})", cell)
    if match:
        return "%s-%s" % (match.group(1), match.group(2))
    match = re.search(r"\b(T\d{3}|C-\d{1,3}|E\d+)\b", cell)
    return match.group(1) if match else None


def _parse_section_rewrite(text: str):
    if "\u00a7" not in text:
        return None
    left, _, right = text.partition("\u00a7")
    artifact = left.strip().strip("`").strip()
    heading = right.strip().strip("`").strip()
    heading = re.sub(r"^#+\s*", "", heading)
    if not artifact or not heading:
        return None
    return artifact, heading


def _parse_parent_mapping(text: str) -> Dict[str, Any]:
    """Parse the `## Parent Mapping` declaration: id rows and declared section rewrites."""
    body, start = _section(text, r"Parent Mapping")
    result = {"declared": body is not None, "mappings": [], "sections": []}
    if body is None:
        return result
    heading = ""
    for offset, line in enumerate(body):
        line_no = (start or 0) + 2 + offset
        if re.match(r"^###\s+", line):
            heading = line
            continue
        if heading and "Section Rewrites" in heading:
            bullet = re.match(r"^\s*-\s+(.+)$", line)
            parsed = _parse_section_rewrite(bullet.group(1)) if bullet else None
            if parsed:
                result["sections"].append(
                    {"artifact": parsed[0], "heading": parsed[1], "line": line_no})
            continue
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        local = _canonical_id(cells[0])
        target = _target_id(cells[1])
        if local and target:
            result["mappings"].append(
                {"slice_id": local, "parent_id": target, "line": line_no})
    return result


def _parse_shared_strings(text: str) -> Dict[str, Dict[str, Any]]:
    body, start = _section(text, r"Shared Strings")
    registry: Dict[str, Dict[str, Any]] = {}
    for offset, line in enumerate(body or []):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.match(r"^`?(STR-\d{3})`?$", cells[0])
        if not match:
            continue
        literal = cells[1].strip().strip("`").strip()
        if len(literal) >= 2 and literal.startswith("\"") and literal.endswith("\""):
            literal = literal[1:-1]
        registry[match.group(1)] = {"literal": literal,
                                    "line": (start or 0) + 2 + offset}
    return registry


def _definition_lines(text: str):
    entries = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = _DEFINITION_RE.match(line)
        if match:
            entries.append({"id": "%s-%s" % (match.group(1), match.group(2)),
                            "line": line_no, "text": _normalize(line)})
    return entries


def _task_rows(text: str, state: Optional[str] = None):
    entries = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = _TASK_ROW_RE.match(line)
        if match and (state is None or match.group(1) == state):
            entries.append({"id": match.group(2), "line": line_no, "text": _normalize(line)})
    return entries


def _contract_clauses(path: Path):
    entries = []
    if not path.is_file():
        return entries
    for line_no, line in enumerate(_read_text(path).splitlines(), 1):
        match = _CLAUSE_RE.match(line)
        if match:
            entries.append({"id": match.group(1), "line": line_no, "text": _normalize(line)})
    return entries


def _entity_rows(path: Path):
    entries = []
    if not path.is_file():
        return entries
    for line_no, line in enumerate(_read_text(path).splitlines(), 1):
        match = _ENTITY_RE.match(line)
        if match:
            entries.append({"id": match.group(1), "line": line_no, "text": _normalize(line)})
    return entries


def _id_number(family: str, identifier: str) -> int:
    if family == "T":
        return int(identifier[1:])
    if family == "E":
        return int(identifier[1:])
    return int(identifier.split("-")[1])


def _format_id(family: str, number: int) -> str:
    if family == "T":
        return "T%03d" % number
    if family == "E":
        return "E%d" % number
    return "%s-%03d" % (family, number)


# ---------------------------------------------------------------------------
# Slice discovery (C-011) and order derivation (C-012)
# ---------------------------------------------------------------------------

def _slice_name_pattern(parent_slug: str):
    match = re.match(r"^(\d{3})", parent_slug)
    if not match:
        return None
    return re.compile(r"^%s[A-Za-z]+-[a-z0-9][a-z0-9-]*$" % match.group(1))


def _declares_parent(text: str, parent_slug: str) -> bool:
    field = re.search(r"^\*\*Parent spec\*\*:\s*(.+)$", text, re.M)
    if field and parent_slug in field.group(1):
        return True
    body, _ = _section(text, r"Parent Mapping")
    return body is not None and parent_slug in "\n".join(body)


# ---------------------------------------------------------------------------
# Manifest-aware slice discovery (100 C-112)
# ---------------------------------------------------------------------------

ARCHIVE_MANIFEST_NAME = "archive-manifest.json"
ARCHIVE_SLICES_DIR = "slices"
ARCHIVE_MANIFEST_KEYS = frozenset((
    "schema_version", "spec", "spec_path", "generated_by", "pinned_commit",
    "order_basis", "order_source", "slices", "references", "merge_manifest",
    "checks", "digest",
))
ARCHIVE_SLICE_KEYS = frozenset((
    "slug", "from", "to", "order", "file_count", "files", "merged_into_pointer",
))
ARCHIVE_ORDER_BASES = ("split-record", "letter-order")


class ArchiveManifestError(ValueError):
    """C-112: the archived layout cannot be read as the same slice set."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _archive_invalid(message: str) -> ArchiveManifestError:
    return ArchiveManifestError("archive-manifest-invalid", message)


def _archive_drift(message: str) -> ArchiveManifestError:
    return ArchiveManifestError("archive-drift", message)


def _archive_manifest_error(action: str, spec_dir: Path,
                            exc: ArchiveManifestError) -> Dict[str, Any]:
    return _payload(
        action, spec_dir, "error", EXIT_INPUT_ERROR,
        [_condition(
            exc.code, str(exc),
            "repair or restore %s so it agrees with %s and the spec tree"
            % (ARCHIVE_MANIFEST_NAME, MANIFEST_NAME),
            "rerun %s after the archive record is repaired" % action,
        )],
    )


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# Archive planning vocabulary and the single manifest validator (100 C-103,
# C-201…C-212). One validator serves reading, planning and (later) apply.
# ---------------------------------------------------------------------------

ARCHIVE_OUTCOMES = ("would-archive", "archived", "already-archived",
                    "not-applicable")
ARCHIVE_REFUSAL_REASONS = ("destination-exists", "dirty-spec-tree",
                           "conflict-open", "slice-unclosed",
                           "unresolved-references", "unclassified-reference")
ARCHIVE_ERROR_REASONS = ("merge-manifest-missing", "merge-manifest-invalid",
                         "slice-missing", "partial-archive", "archive-drift",
                         "archive-manifest-invalid", "not-a-git-tree",
                         "mirror-copy", "write-failed")
ARCHIVE_ERROR_CODES = frozenset(ARCHIVE_ERROR_REASONS)

ARCHIVE_GENERATED_KEYS = frozenset(("engine", "version", "command"))
ARCHIVE_REFERENCES_KEYS = frozenset(("rows", "runtime"))
ARCHIVE_ROW_KEYS = frozenset(("carrier", "line", "before", "after", "kind"))
ARCHIVE_RUNTIME_KEYS = frozenset(("carrier", "status", "reason", "updates"))
ARCHIVE_RUNTIME_UPDATE_KEYS = frozenset(("line", "before", "after"))
ARCHIVE_MERGE_KEYS = frozenset(("path", "digest_before", "digest_after"))
ARCHIVE_CHECKS_KEYS = frozenset((
    "preconditions", "moved_files", "live_rewrite", "dated_preserved",
    "unclassified", "unresolved_before", "unresolved_after", "runtime_carriers",
    "files_match",
))
ARCHIVE_CONDITION_KEYS = frozenset((
    "merge_status", "open_conflicts", "slices_closed", "dirty_spec_tree",
    "side_presence",
))
ARCHIVE_SIDE_VALUES = frozenset(("source", "destination", "both", "missing"))
ARCHIVE_KINDS = ("live-rewrite", "dated-preserved")
ARCHIVE_RUNTIME_STATUSES = ("runtime-updated", "absent")

ARCHIVE_HEX_RE = re.compile(r"^[0-9a-f]{40}$")
ARCHIVE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ARCHIVE_LIVE_DOCUMENTS = frozenset((
    "requirements.md", "plan.md", "tasks.md", "data-model.md", "research.md",
    "quickstart.md", "feature-ref.md", "verification.md", "review.md",
    "code-review.md",
))
ARCHIVE_LIVE_FILES = frozenset((
    ".specify/register.md", ".specify/glossary.md", ".specify/instructions.md",
))
ARCHIVE_DATED_SUBDIRS = ("notes/", "test-evidence/", "checklists/", "slices/")
ARCHIVE_LIVE_TREES = (".specify/shared/", ".specify/shared/", "tests/")
ARCHIVE_DATED_TREES = (".specify/memory/", ".specify/history/")
ARCHIVE_FEATURES_DETAIL_PREFIX = ".specify/features/"
ARCHIVE_MIXED_HEADING_RE = re.compile(
    r"^##\s+Related Specifications/Requirements\s*$")
ARCHIVE_MIXED_HEADING_BYTES_RE = re.compile(
    rb"^##\s+Related Specifications/Requirements\s*$")


def archive_manifest_digest(document: Dict[str, Any]) -> str:
    """C-034/C-207: sha256 over the sorted compact JSON with `digest` removed."""
    body = dict(document)
    body.pop("digest", None)
    canonical = json.dumps(body, separators=(",", ":"), sort_keys=True,
                           ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def archive_closure_errors(document: Dict[str, Any]) -> list:
    """C-206: the three closure arithmetic families, reported by name."""
    errors = []
    references = document.get("references")
    checks = document.get("checks")
    slices = document.get("slices")
    if not isinstance(references, dict) or not isinstance(checks, dict) \
            or not isinstance(slices, list):
        return ["document lacks a usable slices/references/checks surface"]
    rows = references.get("rows")
    runtime = references.get("runtime")
    if not isinstance(rows, list) or not isinstance(runtime, list):
        return ["references rows/runtime are not lists"]
    live = checks.get("live_rewrite")
    dated = checks.get("dated_preserved")
    unclassified = checks.get("unclassified")
    carriers = checks.get("runtime_carriers")
    moved = checks.get("moved_files")
    for name, value in (("live_rewrite", live), ("dated_preserved", dated),
                        ("unclassified", unclassified),
                        ("runtime_carriers", carriers), ("moved_files", moved)):
        if not _is_int(value):
            errors.append("checks.%s is not an integer" % name)
    if _is_int(live) and _is_int(dated) and live + dated != len(rows):
        errors.append(
            "live_rewrite + dated_preserved (%d) != len(references.rows) (%d)"
            % (live + dated, len(rows)))
    if _is_int(carriers):
        counted = sum(1 for row in runtime
                      if isinstance(row, dict)
                      and row.get("status") in ARCHIVE_RUNTIME_STATUSES)
        if counted != carriers:
            errors.append(
                "runtime-updated + absent (%d) != runtime_carriers (%d)"
                % (counted, carriers))
    if _is_int(moved):
        total = sum(entry.get("file_count", 0) for entry in slices
                    if isinstance(entry, dict)
                    and _is_int(entry.get("file_count")))
        if total != moved:
            errors.append(
                "sum(slices[].file_count) (%d) != moved_files (%d)"
                % (total, moved))
    return errors


def _archive_path_ok(value) -> bool:
    return (isinstance(value, str) and bool(value)
            and not value.startswith("/") and "\\" not in value
            and ".." not in value.split("/"))


def _archive_exact_keys(container, keys, where: str, label: str) -> None:
    missing = sorted(keys - set(container))
    unknown = sorted(set(container) - keys)
    if missing or unknown:
        raise _archive_invalid(
            "%s %s key set is not the closed set (missing=%s; unknown=%s)"
            % (label, where, missing or "none", unknown or "none"))


def validate_archive_manifest(document: Dict[str, Any], spec_name: str,
                              label: str = ARCHIVE_MANIFEST_NAME) -> None:
    """C-202…C-209: every closed level, the path basis, arithmetic and digest.

    Shared by the read path and the plan/apply write paths — there is exactly
    one validator (C-209). Any violation is `archive-manifest-invalid` (exit 2).
    """
    if not isinstance(document, dict):
        raise _archive_invalid("%s does not carry a JSON object" % label)
    _archive_exact_keys(document, ARCHIVE_MANIFEST_KEYS, "top-level", label)
    if document["schema_version"] != 1:
        raise _archive_invalid(
            "%s schema_version reads %r; this engine reads and writes only 1"
            % (label, document["schema_version"]))
    if document["spec"] != spec_name:
        raise _archive_invalid(
            "%s names spec %r, not %r" % (label, document["spec"], spec_name))
    expected_spec_path = ".specify/specs/%s" % spec_name
    if document["spec_path"] != expected_spec_path:
        raise _archive_invalid(
            "%s spec_path reads %r, not %r"
            % (label, document["spec_path"], expected_spec_path))
    generated = document["generated_by"]
    if not isinstance(generated, dict):
        raise _archive_invalid("%s generated_by is not an object" % label)
    _archive_exact_keys(generated, ARCHIVE_GENERATED_KEYS,
                        "generated_by", label)
    if not all(isinstance(generated[key], str) and generated[key]
               for key in ARCHIVE_GENERATED_KEYS):
        raise _archive_invalid(
            "%s generated_by fields must all be non-empty strings" % label)
    if not isinstance(document["pinned_commit"], str) \
            or not ARCHIVE_HEX_RE.match(document["pinned_commit"]):
        raise _archive_invalid(
            "%s pinned_commit is not a 40-character lowercase hex commit" % label)
    if document["order_basis"] not in ARCHIVE_ORDER_BASES:
        raise _archive_invalid(
            "%s order_basis reads %r; the closed set is %s"
            % (label, document["order_basis"], list(ARCHIVE_ORDER_BASES)))
    if not isinstance(document["order_source"], str) or not document["order_source"]:
        raise _archive_invalid("%s order_source is not a non-empty string" % label)

    if not isinstance(document["slices"], list):
        raise _archive_invalid("%s slices is not a list" % label)
    orders = []
    for position, entry in enumerate(document["slices"], 1):
        where = "slices[%d]" % position
        if not isinstance(entry, dict):
            raise _archive_invalid("%s %s is not an object" % (label, where))
        _archive_exact_keys(entry, ARCHIVE_SLICE_KEYS, where, label)
        for key in ("slug", "from", "to"):
            if not isinstance(entry[key], str) or not entry[key]:
                raise _archive_invalid(
                    "%s %s.%s is not a non-empty path" % (label, where, key))
        if not _archive_path_ok(entry["from"]) or not _archive_path_ok(entry["to"]):
            raise _archive_invalid(
                "%s %s from/to is not a repository-relative POSIX path"
                % (label, where))
        if entry["from"] != ".specify/specs/%s" % entry["slug"] \
                or entry["to"] != "%s/slices/%s" % (expected_spec_path, entry["slug"]):
            raise _archive_invalid(
                "%s %s does not carry the declared from/to pair" % (label, where))
        if not _is_int(entry["order"]):
            raise _archive_invalid("%s %s.order is not an integer" % (label, where))
        orders.append(entry["order"])
        files = entry["files"]
        if not isinstance(files, list) or not _is_int(entry["file_count"]) \
                or entry["file_count"] != len(files):
            raise _archive_invalid(
                "%s %s.file_count does not equal its files row count"
                % (label, where))
        paths = []
        for row in files:
            if not isinstance(row, dict):
                raise _archive_invalid("%s %s.files row is not an object"
                                       % (label, where))
            _archive_exact_keys(row, frozenset(("path", "sha256")),
                                where + ".files", label)
            if not _archive_path_ok(row["path"]):
                raise _archive_invalid(
                    "%s %s.files path is not slice-relative" % (label, where))
            if not isinstance(row["sha256"], str) \
                    or not re.match(r"^[0-9a-f]{64}$", row["sha256"]):
                raise _archive_invalid(
                    "%s %s.files sha256 is not a 64-character lowercase hex digest"
                    % (label, where))
            paths.append(row["path"])
        if paths != sorted(paths):
            raise _archive_invalid(
                "%s %s.files is not sorted by path" % (label, where))
        pointer = entry["merged_into_pointer"]
        if not isinstance(pointer, dict):
            raise _archive_invalid(
                "%s %s.merged_into_pointer is not an object" % (label, where))
        _archive_exact_keys(pointer, frozenset(("path", "line")),
                            where + ".merged_into_pointer", label)
        if pointer["path"] != entry["to"] + "/requirements.md" \
                or not _archive_path_ok(pointer["path"]):
            raise _archive_invalid(
                "%s %s.merged_into_pointer.path does not name the archived "
                "requirements.md" % (label, where))
        if not _is_int(pointer["line"]) or pointer["line"] < 1:
            raise _archive_invalid(
                "%s %s.merged_into_pointer.line is not a 1-based line number"
                % (label, where))
    if orders != sorted(orders) or orders != list(range(1, len(orders) + 1)):
        raise _archive_invalid(
            "%s slices are not sorted by a contiguous 1..n order set" % label)

    references = document["references"]
    if not isinstance(references, dict):
        raise _archive_invalid("%s references is not an object" % label)
    _archive_exact_keys(references, ARCHIVE_REFERENCES_KEYS, "references", label)
    if not isinstance(references["rows"], list) \
            or not isinstance(references["runtime"], list):
        raise _archive_invalid(
            "%s references rows/runtime must both be lists" % label)
    row_keys = []
    for position, row in enumerate(references["rows"], 1):
        where = "references.rows[%d]" % position
        if not isinstance(row, dict):
            raise _archive_invalid("%s %s is not an object" % (label, where))
        _archive_exact_keys(row, ARCHIVE_ROW_KEYS, where, label)
        if not _archive_path_ok(row["carrier"]):
            raise _archive_invalid(
                "%s %s.carrier is not a repository-relative POSIX path"
                % (label, where))
        if not _is_int(row["line"]) or row["line"] < 1:
            raise _archive_invalid("%s %s.line is not 1-based" % (label, where))
        if not isinstance(row["before"], str) or not isinstance(row["after"], str):
            raise _archive_invalid(
                "%s %s before/after are not strings" % (label, where))
        if row["kind"] not in ARCHIVE_KINDS:
            raise _archive_invalid(
                "%s %s.kind reads %r; the closed set is %s"
                % (label, where, row["kind"], list(ARCHIVE_KINDS)))
        if row["kind"] == "dated-preserved" and row["before"] != row["after"]:
            raise _archive_invalid(
                "%s %s is dated-preserved but its bytes changed" % (label, where))
        row_keys.append((row["carrier"], row["line"]))
    if row_keys != sorted(row_keys):
        raise _archive_invalid(
            "%s references.rows is not sorted by (carrier, line)" % label)
    declared_state = [".specify/state/%s.md" % spec_name] + [
        ".specify/state/%s.md" % entry["slug"] for entry in document["slices"]]
    actual_state = [row.get("carrier") for row in references["runtime"]
                    if isinstance(row, dict)]
    if actual_state != declared_state:
        raise _archive_invalid(
            "%s references.runtime carriers read %r; the declared carrier set is %r"
            % (label, actual_state, declared_state))
    for position, row in enumerate(references["runtime"], 1):
        where = "references.runtime[%d]" % position
        if not isinstance(row, dict):
            raise _archive_invalid("%s %s is not an object" % (label, where))
        _archive_exact_keys(row, ARCHIVE_RUNTIME_KEYS, where, label)
        if row["status"] not in ARCHIVE_RUNTIME_STATUSES:
            raise _archive_invalid(
                "%s %s.status reads %r; the closed set is %s"
                % (label, where, row["status"], list(ARCHIVE_RUNTIME_STATUSES)))
        if row["status"] == "absent":
            if not isinstance(row["reason"], str) or not row["reason"]:
                raise _archive_invalid(
                    "%s %s is absent without a reason" % (label, where))
            if row["updates"] != []:
                raise _archive_invalid(
                    "%s %s is absent but carries updates" % (label, where))
        elif row["reason"] is not None:
            raise _archive_invalid(
                "%s %s is runtime-updated but carries a reason" % (label, where))
        if not isinstance(row["updates"], list):
            raise _archive_invalid("%s %s.updates is not a list" % (label, where))
        for update in row["updates"]:
            if not isinstance(update, dict):
                raise _archive_invalid(
                    "%s %s.updates row is not an object" % (label, where))
            _archive_exact_keys(update, ARCHIVE_RUNTIME_UPDATE_KEYS,
                                where + ".updates", label)
            if not _is_int(update["line"]) or update["line"] < 1 \
                    or not isinstance(update["before"], str) \
                    or not isinstance(update["after"], str):
                raise _archive_invalid(
                    "%s %s.updates row is malformed" % (label, where))

    merge = document["merge_manifest"]
    if not isinstance(merge, dict):
        raise _archive_invalid("%s merge_manifest is not an object" % label)
    _archive_exact_keys(merge, ARCHIVE_MERGE_KEYS, "merge_manifest", label)
    if merge["path"] != MANIFEST_NAME:
        raise _archive_invalid(
            "%s merge_manifest.path reads %r, not %r"
            % (label, merge["path"], MANIFEST_NAME))
    for key in ("digest_before", "digest_after"):
        if not isinstance(merge[key], str) or not ARCHIVE_DIGEST_RE.match(merge[key]):
            raise _archive_invalid(
                "%s merge_manifest.%s is not a `sha256:` digest" % (label, key))

    checks = document["checks"]
    if not isinstance(checks, dict):
        raise _archive_invalid("%s checks is not an object" % label)
    _archive_exact_keys(checks, ARCHIVE_CHECKS_KEYS, "checks", label)
    preconditions = checks["preconditions"]
    if not isinstance(preconditions, dict):
        raise _archive_invalid("%s checks.preconditions is not an object" % label)
    _archive_exact_keys(preconditions, ARCHIVE_CONDITION_KEYS,
                        "checks.preconditions", label)
    if preconditions["merge_status"] not in ("merged", "not-applicable"):
        raise _archive_invalid(
            "%s checks.preconditions.merge_status reads %r"
            % (label, preconditions["merge_status"]))
    if not _is_int(preconditions["open_conflicts"]):
        raise _archive_invalid(
            "%s checks.preconditions.open_conflicts is not an integer" % label)
    if not isinstance(preconditions["slices_closed"], bool) \
            or not isinstance(preconditions["dirty_spec_tree"], bool):
        raise _archive_invalid(
            "%s checks.preconditions booleans are not booleans" % label)
    side_presence = preconditions["side_presence"]
    expected_slugs = {entry["slug"] for entry in document["slices"]}
    if not isinstance(side_presence, dict) \
            or set(side_presence) != expected_slugs \
            or any(value not in ARCHIVE_SIDE_VALUES
                   for value in side_presence.values()):
        raise _archive_invalid(
            "%s checks.preconditions.side_presence is not the declared slug map "
            "over {source, destination, both, missing}" % label)
    for key in ("moved_files", "live_rewrite", "dated_preserved", "unclassified",
                "unresolved_before", "unresolved_after", "runtime_carriers"):
        if not _is_int(checks[key]):
            raise _archive_invalid("%s checks.%s is not an integer" % (label, key))
    if not isinstance(checks["files_match"], bool):
        raise _archive_invalid("%s checks.files_match is not a boolean" % label)
    errors = archive_closure_errors(document)
    if errors:
        raise _archive_invalid(
            "%s closure arithmetic does not hold: %s" % (label, "; ".join(errors)))
    if not isinstance(document["digest"], str) \
            or not ARCHIVE_DIGEST_RE.match(document["digest"]):
        raise _archive_invalid("%s digest is not a `sha256:` digest" % label)
    if archive_manifest_digest(document) != document["digest"]:
        raise _archive_invalid(
            "%s digest does not match its C-034 recomputation" % label)


def _read_archive_manifest(spec_dir: Path) -> Optional[Dict[str, Any]]:
    """C-112/C-202/C-209: read the archive record; absent means "no archive".

    The record is validated before it is believed — one shared validator covers
    every closed level, the path basis, arithmetic and the digest.
    """
    path = spec_dir / ARCHIVE_MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        document = json.loads(_read_text(path))
    except ValueError as exc:
        raise _archive_invalid("%s is unparsable: %s" % (path.name, exc))
    validate_archive_manifest(document, spec_dir.name, path.name)
    return document



def _archived_slice_records(repo: Path, spec_dir: Path, document: Dict[str, Any]):
    """Validate the record against the merge manifest and the tree; same slice set."""
    merge_path = spec_dir / MANIFEST_NAME
    if not merge_path.is_file():
        raise _archive_drift(
            "%s exists but %s is absent; the archived set has no merge record to "
            "agree with" % (ARCHIVE_MANIFEST_NAME, MANIFEST_NAME))
    try:
        merge_document = json.loads(_read_text(merge_path))
    except ValueError as exc:
        raise _archive_drift(
            "%s is unparsable next to %s: %s"
            % (MANIFEST_NAME, ARCHIVE_MANIFEST_NAME, exc))
    recorded = {}
    for entry in (merge_document.get("slices")
                  if isinstance(merge_document, dict) else None) or []:
        if isinstance(entry, dict) and isinstance(entry.get("slug"), str):
            recorded[entry["slug"]] = entry
    archived = {entry["slug"]: entry for entry in document["slices"]}
    if set(archived) != set(recorded):
        raise _archive_drift(
            "%s slice set disagrees with %s (archive-only=%s; merge-only=%s)"
            % (ARCHIVE_MANIFEST_NAME, MANIFEST_NAME,
               sorted(set(archived) - set(recorded)),
               sorted(set(recorded) - set(archived))))
    slices = []
    for entry in sorted(document["slices"], key=lambda item: item["order"]):
        slug = entry["slug"]
        expected_from = ".specify/specs/%s" % slug
        expected_to = ".specify/specs/%s/%s/%s" % (
            spec_dir.name, ARCHIVE_SLICES_DIR, slug)
        if entry["from"] != expected_from or entry["to"] != expected_to:
            raise _archive_drift(
                "%s entry %s reads from=%r to=%r; the declared pair is %r -> %r"
                % (ARCHIVE_MANIFEST_NAME, slug, entry["from"], entry["to"],
                   expected_from, expected_to))
        recorded_entry = recorded[slug]
        if _is_int(recorded_entry.get("order")) \
                and recorded_entry["order"] != entry["order"]:
            raise _archive_drift(
                "%s order for %s reads %r while %s records %r"
                % (ARCHIVE_MANIFEST_NAME, slug, entry["order"], MANIFEST_NAME,
                   recorded_entry["order"]))
        target_dir = repo / entry["to"]
        if (repo / entry["from"]).exists():
            raise _archive_drift(
                "slice %s is still present at its source %s" % (slug, entry["from"]))
        if not target_dir.is_dir():
            raise _archive_drift(
                "archived slice directory is missing: %s" % entry["to"])
        requirements = target_dir / "requirements.md"
        if not requirements.is_file():
            raise _archive_drift(
                "archived slice carries no requirements.md: %s/requirements.md"
                % entry["to"])
        listed = {row["path"] for row in entry["files"]}
        on_disk = {path.relative_to(target_dir).as_posix()
                   for path in target_dir.rglob("*") if path.is_file()}
        if listed != on_disk:
            raise _archive_drift(
                "slice %s file set disagrees with %s (recorded-only=%s; tree-only=%s)"
                % (slug, ARCHIVE_MANIFEST_NAME, sorted(listed - on_disk),
                   sorted(on_disk - listed)))
        pointer_path = entry["merged_into_pointer"]["path"]
        if pointer_path != entry["to"] + "/requirements.md":
            raise _archive_drift(
                "slice %s merged_into_pointer.path reads %r, not its archived "
                "requirements.md" % (slug, pointer_path))
        slices.append({
            "slug": slug,
            "path": target_dir,
            "requirements": requirements,
            "text": _read_text(requirements),
            "archive_order": entry["order"],
            "archive_order_basis": document["order_basis"],
            "archive_order_source": document["order_source"],
        })
    return slices, []


def _discover_slices(spec_dir: Path, repo: Path):
    """C-011 / C-112: the slice set, read from the archive record when it exists."""
    archive = _read_archive_manifest(spec_dir)
    if archive is not None:
        return _archived_slice_records(repo, spec_dir, archive)
    slices_dir = spec_dir / ARCHIVE_SLICES_DIR
    if slices_dir.is_dir() and any(slices_dir.iterdir()):
        raise _archive_drift(
            "%s is populated but %s is absent; an archived layout is never read "
            "back as a sibling scan"
            % (ARCHIVE_SLICES_DIR + "/", ARCHIVE_MANIFEST_NAME))
    parent_slug = spec_dir.name
    pattern = _slice_name_pattern(parent_slug)
    slices, excluded = [], []
    specs_root = spec_dir.parent
    if not specs_root.is_dir():
        return slices, excluded
    for entry in sorted(specs_root.iterdir(), key=lambda item: item.name):
        if not entry.is_dir() or entry.resolve() == spec_dir.resolve():
            continue
        requirements = entry / "requirements.md"
        if not requirements.is_file():
            continue
        text = _read_text(requirements)
        name_hit = bool(pattern and pattern.match(entry.name))
        declared = _declares_parent(text, parent_slug)
        if name_hit and declared:
            slices.append({"slug": entry.name, "path": entry,
                           "requirements": requirements, "text": text})
        elif name_hit or declared:
            excluded.append({"slug": entry.name, "path": entry,
                             "requirements": requirements,
                             "missing": "parent-declaration" if name_hit else "name-family"})
    return slices, excluded


def _derive_order(repo: Path, parent_slug: str, slices):
    archived = [item for item in slices if "archive_order" in item]
    if archived:
        if len(archived) != len(slices):
            raise _archive_drift(
                "%s mixes archived and sibling slice records" % parent_slug)
        ordered = sorted(slices, key=lambda item: item["archive_order"])
        orders = [item["archive_order"] for item in ordered]
        if orders != list(range(1, len(ordered) + 1)):
            raise _archive_drift(
                "%s order values are not the contiguous 1..n set: %r"
                % (ARCHIVE_MANIFEST_NAME, orders))
        bases = {item["archive_order_basis"] for item in ordered}
        sources = {item["archive_order_source"] for item in ordered}
        if len(bases) != 1 or len(sources) != 1:
            raise _archive_drift(
                "%s carries inconsistent parent-level order fields"
                % ARCHIVE_MANIFEST_NAME)
        basis = bases.pop()
        source = sources.pop()
        return [{
            "slug": item["slug"],
            "order": item["archive_order"],
            "order_basis": basis,
            "order_source": source,
            "path": item["path"],
            "requirements": item["requirements"],
            "text": item["text"],
        } for item in ordered]
    state_path = repo / ".specify" / "state" / ("%s.md" % parent_slug)
    slugs = [item["slug"] for item in slices]
    basis = "letter-order"
    source = "directory-name sort (no split record at .specify/state/%s.md)" % parent_slug
    ordered = sorted(slugs)
    if state_path.is_file():
        body, _ = _section(_read_text(state_path), r"拆分记录")
        found = []
        for index, line in enumerate(body or []):
            if not re.match(r"^\s*(?:[-*]\s*)?proposed_slices\s*:", line):
                continue
            for inner in body[index + 1:]:
                if not inner.strip():
                    continue
                if not re.match(r"^\s+[-*]\s+", inner):
                    break
                match = re.search(r"\d{3}[A-Za-z]+-[a-z0-9-]+", inner)
                if match and match.group(0) in slugs and match.group(0) not in found:
                    found.append(match.group(0))
            break
        if found:
            remainder = sorted(slug for slug in slugs if slug not in found)
            ordered = found + remainder
            basis = "split-record"
            source = ".specify/state/%s.md#拆分记录.proposed_slices" % parent_slug
            if remainder:
                source += " (record omits %s; appended in letter order)" % ",".join(remainder)
    ordered_slices = []
    for position, slug in enumerate(ordered, 1):
        item = next(entry for entry in slices if entry["slug"] == slug)
        ordered_slices.append({
            "slug": slug,
            "order": position,
            "order_basis": basis,
            "order_source": source,
            "path": item["path"],
            "requirements": item["requirements"],
            "text": item["text"],
        })
    return ordered_slices


# ---------------------------------------------------------------------------
# Archive reference classification (100 C-301…C-311). Pure, path-and-line
# predicates only — no semantic reading, no model judgment.
# ---------------------------------------------------------------------------

def _f1_pattern(slug: str):
    return re.compile(
        r"(?<![/.\w-])\.specify/specs/%s(?![A-Za-z0-9_-])" % re.escape(slug))


def _f2_pattern(slug: str):
    return re.compile(r"(?<![A-Za-z0-9_./-])%s/" % re.escape(slug))


def _is_path_construction(line: str) -> bool:
    return (".specify" in line and "specs" in line
            and ("Path" in line or " / " in line or " + " in line
                 or 'f"' in line or "f'" in line))


def find_reference_hits(line: str, slugs, *, parent_slug: str,
                        carrier_rel: str, tests_carrier: bool = False) -> list:
    """C-302: the closed F1/F2/F3 forms on one line, longest form wins.

    Overlaps are resolved in declaration order: F1 first, F2 only outside F1,
    F3 only outside both. A bare slug never produces a hit.
    """
    patterns = list(slugs)
    spec_rel = ".specify/specs/%s" % parent_slug if parent_slug else ""
    in_parent = bool(spec_rel) and carrier_rel.startswith(spec_rel + "/")
    hits, spans = [], []

    def add(slug, form, start, end, replacement):
        if any(start < other_end and end > other_start
               for other_start, other_end in spans):
            return
        spans.append((start, end))
        hits.append({"slug": slug, "form": form, "start": start, "end": end,
                     "replacement": replacement})

    for slug in sorted(patterns, key=len, reverse=True):
        for match in _f1_pattern(slug).finditer(line):
            add(slug, "F1", match.start(), match.end(),
                ("%s/slices/%s" % (spec_rel, slug)) if spec_rel
                else ".specify/specs/%s/slices/%s" % (parent_slug, slug))
    if in_parent:
        for slug in sorted(patterns, key=len, reverse=True):
            for match in _f2_pattern(slug).finditer(line):
                add(slug, "F2", match.start(), match.end(),
                    "slices/%s/" % slug)
    if tests_carrier and _is_path_construction(line):
        for slug in sorted(patterns, key=len, reverse=True):
            for match in re.finditer(r"(['\"])%s\1" % re.escape(slug), line):
                start, end = match.start(1) + 1, match.end() - 1
                prefix = line[:match.start(1)].rstrip()
                if prefix.endswith("==") or prefix.endswith("!="):
                    continue
                add(slug, "F3", start, end,
                    "%s/slices/%s" % (parent_slug, slug))
    return sorted(hits, key=lambda hit: hit["start"])


def loose_source_hits(line: str, slugs, hits=None) -> list:
    """C-302: source-path shapes outside F1/F2/F3, attributed to their slice."""
    if hits is None:
        hits = find_reference_hits(line, slugs, parent_slug="", carrier_rel="",
                                   tests_carrier=False)
    spans = [(hit["start"], hit["end"]) for hit in hits]
    found = []
    for slug in slugs:
        for match in re.finditer(
                r"(?<![\w-])\.specify/specs/%s(?![A-Za-z0-9_-])"
                % re.escape(slug), line):
            if any(match.start() < end and match.end() > start
                   for start, end in spans):
                continue
            found.append({"slug": slug, "form": ".specify/specs/%s" % slug,
                          "start": match.start(), "end": match.end()})
        for match in re.finditer(
                r"(?<![\w-])(?:\.\./)+%s(?![A-Za-z0-9_-])" % re.escape(slug),
                line):
            found.append({"slug": slug, "form": "../%s" % slug,
                          "start": match.start(), "end": match.end()})
    found.sort(key=lambda item: item["start"])
    return found


def loose_source_forms(line: str, slugs, hits=None) -> list:
    """C-302: source-path shapes outside F1/F2/F3 must fail closed."""
    return [hit["form"] for hit in loose_source_hits(line, slugs, hits=hits)]


def _joined_needle_line(lines, needle: str) -> int:
    """C-302: map a cross-line occurrence's start back to its 1-based line."""
    offsets, parts, position = [], [], 0
    for line in lines:
        stripped = line.strip()
        offsets.append(position)
        parts.append(stripped)
        position += len(stripped)
    index = "".join(parts).find(needle)
    if index < 0:
        return 1
    line_no = 1
    for position, offset in enumerate(offsets, 1):
        if offset <= index:
            line_no = position
        else:
            break
    return line_no


def rewrite_line(line: str, hits) -> str:
    result = line
    for hit in sorted(hits, key=lambda item: item["start"], reverse=True):
        result = result[:hit["start"]] + hit["replacement"] + result[hit["end"]:]
    return result


def archive_carrier_kind(rel_path: str, parent_slug: str, slugs) -> Optional[str]:
    """C-301/C-303/C-304: the carrier roster as a closed classifier."""
    spec_rel = ".specify/specs/%s" % parent_slug
    if rel_path.startswith(spec_rel + "/"):
        rest = rel_path[len(spec_rel) + 1:]
        if rest in ARCHIVE_LIVE_DOCUMENTS:
            return "live"
        if rest.startswith("contracts/"):
            return "live"
        if rest.startswith(ARCHIVE_DATED_SUBDIRS):
            return "dated"
        if rest == MANIFEST_NAME:
            return "merge-json"
        if rest in ("seal.md", ARCHIVE_MANIFEST_NAME):
            return "excluded"
        return "unclassified"
    for slug in slugs:
        if rel_path.startswith(".specify/specs/%s/" % slug):
            return "dated"
    if rel_path in ARCHIVE_LIVE_FILES:
        return "live"
    if rel_path == ".specify/features.md":
        return "dated"
    if rel_path.startswith(ARCHIVE_FEATURES_DETAIL_PREFIX) \
            and rel_path.endswith(".md") \
            and "/" not in rel_path[len(ARCHIVE_FEATURES_DETAIL_PREFIX):]:
        return "mixed"
    if rel_path.startswith(ARCHIVE_DATED_TREES):
        return "dated"
    if rel_path.startswith(ARCHIVE_LIVE_TREES):
        return "live"
    return None


def mixed_section_kind(lines, line_no: int) -> str:
    """C-304: only `## Related Specifications/Requirements` is live."""
    in_live = False
    for index, line in enumerate(lines, 1):
        if re.match(r"^##\s+", line):
            in_live = bool(ARCHIVE_MIXED_HEADING_RE.match(line))
        if index == line_no:
            return "live" if in_live else "dated"
    return "dated"


def mixed_dated_sections(raw: bytes) -> bytes:
    """C-304/C-306: a mixed carrier's dated H2 blocks, byte for byte."""
    blocks, current = [], []
    for line in raw.splitlines(keepends=True):
        if re.match(rb"^##\s+", line):
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    blocks.append(current)
    kept = []
    for block in blocks:
        if block and ARCHIVE_MIXED_HEADING_BYTES_RE.match(block[0]):
            continue
        kept.extend(block)
    return b"".join(kept)


def map_archived_reference(rel_path: str, slices):
    """C-210: the manifest's `from -> to` prefix map is the only resolver."""
    matches = []
    for item in slices:
        if rel_path == item["from"] or rel_path.startswith(item["from"] + "/"):
            matches.append(item)
    if not matches:
        return (None, None)
    matches.sort(key=lambda item: len(item["from"]), reverse=True)
    best = matches[0]
    if len(matches) > 1 and len(matches[1]["from"]) == len(best["from"]):
        raise _archive_invalid(
            "the archive mapping for %r is ambiguous" % rel_path)
    return (best["to"] + rel_path[len(best["from"]):],
            best.get("slug") or best["from"].rsplit("/", 1)[-1])


def amended_merge_document(document: Dict[str, Any], slices) -> Dict[str, Any]:
    """C-211: replace whole path-form string values and recompute the digest."""
    ordered_pairs = sorted(slices, key=lambda item: len(item["from"]),
                           reverse=True)
    amendments = []

    def walk(value):
        if isinstance(value, dict):
            return {key: walk(inner) for key, inner in value.items()}
        if isinstance(value, list):
            return [walk(inner) for inner in value]
        if isinstance(value, str):
            for item in ordered_pairs:
                frm, to = item["from"], item["to"]
                if value == frm or value.startswith(frm + "/"):
                    replaced = to + value[len(frm):]
                    amendments.append({"before": value, "after": replaced})
                    return replaced
        return value

    amended = walk(document)
    if not isinstance(amended, dict):
        raise _archive_invalid("the merge manifest must carry a JSON object")
    existing = document.get("digest")
    digest_before = existing if isinstance(existing, str) \
        and ARCHIVE_DIGEST_RE.match(existing) else archive_manifest_digest(document)
    amended.pop("digest", None)
    digest_after = archive_manifest_digest(amended)
    amended["digest"] = digest_after
    return {"document": amended, "amendments": amendments,
            "digest_before": digest_before, "digest_after": digest_after}


def _projected_path_exists(repo: Path, target_rel: str, slices) -> bool:
    """C-306/C-307: plan-time existence on the projected post-move tree."""
    if (repo / target_rel).exists():
        return True
    for item in slices:
        to = item["to"]
        if target_rel == to or target_rel.startswith(to + "/"):
            tail = target_rel[len(to):]
            return (repo / (item["from"] + tail)).exists()
    return False


def _hit_target(hit, parent_slug: str, tail: str) -> str:
    if hit["form"] == "F1":
        return hit["replacement"] + tail
    if hit["form"] == "F2":
        return ".specify/specs/%s/%s%s" % (parent_slug, hit["replacement"], tail)
    return ".specify/specs/" + hit["replacement"]


def _reference_tail(line: str, end: int) -> str:
    match = re.match(r"[/A-Za-z0-9_.-]*", line[end:])
    return match.group(0).rstrip(".")


# ---------------------------------------------------------------------------
# Artifact classification (C-013 / C-020)
# ---------------------------------------------------------------------------

def _artifact_row(name, action, unit, sources, per_slice,
                  basis=None, pointer=None, pointer_view=False):
    row = {"name": name, "action": action, "unit": unit,
           "sources": list(sources), "per_slice": per_slice}
    if basis:
        row["basis"] = basis
    if pointer:
        row["pointer"] = pointer
    if pointer_view:
        row["pointer_view"] = True
    return row


def _dated_record(name: str) -> bool:
    return _DATE_RE.search(name) is not None


def _classify_artifacts(repo: Path, spec_dir: Path, slices):
    rows = []
    for name in CANDIDATES:
        if name in DIRECTORY_CANDIDATES:
            parent_dir = spec_dir / name
            files = set()
            if parent_dir.is_dir():
                files.update(item.name for item in parent_dir.iterdir() if item.is_file())
            for item in slices:
                candidate_dir = item["path"] / name
                if candidate_dir.is_dir():
                    files.update(child.name for child in candidate_dir.iterdir()
                                 if child.is_file())
            if not files:
                rows.append(_artifact_row(
                    name, "not-applicable", "directory", [],
                    [{"slice": item["slug"], "present": False} for item in slices],
                    basis="no files on the parent or on any slice"))
                continue
            for fname in sorted(files):
                per_slice = [{"slice": item["slug"],
                              "present": (item["path"] / name / fname).is_file()}
                             for item in slices]
                sources = [entry["slice"] for entry in per_slice if entry["present"]]
                parent_has = (parent_dir / fname).is_file()
                unit_name = "%s/%s" % (name, fname)
                dated = name in DATED_RECORD_DIRS and _dated_record(fname)
                if dated and parent_has and sources:
                    rows.append(_artifact_row(
                        unit_name, "keep", "directory-file", sources, per_slice,
                        basis="dated record: the parent copy is kept; slice originals "
                              "are referenced, never copied",
                        pointer={"kind": "slice-original",
                                 "paths": [_rel_path(repo, item["path"] / name / fname)
                                           for item in slices
                                           if (item["path"] / name / fname).is_file()]}))
                elif dated and sources:
                    rows.append(_artifact_row(
                        unit_name, "create", "directory-file", sources, per_slice,
                        basis="dated record: the parent pointer view carries a summary "
                              "row and a pointer, never a copy",
                        pointer={"kind": "pointer-view",
                                 "paths": [_rel_path(repo, item["path"] / name / fname)
                                           for item in slices
                                           if (item["path"] / name / fname).is_file()]},
                        pointer_view=True))
                elif parent_has and sources:
                    rows.append(_artifact_row(unit_name, "merge", "directory-file",
                                              sources, per_slice))
                elif parent_has:
                    rows.append(_artifact_row(unit_name, "keep", "directory-file",
                                              sources, per_slice))
                else:
                    rows.append(_artifact_row(unit_name, "create", "directory-file",
                                              sources, per_slice))
            continue

        parent_has = (spec_dir / name).is_file()
        per_slice = [{"slice": item["slug"],
                      "present": (item["path"] / name).is_file()} for item in slices]
        sources = [entry["slice"] for entry in per_slice if entry["present"]]
        if slices and name in POINTER_VIEW_CANDIDATES:
            rows.append(_artifact_row(
                name, "merge" if parent_has else "create", "file", sources, per_slice,
                basis=("aggregated pointer view over the slice records "
                       "(summary rows + pointers)") if parent_has else
                      ("required pointer view (parent record absent; summary rows "
                       "+ pointers)"),
                pointer={"kind": "pointer-view",
                         "paths": [_rel_path(repo, item["path"] / name)
                                   for item in slices
                                   if (item["path"] / name).is_file()]},
                pointer_view=True))
        elif parent_has and sources:
            rows.append(_artifact_row(name, "merge", "file", sources, per_slice))
        elif parent_has:
            rows.append(_artifact_row(name, "keep", "file", sources, per_slice))
        elif sources:
            rows.append(_artifact_row(name, "create", "file", sources, per_slice))
        else:
            basis = "absent on the parent and on every slice"
            if name == "tasks.md":
                basis = ("required floor: absent on the parent and on every slice; "
                         "the candidate is still disposed, never skipped")
            rows.append(_artifact_row(name, "not-applicable", "file",
                                      sources, per_slice, basis=basis))
    return rows


# ---------------------------------------------------------------------------
# ID-family maps (C-014 / C-015 / C-016) and conflicts
# ---------------------------------------------------------------------------

def _conflict(code, artifact, unit, side_a, side_b, candidates):
    return {
        "code": code,
        "artifact": artifact,
        "unit": unit,
        "side_a": side_a,
        "side_b": side_b,
        "candidates": list(candidates),
        "status": "open",
    }


def _side(path: str, line: int, excerpt: str) -> Dict[str, Any]:
    return {"path": path, "line": line, "excerpt": excerpt}


def _parent_registry_context(spec_dir: Path, with_slices: bool):
    requirements = _read_text(spec_dir / "requirements.md")
    tasks_path = spec_dir / "tasks.md"
    contracts = {}
    contracts_dir = spec_dir / "contracts"
    if contracts_dir.is_dir():
        for contract in sorted(contracts_dir.glob("*.md")):
            contracts[contract.name] = _contract_clauses(contract)
    return {
        "requirements": requirements,
        "definitions": _definition_lines(requirements),
        "strings": _parse_shared_strings(requirements),
        "tasks": _task_rows(_read_text(tasks_path),
                            state=("X" if with_slices else None))
        if tasks_path.is_file() else [],
        "all_tasks": {entry["id"]: entry for entry in (
            _task_rows(_read_text(tasks_path)) if tasks_path.is_file() else [])},
        "contracts": contracts,
        "entities": _entity_rows(spec_dir / "data-model.md"),
    }


def _family_entries(slice_item, family):
    """Ordered (id, line, text, file_rel) family entries inside one slice."""
    entries = []
    if family in ("FR", "SC"):
        for entry in _definition_lines(slice_item["text"]):
            if entry["id"].startswith(family + "-"):
                entries.append((entry["id"], entry["line"], entry["text"], "requirements.md"))
    elif family == "STR":
        for string_id, record in _parse_shared_strings(slice_item["text"]).items():
            entries.append((string_id, record["line"], record["literal"], "requirements.md"))
    elif family == "T":
        tasks_path = slice_item["path"] / "tasks.md"
        if tasks_path.is_file():
            for entry in _task_rows(_read_text(tasks_path)):
                entries.append((entry["id"], entry["line"], entry["text"], "tasks.md"))
    elif family == "C":
        contracts_dir = slice_item["path"] / "contracts"
        if contracts_dir.is_dir():
            for contract in sorted(contracts_dir.glob("*.md")):
                for entry in _contract_clauses(contract):
                    entries.append((entry["id"], entry["line"], entry["text"],
                                    contract.name))
    elif family == "E":
        model = slice_item["path"] / "data-model.md"
        for entry in _entity_rows(model):
            entries.append((entry["id"], entry["line"], entry["text"], "data-model.md"))
    return entries


def _parent_has(family, parent_id, file_rel, parent_sequences) -> bool:
    if family == "C":
        return any(parent_id in ids for ids in parent_sequences["C"].values())
    return parent_id in parent_sequences[family]


def _text_differs(family, text, parent_id, file_rel, context) -> bool:
    if family == "STR":
        parent = context["strings"].get(parent_id)
        return parent is not None and parent["literal"] != text
    if family in ("FR", "SC"):
        parent = next((entry for entry in context["definitions"]
                       if entry["id"] == parent_id), None)
        return parent is not None and parent["text"] != text
    if family == "T":
        parent = context["all_tasks"].get(parent_id)
        return parent is not None and parent["text"] != text
    if family == "C":
        parent = next((entry for entry in context["contracts"].get(file_rel, [])
                       if entry["id"] == parent_id), None)
        return parent is not None and parent["text"] != text
    if family == "E":
        parent = next((entry for entry in context["entities"]
                       if entry["id"] == parent_id), None)
        return parent is not None and parent["text"] != text
    return False


def _conflict_artifact(family: str, file_rel: str) -> str:
    if family in ("FR", "SC", "STR"):
        return "requirements.md"
    if family == "T":
        return "tasks.md"
    if family == "C":
        return "contracts/" + file_rel
    return "data-model.md"


def _build_id_maps(repo: Path, spec_dir: Path, slices):
    context = _parent_registry_context(spec_dir, with_slices=bool(slices))
    strings = context["strings"]
    parent_sequences = {
        "FR": [entry["id"] for entry in context["definitions"]
               if entry["id"].startswith("FR-")],
        "SC": [entry["id"] for entry in context["definitions"]
               if entry["id"].startswith("SC-")],
        "STR": list(strings),
        "T": [entry["id"] for entry in context["tasks"]],
        "C": {name: [entry["id"] for entry in entries]
              for name, entries in context["contracts"].items()},
        "E": [entry["id"] for entry in context["entities"]],
    }
    taken = {family: set(parent_sequences[family]) for family in ("FR", "SC", "STR", "T", "E")}
    for name, ids in parent_sequences["C"].items():
        taken[("C", name)] = set(ids)
    counters = {}
    for family in ("FR", "SC", "STR", "T", "E"):
        numbers = [_id_number(family, item) for item in parent_sequences[family]]
        counters[family] = (max(numbers) + 1) if numbers else 1
    for name, ids in parent_sequences["C"].items():
        numbers = [_id_number("C", item) for item in ids]
        counters[("C", name)] = (max(numbers) + 1) if numbers else 1
    claimed: Dict[str, Dict[str, Any]] = {family: {} for family in FAMILIES}

    def _allocate(family: str, file_key: Optional[str] = None) -> str:
        key = (family, file_key) if family == "C" else family
        if key not in counters:
            counters[key] = 1
            taken[key] = set()
        while True:
            number = counters[key]
            counters[key] = number + 1
            candidate = _format_id(family, number)
            if candidate not in taken[key]:
                taken[key].add(candidate)
                return candidate

    id_maps: Dict[str, list] = {family: [] for family in FAMILIES}
    conflicts = []
    parent_requirements = _rel_path(repo, spec_dir / "requirements.md")

    for family in FAMILIES:
        for slice_item in slices:
            slug = slice_item["slug"]
            slice_requirements = _rel_path(repo, slice_item["requirements"])
            mapping = {row["slice_id"]: row for row in
                       _parse_parent_mapping(slice_item["text"])["mappings"]}
            for slice_id, line, text, file_rel in _family_entries(slice_item, family):
                artifact = _conflict_artifact(family, file_rel)
                target = mapping.get(slice_id)
                if target is not None:
                    parent_id = target["parent_id"]
                    if not _parent_has(family, parent_id, file_rel, parent_sequences):
                        conflicts.append(_conflict(
                            "mapping-target-missing", artifact,
                            "%s -> %s" % (slice_id, parent_id),
                            _side(slice_requirements, target["line"],
                                  "declared mapping %s -> %s" % (slice_id, parent_id)),
                            _side(parent_requirements, 0,
                                  "the parent sequence carries no %s" % parent_id),
                            ["fix the declared mapping to an existing parent id",
                             "or record a user-waiver after review"]))
                        continue
                    if parent_id in claimed[family]:
                        same_shared_string = (
                            family == "STR"
                            and parent_id in strings
                            and strings[parent_id]["literal"] == text)
                        if not same_shared_string:
                            prior = claimed[family][parent_id]
                            conflicts.append(_conflict(
                                "duplicate-mapping", artifact, parent_id,
                                _side(slice_requirements, target["line"],
                                      "declared mapping %s -> %s"
                                      % (slice_id, parent_id)),
                                _side(prior["path"], prior["line"],
                                      "the target is already claimed by %s %s"
                                      % (prior["slice"], prior["slice_id"])),
                                ["declare a multi-to-one merge explicitly",
                                 "or record a user-waiver after review"]))
                            continue
                    claimed[family][parent_id] = {"slice": slug, "slice_id": slice_id,
                                                  "path": slice_requirements,
                                                  "line": target["line"]}
                    kind = ("localization"
                            if _text_differs(family, text, parent_id, file_rel, context)
                            else "mapped")
                    entry = {"slice": slug, "slice_id": slice_id,
                             "parent_id": parent_id, "kind": kind}
                    if family == "C":
                        entry["file"] = "contracts/" + file_rel
                    id_maps[family].append(entry)
                    continue

                if family == "STR":
                    existing = strings.get(slice_id)
                    if existing is not None:
                        if existing["literal"] == text:
                            id_maps["STR"].append({"slice": slug, "slice_id": slice_id,
                                                   "parent_id": slice_id, "kind": "mapped"})
                        else:
                            conflicts.append(_conflict(
                                "str-same-number-different-meaning", artifact, slice_id,
                                _side(slice_requirements, line,
                                      '%s = "%s"' % (slice_id, text)),
                                _side(parent_requirements, existing["line"],
                                      '%s = "%s"' % (slice_id, existing["literal"])),
                                ["declare the mapping in `## Parent Mapping` "
                                 "(canonical-map)",
                                 "or record a user-waiver after review — never silently "
                                 "renumber"]))
                    else:
                        new_id = _allocate("STR")
                        id_maps["STR"].append({"slice": slug, "slice_id": slice_id,
                                               "parent_id": new_id, "kind": "appended"})
                elif family in ("FR", "SC"):
                    if slice_id in parent_sequences[family]:
                        parent_entry = next(entry for entry in context["definitions"]
                                            if entry["id"] == slice_id)
                        conflicts.append(_conflict(
                            "no-mapping", artifact, slice_id,
                            _side(slice_requirements, line, text),
                            _side(parent_requirements, parent_entry["line"],
                                  parent_entry["text"]),
                            ["declare the slice id's parent target in `## Parent Mapping`",
                             "or record a user-waiver after review"]))
                    else:
                        new_id = _allocate(family)
                        id_maps[family].append({"slice": slug, "slice_id": slice_id,
                                                "parent_id": new_id, "kind": "appended"})
                else:
                    file_key = file_rel if family == "C" else None
                    new_id = _allocate(family, file_key)
                    entry = {"slice": slug, "slice_id": slice_id,
                             "parent_id": new_id, "kind": "appended"}
                    if family == "C":
                        entry["file"] = "contracts/" + file_rel
                    id_maps[family].append(entry)
    return id_maps, conflicts, context


# ---------------------------------------------------------------------------
# Token→registry binding for factory docs (C-017)
# ---------------------------------------------------------------------------

def _factory_doc_refs(repo: Path, slices, parent_strings, id_maps):
    refs, conflicts = [], []
    registries = [(item["slug"], item["requirements"],
                   _parse_shared_strings(item["text"])) for item in slices]
    for root in FACTORY_DOC_ROOTS:
        base = repo / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md"), key=lambda item: str(item)):
            if not path.is_file():
                continue
            for line_no, line in enumerate(_read_text(path).splitlines(), 1):
                for match in _STR_REF_RE.finditer(line):
                    token = match.group(1)
                    hits = [(slug, requirements, registry[token])
                            for slug, requirements, registry in registries
                            if token in registry]
                    if not hits:
                        # no slice registry carries this token: it is not a
                        # slice-local id and its meaning cannot change here
                        continue
                    if len(hits) > 1 and len({hit[2]["literal"] for hit in hits}) > 1:
                        conflicts.append(_conflict(
                            "factory-doc-ref-ambiguous", _rel_path(repo, path), token,
                            _side(_rel_path(repo, hits[0][1]), hits[0][2]["line"],
                                  '%s = "%s" in %s' % (token, hits[0][2]["literal"],
                                                       hits[0][0])),
                            _side(_rel_path(repo, hits[1][1]), hits[1][2]["line"],
                                  '%s = "%s" in %s' % (token, hits[0 + 1][2]["literal"],
                                                       hits[1][0])),
                            ["declare the registry (spec path + section anchor) in the "
                             "factory doc",
                             "repoint the reference to one merged parent id",
                             "or record a user-waiver after review"]))
                        continue
                    slug, slice_requirements, hit = hits[0]
                    literal = hit["literal"]
                    parent_record = parent_strings.get(token)
                    if parent_record is not None and parent_record["literal"] == literal:
                        continue  # resolves identically after the merge
                    merged = next((entry for entry in id_maps["STR"]
                                   if entry["slice"] == slug and entry["slice_id"] == token),
                                  None)
                    parent_id = merged["parent_id"] if merged else None
                    status = "resolved" if parent_id else "open"
                    refs.append({
                        "path": _rel_path(repo, path),
                        "line": line_no,
                        "token": token,
                        "slice": slug,
                        "slice_id": token,
                        "slice_literal": literal,
                        "parent_id": parent_id,
                        "parent_literal": (parent_record["literal"]
                                           if parent_record is not None else None),
                        "resolution": {"kind": "repoint", "target": parent_id},
                        "status": status,
                    })
                    if status == "open":
                        conflicts.append(_conflict(
                            "factory-doc-ref-unresolved", _rel_path(repo, path), token,
                            _side(_rel_path(repo, path), line_no,
                                  "the reference resolves only through %s" % slug),
                            _side(_rel_path(repo, slice_requirements), 0,
                                  "no merged parent id is derivable for %s" % token),
                            ["declare the registry or repoint the reference",
                             "or record a user-waiver after review"]))
    return refs, conflicts


def _finalize_conflicts(conflicts):
    ordered = sorted(
        conflicts,
        key=lambda item: (item["artifact"], item["code"], item["unit"],
                          item["side_a"].get("path", ""),
                          item["side_a"].get("line", 0),
                          item["side_b"].get("path", ""),
                          item["side_b"].get("line", 0)))
    for index, item in enumerate(ordered, 1):
        item["id"] = "CF-%03d" % index
    return ordered


def _excluded_conflicts(repo: Path, excluded):
    conflicts = []
    for item in excluded:
        requirements = _rel_path(repo, item["requirements"])
        if item["missing"] == "parent-declaration":
            satisfied = ("name-family satisfied: the directory name matches "
                         "`<parent-number><letters>-<slug>`")
            unmet = ("parent-declaration unmet: no `## Parent Mapping` section and "
                     "no `**Parent spec**:` field names the parent")
            candidates = [
                "add a `## Parent Mapping` section or a `**Parent spec**:` field "
                "naming the parent",
                "or rename the directory out of the slice name family",
            ]
        else:
            satisfied = "parent-declaration satisfied: the file names the parent"
            unmet = ("name-family unmet: the directory name does not match "
                     "`<parent-number><letters>-<slug>`")
            candidates = [
                "rename the directory to `<parent-number><letters>-<slug>` inside "
                "`.specify/specs/`",
                "or remove the parent declaration if the directory is not a slice",
            ]
        conflicts.append(_conflict(
            SLICE_CODE, "slices", item["slug"],
            _side(requirements, 0, satisfied),
            _side(requirements, 0, unmet),
            candidates))
    return conflicts


def _section_rewrite_conflicts(repo: Path, spec_dir: Path, slices):
    conflicts = []
    for item in slices:
        parsed = _parse_parent_mapping(item["text"])
        for section in parsed["sections"]:
            parent_file = spec_dir / section["artifact"]
            if not parent_file.is_file():
                continue  # a slice-unique section lands in the merged appendix
            heading_line = 0
            heading_text = ""
            for line_no, line in enumerate(_read_text(parent_file).splitlines(), 1):
                if re.match(r"^##\s+" + re.escape(section["heading"]) + r"\s*$", line):
                    heading_line = line_no
                    heading_text = _normalize(line)
                    break
            if not heading_line:
                continue
            conflicts.append(_conflict(
                "same-anchor-dual-edit", section["artifact"],
                "\u00a7 %s" % section["heading"],
                _side(_rel_path(repo, item["requirements"]), section["line"],
                      "the slice declares a rewrite of `%s`" % section["heading"]),
                _side(_rel_path(repo, parent_file), heading_line,
                      "the parent owns the same anchor: %s" % heading_text),
                ["record a user-waiver after review",
                 "recheck-clean (drop the rewrite declaration or the parent edit)"]))
    return conflicts


def _build_plan(repo: Path, spec_dir: Path) -> Dict[str, Any]:
    slices, excluded = _discover_slices(spec_dir, repo)
    ordered_slices = _derive_order(repo, spec_dir.name, slices)
    artifacts = _classify_artifacts(repo, spec_dir, ordered_slices)
    id_maps, map_conflicts, context = _build_id_maps(repo, spec_dir, ordered_slices)
    factory_refs, factory_conflicts = _factory_doc_refs(
        repo, ordered_slices, context["strings"], id_maps)
    conflicts = []
    conflicts.extend(map_conflicts)
    conflicts.extend(factory_conflicts)
    conflicts.extend(_excluded_conflicts(repo, excluded))
    conflicts.extend(_section_rewrite_conflicts(repo, spec_dir, ordered_slices))
    conflicts = _finalize_conflicts(conflicts)

    def _carrier(item) -> Optional[str]:
        tasks_path = item["path"] / "tasks.md"
        return _rel_path(repo, tasks_path) if tasks_path.is_file() else None

    plan = {
        "schema_version": 1,
        "spec": spec_dir.name,
        "slices": [{
            "slug": item["slug"],
            "order": item["order"],
            "order_basis": item["order_basis"],
            "order_source": item["order_source"],
            "carrier_tasks": _carrier(item),
            "retention": "pending-review",
        } for item in ordered_slices],
        "artifacts": artifacts,
        "id_maps": id_maps,
        "factory_doc_refs": factory_refs,
        "conflicts": conflicts,
        "checks": {
            "candidate_count": len(CANDIDATES),
            "slice_count": len(ordered_slices),
            "slice_conditions": ["name-family", "parent-declaration"],
            "excluded_candidates": len(excluded),
            "artifact_rows": len(artifacts),
            "id_map_entries": sum(len(entries) for entries in id_maps.values()),
            "factory_doc_refs": len(factory_refs),
            "open_conflicts": len([c for c in conflicts if c["status"] == "open"]),
        },
    }
    return plan


def action_merge_plan(args: argparse.Namespace, spec_dir: Path) -> Tuple[Dict[str, Any], int]:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    try:
        plan = _build_plan(repo, spec_dir)
    except ArchiveManifestError as exc:
        return _archive_manifest_error("merge-plan", spec_dir, exc), EXIT_INPUT_ERROR
    except (OSError, ValueError, StopIteration) as exc:
        return _payload(
            "merge-plan", spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "merge-plan-error",
                "the merge plan cannot be derived from this tree: %s" % exc,
                "repair the named input (spec tree, split record or registries)",
                "rerun the same command after the input is repaired",
            )],
        ), EXIT_INPUT_ERROR
    open_conflicts = [c for c in plan["conflicts"] if c["status"] == "open"]
    conditions = [
        _condition(
            item["code"],
            "%s %s: %s <<>> %s" % (
                item["artifact"], item["unit"],
                item["side_a"].get("excerpt", ""), item["side_b"].get("excerpt", "")),
            "; ".join(item["candidates"]),
            "resolve the named records, then rerun merge-plan",
        ) for item in open_conflicts
    ]
    verdict = "refused" if open_conflicts else "ok"
    code = EXIT_REFUSED if open_conflicts else EXIT_OK
    payload = _payload("merge-plan", spec_dir, verdict, code, conditions)
    payload["plan"] = plan
    return payload, code


# ---------------------------------------------------------------------------
# Merge-apply surface (C-013 … C-023): deterministic writes into the parent
# ---------------------------------------------------------------------------

MANIFEST_NAME = "merge-manifest.json"
SUPERSEDE_HEADING = "## Superseded pre-split record"
MERGE_APPENDIX_HEADING = "## Merged from slices"
POINTER_BEGIN = "<!-- begin: merge-apply aggregated pointer view (generated) -->"
POINTER_END = "<!-- end: merge-apply aggregated pointer view -->"
SLICE_STATUS_RE = re.compile(r"^(SC-\d{3}|FR-\d{3})_status=(.*)$")
_ID_TOKEN_RE = re.compile(r"\b(?:STR-\d{3}|FR-\d{3}|SC-\d{3}|C-\d{1,3}|T\d{3}|E\d+)\b")
_MERGED_INTO_RE = re.compile(r"^\*\*Merged into\*\*:\s*(.+?)\s*$")
_TASK_ANY_RE = re.compile(r"^-\s+\[(.)\]\s+T\d{3}\b")


def _ensure_newline(text: str) -> str:
    stripped = text.rstrip("\n")
    return stripped + "\n" if stripped else ""


def _slice_rewrite_map(id_maps: Dict[str, list], slug: str,
                       contract_file: Optional[str] = None) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for family in ("FR", "SC", "STR", "T", "E"):
        for entry in id_maps.get(family, []):
            if entry["slice"] == slug:
                mapping[entry["slice_id"]] = entry["parent_id"]
    for entry in id_maps.get("C", []):
        if entry["slice"] == slug and (contract_file is None
                                       or entry.get("file") == contract_file):
            mapping[entry["slice_id"]] = entry["parent_id"]
    return mapping


#: `(父 C-47–C-54)` style annotations name ids of the *parent's* own clauses. They
#: are not slice-local references, so a slice-local rewrite mapping must leave them
#: alone; rewriting would repoint them at an unrelated merged id.
_PARENT_ANNOTATION_RE = re.compile(r"[（(]父 [^）)]*[）)]")


def _rewrite_ids(text: str, mapping: Dict[str, str]) -> str:
    if not mapping:
        return text
    protected = [(match.start(), match.end())
                 for match in _PARENT_ANNOTATION_RE.finditer(text)]

    def _replace(match):
        if any(start <= match.start() and match.end() <= end
               for start, end in protected):
            return match.group(0)
        return mapping.get(match.group(0), match.group(0))

    return _ID_TOKEN_RE.sub(_replace, text)


def _raw_definition_line(text: str, slice_id: str) -> Optional[str]:
    for line in text.splitlines():
        match = re.match(r"^-\s+\*\*(FR|SC)-(\d{3})\*\*", line)
        if match and "%s-%s" % (match.group(1), match.group(2)) == slice_id:
            return line
    return None


def _h2_sections(text: str):
    sections = []
    current = None
    for line in text.splitlines():
        if re.match(r"^##\s+", line):
            current = [re.sub(r"^##\s+", "", line).strip(), []]
            sections.append(current)
        elif current is not None:
            current[1].append(line)
    return [(heading, body) for heading, body in sections]


def _demote_heading(line: str) -> str:
    return "#" + line if re.match(r"^#{1,6}\s", line) else line


def _summary_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped[:1] in ("-", "*"):
            stripped = stripped.lstrip("-*").strip()
        return stripped
    return "(no summary line)"


def _write_if_changed(path: Path, content: str, written: list, repo: Path) -> bool:
    data = content.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    written.append(_rel_path(repo, path))
    return True


def _engine_version() -> str:
    try:
        return _sig_version_text(ENGINE_NAME).rsplit(" ", 1)[-1]
    except (OSError, ValueError):
        return "unknown"


def _dated_files(ordered) -> list:
    paths = []
    for item in ordered:
        base = item["path"]
        for name in ("review.md", "code-review.md", "verification.md"):
            if (base / name).is_file():
                paths.append(base / name)
        for dirname in DATED_RECORD_DIRS:
            if (base / dirname).is_dir():
                paths.extend(sorted(p for p in (base / dirname).rglob("*") if p.is_file()))
    return sorted(set(paths), key=lambda item: str(item))


def _dated_snapshot(ordered) -> Dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in _dated_files(ordered)}


def _open_task_rows(text: str) -> list:
    rows = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = _TASK_ROW_RE.match(line)
        if match and match.group(1) in (" ", ">"):
            rows.append({"line": line_no, "text": line, "id": match.group(2)})
    return rows


def _deferred_recorded(item, task_id: str) -> bool:
    verification = item["path"] / "verification.md"
    if not verification.is_file():
        return False
    return any("deferred_tasks=" in line and task_id in line
               for line in _read_text(verification).splitlines())


def _unclosed_slice_rows(repo: Path, ordered) -> list:
    findings = []
    for item in ordered:
        tasks_path = item["path"] / "tasks.md"
        if not tasks_path.is_file():
            continue
        for line_no, line in enumerate(_read_text(tasks_path).splitlines(), 1):
            match = _TASK_ROW_RE.match(line)
            if not match:
                continue
            state = match.group(1)
            if state in (" ", ">"):
                findings.append((_rel_path(repo, tasks_path), line_no, match.group(2), state))
            elif state == "~" and not _deferred_recorded(item, match.group(2)):
                findings.append((_rel_path(repo, tasks_path), line_no, match.group(2), state))
    return findings


# --- per-artifact content builders -----------------------------------------

def _prose_content(repo, spec_dir, name, action, ordered, id_maps):
    parent_path = spec_dir / name
    parent_text = _read_text(parent_path) if parent_path.is_file() else ""
    contributors = [item for item in ordered if (item["path"] / name).is_file()]
    blocks = []
    for item in contributors:
        mapping = _slice_rewrite_map(id_maps, item["slug"])
        body = _rewrite_ids(_read_text(item["path"] / name), mapping).rstrip("\n")
        blocks.append("<!-- merged from %s (source: %s) -->\n\n%s" % (
            item["slug"], _rel_path(repo, item["path"] / name), body))
    if action == "create" or not parent_text:
        if not blocks:
            return None
        return _ensure_newline("\n\n".join(blocks))
    parent_headings = {heading for heading, _ in _h2_sections(parent_text)}
    appendix = []
    for item in contributors:
        mapping = _slice_rewrite_map(id_maps, item["slug"])
        slice_text = _rewrite_ids(_read_text(item["path"] / name), mapping)
        unique = [(heading, body) for heading, body in _h2_sections(slice_text)
                  if heading not in parent_headings]
        if not unique:
            continue
        block = ["<!-- source: %s -->" % item["slug"], ""]
        for heading, body in unique:
            block.append(_demote_heading("## " + heading))
            block.append("")
            lines = list(body)
            while lines and not lines[-1].strip():
                lines.pop()
            block.extend(_demote_heading(line) for line in lines)
            block.append("")
        appendix.append("\n".join(block).rstrip("\n"))
    if not appendix:
        return None
    return _ensure_newline(parent_text) + "\n" + MERGE_APPENDIX_HEADING + "\n\n" \
        + "\n\n".join(appendix) + "\n"


def _requirements_content(repo, spec_dir, action, ordered, id_maps):
    parent_path = spec_dir / "requirements.md"
    if not parent_path.is_file():
        return _prose_content(repo, spec_dir, "requirements.md", action, ordered, id_maps)
    parent_text = _read_text(parent_path)
    lines = parent_text.splitlines()
    anchors: Dict[int, list] = {}
    for family in ("FR", "SC"):
        appended_lines = []
        for entry in id_maps.get(family, []):
            if entry["kind"] != "appended":
                continue
            item = next(i for i in ordered if i["slug"] == entry["slice"])
            raw = _raw_definition_line(item["text"], entry["slice_id"])
            if raw is None:
                continue
            appended_lines.append(_rewrite_ids(
                raw, _slice_rewrite_map(id_maps, entry["slice"])))
        if not appended_lines:
            continue
        anchor = max((index for index, line in enumerate(lines)
                      if re.match(r"^-\s+\*\*%s-\d{3}\*\*" % family, line)),
                     default=len(lines))
        anchors.setdefault(anchor, []).extend(appended_lines)
    string_rows = []
    for entry in id_maps.get("STR", []):
        if entry["kind"] != "appended":
            continue
        item = next(i for i in ordered if i["slug"] == entry["slice"])
        record = _parse_shared_strings(item["text"]).get(entry["slice_id"])
        if record is None:
            continue
        string_rows.append("| `%s` | `\"%s\"` | appended from %s by merge |" % (
            entry["parent_id"], record["literal"], entry["slice"]))
    if string_rows:
        body, start = _section(parent_text, r"Shared Strings")
        if body is not None:
            offsets = [offset for offset, line in enumerate(body) if line.startswith("|")]
            if offsets:
                anchor = start + 1 + max(offsets)
            else:
                anchor = start + len(body)
            anchors.setdefault(anchor, []).extend(string_rows)
        else:
            anchors.setdefault(len(lines), []).extend(
                ["", "## Shared Strings", "",
                 "| String ID | Value (verbatim) | Consumed by |",
                 "|-----------|------------------|-------------|"] + string_rows)
    if not anchors:
        return None
    out = []
    for index, line in enumerate(lines):
        out.append(line)
        out.extend(anchors.get(index, []))
    out.extend(anchors.get(len(lines), []))
    return _ensure_newline("\n".join(out))


def _tasks_content(repo, spec_dir, action, ordered, id_maps, carriers):
    parent_path = spec_dir / "tasks.md"
    parent_text = _read_text(parent_path) if parent_path.is_file() else ""
    kept = []
    for line in parent_text.splitlines():
        match = _TASK_ROW_RE.match(line)
        if match and match.group(1) in (" ", ">"):
            continue
        kept.append(line)
    appended = []
    for item in ordered:
        tasks_path = item["path"] / "tasks.md"
        if not tasks_path.is_file():
            continue
        mapping = _slice_rewrite_map(id_maps, item["slug"])
        block = []
        for line in _read_text(tasks_path).splitlines():
            if SLICE_PHASE_RE.match(line):
                block.append(line)
            elif _TASK_ROW_RE.match(line):
                if not block:
                    # a slice that opens with a row before any phase heading still
                    # gets a heading, so the row is never parentless in the parent
                    block.append("## Phase: merged slice tasks (`%s`)" % item["slug"])
                block.append(_rewrite_ids(line, mapping))
        if block:
            merged_block = ["", "<!-- source: %s -->" % item["slug"]]
            merged_block.extend(block)
            appended.append(merged_block)
    anchor_rows = [index for index, line in enumerate(kept) if _TASK_ROW_RE.match(line)]
    insert_at = anchor_rows[-1] + 1 if anchor_rows else len(kept)
    inserted = [line for block in appended for line in block]
    out = kept[:insert_at] + inserted + kept[insert_at:]
    superseded = _open_task_rows(parent_text)
    if superseded:
        carrier_note = ", ".join(carriers) if carriers else "-"
        block = ["", SUPERSEDE_HEADING, ""]
        for row in superseded:
            block.append("> " + row["text"])
            block.append(">")
            block.append("> superseded: tasks.md:%d (original position); superseded_by: "
                         "%s line 0 (whole-file fact); carriers: %s" % (
                             row["line"], MANIFEST_NAME, carrier_note))
            block.append("")
        out.extend(block)
    if not appended and not superseded and action == "keep":
        return None
    return _ensure_newline("\n".join(out))


def _contract_content(repo, spec_dir, fname, action, ordered, id_maps):
    unit = "contracts/" + fname
    parent_path = spec_dir / "contracts" / fname
    contributors = [item for item in ordered
                    if (item["path"] / "contracts" / fname).is_file()]
    if action == "create" or not parent_path.is_file():
        blocks = []
        for item in contributors:
            mapping = _slice_rewrite_map(id_maps, item["slug"], contract_file=unit)
            body = _rewrite_ids(
                _read_text(item["path"] / "contracts" / fname), mapping).rstrip("\n")
            blocks.append("<!-- merged from %s (source: %s) -->\n\n%s" % (
                item["slug"], _rel_path(repo, item["path"] / "contracts" / fname), body))
        return _ensure_newline("\n\n".join(blocks)) if blocks else None
    parent_text = _read_text(parent_path)
    appended = []
    for item in contributors:
        mapping = _slice_rewrite_map(id_maps, item["slug"], contract_file=unit)
        for entry in id_maps.get("C", []):
            if entry["slice"] != item["slug"] or entry.get("file") != unit:
                continue
            if entry["kind"] != "appended":
                continue
            raw = next((line for line in
                        _read_text(item["path"] / "contracts" / fname).splitlines()
                        if re.match(r"^\*\*%s\*\*" % re.escape(entry["slice_id"]), line)),
                       None)
            if raw is not None:
                appended.append(_rewrite_ids(raw, mapping))
    if not appended:
        return None
    return _ensure_newline(parent_text) + "\n" + "\n".join(appended) + "\n"


def _data_model_content(repo, spec_dir, action, ordered, id_maps):
    parent_path = spec_dir / "data-model.md"
    if action == "create" or not parent_path.is_file():
        return _prose_content(repo, spec_dir, "data-model.md", action, ordered, id_maps)
    parent_text = _read_text(parent_path)
    lines = parent_text.splitlines()
    appended = []
    for entry in id_maps.get("E", []):
        if entry["kind"] != "appended":
            continue
        item = next(i for i in ordered if i["slug"] == entry["slice"])
        mapping = _slice_rewrite_map(id_maps, entry["slice"])
        for line in _read_text(item["path"] / "data-model.md").splitlines():
            match = re.match(r"^\|\s*(E\d+)\s*\|", line)
            if match and match.group(1) == entry["slice_id"]:
                appended.append(_rewrite_ids(line, mapping))
    if not appended:
        return None
    rows = [index for index, line in enumerate(lines) if re.match(r"^\|\s*E\d+\s*\|", line)]
    insert_at = rows[-1] + 1 if rows else len(lines)
    out = lines[:insert_at] + appended + lines[insert_at:]
    return _ensure_newline("\n".join(out))


def _dated_pointer_view(repo, row):
    blocks = []
    for rel in row.get("pointer", {}).get("paths", []):
        path = repo / rel
        if not path.is_file():
            continue
        summary = next((line.strip() for line in _read_text(path).splitlines()
                        if line.strip()), "(empty record)")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        blocks.append("summary: %s\npointer: %s\nsha256: %s" % (summary, rel, digest))
    return _ensure_newline("\n\n".join(blocks)) if blocks else None


def _directory_file_content(repo, spec_dir, dirname, fname, action, row,
                            ordered, id_maps):
    if row.get("pointer_view"):
        return _dated_pointer_view(repo, row)
    parent_path = spec_dir / dirname / fname
    contributors = [item for item in ordered
                    if (item["path"] / dirname / fname).is_file()]
    blocks = []
    for item in contributors:
        mapping = _slice_rewrite_map(id_maps, item["slug"])
        body = _rewrite_ids(
            _read_text(item["path"] / dirname / fname), mapping).rstrip("\n")
        blocks.append("<!-- merged from %s (source: %s) -->\n\n%s" % (
            item["slug"], _rel_path(repo, item["path"] / dirname / fname), body))
    if action == "create" or not parent_path.is_file():
        return _ensure_newline("\n\n".join(blocks)) if blocks else None
    if not blocks:
        return None
    return _ensure_newline(_read_text(parent_path).rstrip("\n") + "\n\n"
                           + "\n\n".join(blocks))


def _pointer_view_block(repo, name, ordered, id_maps):
    if name == "verification.md":
        lines = []
        for item in ordered:
            path = item["path"] / "verification.md"
            if not path.is_file():
                continue
            mapping = _slice_rewrite_map(id_maps, item["slug"])
            for line in _read_text(path).splitlines():
                match = SLICE_STATUS_RE.match(re.sub(r"^[-*]\s+", "", line.strip()))
                if not match:
                    continue
                parent_id = mapping.get(match.group(1), match.group(1))
                lines.append("%s_status=%s" % (parent_id, match.group(2).strip()))
                lines.append("%s_note=%s (%s local row %s)" % (
                    parent_id, _rel_path(repo, path), item["slug"], match.group(1)))
        return lines or ["(no slice verification records in this merge)"]
    lines = []
    for item in ordered:
        path = item["path"] / name
        if not path.is_file():
            continue
        lines.append("- %s: %s — %s" % (
            item["slug"], _rel_path(repo, path), _summary_line(_read_text(path))))
    return lines or ["- (no slice %s records in this merge)" % name]


def _pointer_view_content(repo, spec_dir, name, action, ordered, id_maps):
    block = _pointer_view_block(repo, name, ordered, id_maps)
    parent_path = spec_dir / name
    parent_text = _read_text(parent_path) if parent_path.is_file() else ""
    if action == "create" or not parent_text:
        title = {"verification.md": "# Verification — aggregated pointer view",
                 "review.md": "# Review — aggregated pointer view",
                 "code-review.md": "# Code review — aggregated pointer view"}[name]
        return _ensure_newline("%s (%s)\n\n%s\n" % (
            title, spec_dir.name, "\n".join(block)))
    generated = POINTER_BEGIN + "\n" + "\n".join(block) + "\n" + POINTER_END
    if POINTER_BEGIN in parent_text and POINTER_END in parent_text:
        prefix, _, rest = parent_text.partition(POINTER_BEGIN)
        _, _, suffix = rest.partition(POINTER_END)
        return _ensure_newline(prefix + generated + suffix)
    return _ensure_newline(parent_text) + "\n" + generated + "\n"


def _artifact_content(repo, spec_dir, row, ordered, id_maps, carriers):
    name, action = row["name"], row["action"]
    if "/" in name:
        dirname, fname = name.split("/", 1)
        if dirname == "contracts":
            return _contract_content(repo, spec_dir, fname, action, ordered, id_maps)
        return _directory_file_content(repo, spec_dir, dirname, fname, action, row,
                                       ordered, id_maps)
    if name == "requirements.md":
        return _requirements_content(repo, spec_dir, action, ordered, id_maps)
    if name == "tasks.md":
        return _tasks_content(repo, spec_dir, action, ordered, id_maps, carriers)
    if name in POINTER_VIEW_CANDIDATES:
        return _pointer_view_content(repo, spec_dir, name, action, ordered, id_maps)
    if name == "data-model.md":
        return _data_model_content(repo, spec_dir, action, ordered, id_maps)
    if name in ("plan.md", "research.md", "quickstart.md", "feature-ref.md"):
        return _prose_content(repo, spec_dir, name, action, ordered, id_maps)
    return None


# --- the merge state, the slice marker and factory-doc rewrites -------------

def _slice_marker_content(spec_dir: Path, item) -> Optional[str]:
    path = item["path"] / "requirements.md"
    text = _read_text(path)
    if any(line.startswith("**Merged into**:") for line in text.splitlines()):
        return None
    marker = "**Merged into**: .specify/specs/%s（%s）" % (spec_dir.name, MANIFEST_NAME)
    lines = text.split("\n")
    status = next((index for index, line in enumerate(lines)
                   if line.startswith("**Status**:")), None)
    if status is not None:
        insert_at = status + 1
    else:
        insert_at = next((index for index, line in enumerate(lines)
                          if re.match(r"^##\s+", line)), len(lines))
    lines.insert(insert_at, marker)
    return "\n".join(lines)


def _factory_writes(repo: Path, plan):
    grouped: Dict[str, list] = {}
    for ref in plan.get("factory_doc_refs", []):
        if ref.get("status") != "resolved":
            continue
        if (ref.get("resolution") or {}).get("kind") != "repoint":
            continue
        grouped.setdefault(ref["path"], []).append(ref)
    writes, resolutions = [], []
    for rel, refs in sorted(grouped.items()):
        path = repo / rel
        if not path.is_file():
            continue
        lines = _read_text(path).split("\n")
        for ref in sorted(refs, key=lambda item: item["line"]):
            index = ref["line"] - 1
            if index < 0 or index >= len(lines):
                continue
            before = lines[index]
            after = before.replace("[[%s]]" % ref["token"],
                                   "[[%s]]" % ref["parent_id"])
            if after == before:
                continue
            lines[index] = after
            resolutions.append({"path": rel, "line": ref["line"], "before": before,
                                "after": after, "kind": "repoint"})
        writes.append((path, "\n".join(lines)))
    return writes, resolutions


def _merge_state(spec_dir: Path, ordered):
    manifest_path = spec_dir / MANIFEST_NAME
    manifest = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            manifest = None
    marks = []
    for item in ordered:
        found = [match.group(1) for line in
                 _read_text(item["path"] / "requirements.md").splitlines()
                 if (match := _MERGED_INTO_RE.match(line))]
        if len(found) > 1 or (found and spec_dir.name not in found[0]):
            raise ValueError(
                "slice %s carries an unusable `**Merged into**` marker" % item["slug"])
        marks.append(bool(found))
    if any(marks) and not all(marks):
        raise ValueError("some slices are marked merged and others are not; "
                         "partial merge state cannot be merged again deterministically")
    if ordered:
        completed = all(marks)
        if completed and (manifest is None or manifest.get("spec") != spec_dir.name):
            raise ValueError("slices are marked merged but %s is missing or foreign"
                             % MANIFEST_NAME)
        return completed, manifest
    return manifest is not None, manifest


# --- the manifest and its post-merge checks --------------------------------

def _continuous(numbers) -> bool:
    """Contiguous from the sequence's own first value (gaps/duplicates fail).

    The anchor is the minimum, not 1: clause ids are scoped per file and the
    real 074 trees number them across the whole contract set (``report-and-
    attribution.md`` starts at ``C-47``). A fixed ``1..max`` window would call
    every such file discontinuous and, worse, would pass only when the parser
    recognized no clauses at all.
    """
    values = sorted(set(numbers))
    return not values or values == list(range(values[0], values[-1] + 1))


def _scan_merged_checks(spec_dir: Path, dated_stable: bool) -> Dict[str, Any]:
    requirements = _read_text(spec_dir / "requirements.md")
    defs: Dict[str, list] = {"FR": [], "SC": []}
    for line in requirements.splitlines():
        match = re.match(r"^-\s+\*\*(FR|SC)-(\d{3})\*\*", line)
        if match:
            defs[match.group(1)].append(int(match.group(2)))
    strings = _parse_shared_strings(requirements)
    string_numbers = [int(string_id.split("-")[1]) for string_id in strings]
    continuity = (_continuous(defs["FR"]) and _continuous(defs["SC"])
                  and _continuous(string_numbers))
    duplicates = sum(len(values) - len(set(values)) for values in defs.values())
    duplicates += len(string_numbers) - len(set(string_numbers))

    tasks_path = spec_dir / "tasks.md"
    tasks_text = _read_text(tasks_path) if tasks_path.is_file() else ""
    task_numbers, open_rows = [], 0
    for line in tasks_text.splitlines():
        match = _TASK_ROW_RE.match(line)
        if not match:
            continue
        task_numbers.append(int(match.group(2)[1:]))
        if match.group(1) in (" ", ">"):
            open_rows += 1
    continuity = continuity and _continuous(task_numbers)
    duplicates += len(task_numbers) - len(set(task_numbers))

    texts = [requirements, tasks_text]
    contracts_dir = spec_dir / "contracts"
    if contracts_dir.is_dir():
        for contract in sorted(contracts_dir.glob("*.md")):
            texts.append(_read_text(contract))
            clause_numbers = [int(clause["id"].split("-")[1])
                              for clause in _contract_clauses(contract)]
            continuity = continuity and _continuous(clause_numbers)
            duplicates += len(clause_numbers) - len(set(clause_numbers))
    model_path = spec_dir / "data-model.md"
    if model_path.is_file():
        texts.append(_read_text(model_path))
        entity_numbers = [int(entity["id"][1:]) for entity in _entity_rows(model_path)]
        continuity = continuity and _continuous(entity_numbers)
        duplicates += len(entity_numbers) - len(set(entity_numbers))

    defined_fr = set(defs["FR"])
    defined_sc = set(defs["SC"])
    dangling = 0
    for text in texts:
        for line in text.splitlines():
            for match in re.finditer(r"\bFR-(\d{3})\b", line):
                if int(match.group(1)) not in defined_fr:
                    dangling += 1
            for match in re.finditer(r"\bSC-(\d{3})\b", line):
                if int(match.group(1)) not in defined_sc:
                    dangling += 1
            for match in _STR_REF_RE.finditer(line):
                if match.group(1) not in strings:
                    dangling += 1
    return {
        "id_continuity": "pass" if continuity else "fail",
        "duplicate_ids": duplicates,
        "dangling_refs": dangling,
        "open_rows": open_rows,
        "dated_record_hashes_stable": dated_stable,
    }


def _manifest_document(repo: Path, spec_dir: Path, plan, dispositions,
                       resolutions, checks) -> Dict[str, Any]:
    artifacts = []
    for row in plan["artifacts"]:
        entry = dict(row)
        entry["checks"] = {}
        if row["name"] == "requirements.md":
            entry["checks"] = {"id_continuity": checks["id_continuity"],
                               "duplicate_ids": checks["duplicate_ids"],
                               "dangling_refs": checks["dangling_refs"]}
        elif row["name"] == "tasks.md":
            entry["checks"] = {"open_rows": checks["open_rows"]}
        artifacts.append(entry)
    merge = {"status": "merged"}
    if not plan["slices"]:
        merge = {
            "status": "not-applicable",
            "basis": "the slice set is empty: no directory in `.specify/specs/` "
                     "satisfies both the name-family and parent-declaration conditions",
        }
    return {
        "schema_version": 1,
        "spec": spec_dir.name,
        "merge": merge,
        "generated_by": {
            "engine": ENGINE_NAME,
            "version": _engine_version(),
            "command": "%s --action merge-apply --spec-dir %s" % (
                ENGINE_NAME, _rel_path(repo, spec_dir)),
        },
        "slices": plan["slices"],
        "artifacts": artifacts,
        "factory_doc_resolutions": resolutions,
        "id_maps": plan["id_maps"],
        "conflicts": [],
        "dispositions": dispositions,
        "checks": checks,
    }


def _apply_merge(repo: Path, spec_dir: Path, plan, ordered) -> Dict[str, Any]:
    id_maps = plan["id_maps"]
    carriers = [entry["carrier_tasks"] for entry in plan["slices"]
                if entry.get("carrier_tasks")]
    dated_before = _dated_snapshot(ordered)
    parent_tasks = spec_dir / "tasks.md"
    superseded_rows = (_open_task_rows(_read_text(parent_tasks))
                       if plan["slices"] and parent_tasks.is_file() else [])
    written: list = []

    outputs = []
    for row in plan["artifacts"]:
        if row["action"] in ("keep", "not-applicable"):
            continue
        content = _artifact_content(repo, spec_dir, row, ordered, id_maps, carriers)
        if content is not None:
            outputs.append((spec_dir / row["name"], content))
    for item in ordered:
        content = _slice_marker_content(spec_dir, item)
        if content is not None:
            outputs.append((item["path"] / "requirements.md", content))
    factory_writes, resolutions = _factory_writes(repo, plan)

    for path, content in outputs + factory_writes:
        _write_if_changed(path, content, written, repo)

    dated_stable = _dated_snapshot(ordered) == dated_before
    if not dated_stable:
        raise ValueError("a slice dated record changed during the run; "
                         "merge-apply must never rewrite measurements")
    checks = _scan_merged_checks(spec_dir, dated_stable)
    dispositions = []
    for row in superseded_rows:
        dispositions.append({
            "disposition": "supersede",
            "superseded": {"path": _rel_path(repo, parent_tasks), "line": row["line"]},
            "superseded_by": {"path": MANIFEST_NAME, "line": 0},
            "evidence": carriers,
            "guard_status": "replaced",
        })
    document = _manifest_document(repo, spec_dir, plan, dispositions, resolutions, checks)
    canonical = json.dumps(document, separators=(",", ":"), sort_keys=True,
                           ensure_ascii=False)
    document["digest"] = "sha256:" + hashlib.sha256(
        canonical.encode("utf-8")).hexdigest()
    manifest_path = spec_dir / MANIFEST_NAME
    _write_if_changed(manifest_path,
                      json.dumps(document, indent=2, sort_keys=True,
                                 ensure_ascii=False) + "\n",
                      written, repo)
    return {
        "manifest": _rel_path(repo, manifest_path),
        "idempotent": False,
        "slices": [item["slug"] for item in ordered],
        "writes": sorted(written),
        "dispositions": len(dispositions),
        "factory_doc_resolutions": len(resolutions),
        "checks": checks,
    }


def action_merge_apply(args: argparse.Namespace, spec_dir: Path) -> Tuple[Dict[str, Any], int]:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    try:
        plan = _build_plan(repo, spec_dir)
    except ArchiveManifestError as exc:
        return _archive_manifest_error("merge-apply", spec_dir, exc), EXIT_INPUT_ERROR
    except (OSError, ValueError, StopIteration) as exc:
        return _payload(
            "merge-apply", spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "merge-apply-error",
                "the merge plan cannot be derived from this tree: %s" % exc,
                "repair the named input (spec tree, split record or registries)",
                "rerun the same command after the input is repaired",
            )],
        ), EXIT_INPUT_ERROR
    open_conflicts = [c for c in plan["conflicts"] if c["status"] == "open"]
    if open_conflicts:
        conditions = [
            _condition(
                item["code"],
                "%s %s: %s <<>> %s" % (
                    item["artifact"], item["unit"],
                    item["side_a"].get("excerpt", ""), item["side_b"].get("excerpt", "")),
                "; ".join(item["candidates"]),
                "resolve the named records, then rerun merge-apply",
            ) for item in open_conflicts
        ]
        payload = _payload("merge-apply", spec_dir, "refused", EXIT_REFUSED, conditions)
        payload["plan"] = plan
        return payload, EXIT_REFUSED

    slices, _excluded = _discover_slices(spec_dir, repo)
    ordered = _derive_order(repo, spec_dir.name, slices)

    unclosed = _unclosed_slice_rows(repo, ordered)
    if unclosed:
        conditions = [
            _condition(
                "slice-unclosed",
                "%s:%d %s is not closed (state `- [%s]`)" % (path, line, task_id, state),
                "close the slice task, or record its `deferred_tasks=` entry in the "
                "slice verification.md",
                "rerun merge-apply after the slice is closed",
            ) for path, line, task_id, state in unclosed
        ]
        return _payload("merge-apply", spec_dir, "refused", EXIT_REFUSED,
                        conditions), EXIT_REFUSED

    try:
        completed, manifest = _merge_state(spec_dir, ordered)
    except ValueError as exc:
        return _payload(
            "merge-apply", spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "merge-state-inconsistent",
                str(exc),
                "inspect the slice markers and merge-manifest.json; restore one "
                "coherent state before rerunning",
                "rerun merge-apply after the merged state is repaired",
            )],
        ), EXIT_INPUT_ERROR

    if completed:
        manifest = manifest if isinstance(manifest, dict) else {}
        payload = _payload("merge-apply", spec_dir, "ok", EXIT_OK, [])
        payload["apply"] = {
            "manifest": _rel_path(repo, spec_dir / MANIFEST_NAME),
            "idempotent": True,
            "slices": [item["slug"] for item in ordered],
            "writes": [],
            "dispositions": len(manifest.get("dispositions", [])),
            "factory_doc_resolutions": len(manifest.get("factory_doc_resolutions", [])),
            "checks": manifest.get("checks", {}),
        }
        return payload, EXIT_OK

    try:
        summary = _apply_merge(repo, spec_dir, plan, ordered)
    except (OSError, ValueError, StopIteration) as exc:
        return _payload(
            "merge-apply", spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "merge-write-failed",
                "the merge could not be written deterministically: %s" % exc,
                "repair the named write failure, then rerun; the engine never "
                "rewrites a dated record",
                "rerun merge-apply after the failure is repaired",
            )],
        ), EXIT_INPUT_ERROR
    payload = _payload("merge-apply", spec_dir, "ok", EXIT_OK, [])
    payload["apply"] = summary
    return payload, EXIT_OK


# ---------------------------------------------------------------------------
# Seal surface (C-005 … C-010, C-032 … C-034, C-037 … C-042, C-044)
# ---------------------------------------------------------------------------

#: C-042: the closed refusal code set of the `seal` action.
SEAL_REFUSAL_CODES = (
    "from-status-invalid", "slice-not-sealable", "review-missing", "p0-unresolved",
    "code-review-blocking", "closure-refused", "closure-input-defect",
    "merge-incomplete", "conflict-open", "slice-unclosed", "dirty-spec-tree",
)
#: Exit 2 members: input or environment errors, never read as a pass (DoD-5).
SEAL_EXIT2_CODES = ("state-drift", "closure-input-defect", "git-unavailable",
                    "seal-receipt-invalid", "seal-write-failed")

DETAIL_STATUS_RE = re.compile(r"(?m)^\*\*Status\*\*:\s*(.+?)\s*$")
REGISTRY_SEPARATOR_RE = re.compile(r"^:?-+:?$")
SEAL_P0_LINE_RE = re.compile(r"^\s*-\s+\*\*Severity\*\*:\s*P0\s*$")
SEAL_FIX_RE = re.compile(r"^\s*-\s+\*\*Fix\*\*:\s*(.+)$")
SEAL_USER_WAIVER_RE = re.compile(r"^\s*-\s+\*\*User waiver\*\*:\s*(.+)$")
BLOCKING_HEADING_RE = re.compile(r"^### .*\[BLOCKING\]")
FINAL_PATH_KEYS_SEAL = ("pass", "blocked", "deferred", "partial", "fail", "unknown",
                        "total")

DEFAULT_SLICES_BASIS = (
    "the slice set is empty: no directory in `.specify/specs/` satisfies both the "
    "name-family and the parent-declaration conditions"
)
SEAL_FIX_GUIDANCE = (
    "repair the named input, commit the spec tree, then rerun seal"
)


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _resolve_override(raw: Optional[str]) -> Optional[Path]:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _carrier_paths(repo: Path, spec_dir: Path, args: argparse.Namespace):
    """The two claimed-status carriers, resolved exactly like the closure engine.

    `--feature-detail` / `--feature-registry` win; a spec-local carrier file is the
    fixture form; otherwise the repository registry and `.specify/features/<key>.md`.
    """
    detail = _resolve_override(args.feature_detail)
    if detail is None:
        local = spec_dir / "feature-detail.md"
        detail = local if local.is_file() else (
            repo / ".specify" / "features" / ("%s.md" % spec_dir.name))
    registry = _resolve_override(args.feature_registry)
    if registry is None:
        local = spec_dir / "feature-registry.md"
        registry = local if local.is_file() else repo / ".specify" / "features.md"
    return detail, registry


def _detail_status(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    match = DETAIL_STATUS_RE.search(_read_text(path))
    return match.group(1).strip() if match else None


def _registry_row(text: str, key: str) -> Optional[Dict[str, Any]]:
    """The registry data row for `key`, located by header name, never by position."""
    wanted = {key}
    digits = re.match(r"^(\d+)", key)
    if digits:
        wanted.add(digits.group(1))
    header = None
    for index, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped.startswith("|"):
            # A blank line inside the table is a formatting fact: the real
            # `.specify/features.md` separates row blocks with blank lines. Only
            # non-blank, non-table content (prose, a new heading) ends the table
            # context; resetting on a blank line silently hides every row after it.
            if stripped:
                header = None
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if header is None:
            lowered = [cell.casefold() for cell in cells]
            if "id" in lowered:
                header = {name: position for position, name in enumerate(lowered)}
            continue
        if cells and all(REGISTRY_SEPARATOR_RE.match(cell) for cell in cells if cell):
            continue
        if cells and cells[0] in wanted:
            status_col = header.get("status") if header else None
            if status_col is None or status_col >= len(cells):
                status_col = 3 if len(cells) > 3 else None
            updated_col = header.get("last updated") if header else None
            if updated_col is not None and updated_col >= len(cells):
                updated_col = None
            return {"line": index, "cells": cells, "status_col": status_col,
                    "updated_col": updated_col}
    return None


def _registry_cell(row: Optional[Dict[str, Any]], column: Optional[int]):
    if row is None or column is None or column >= len(row["cells"]):
        return None
    return row["cells"][column]


def _seal_state(repo: Path, spec_dir: Path, args: argparse.Namespace) -> Dict[str, Any]:
    detail_path, registry_path = _carrier_paths(repo, spec_dir, args)
    registry_text = _read_text(registry_path) if registry_path.is_file() else ""
    row = _registry_row(registry_text, spec_dir.name) if registry_text else None
    return {
        "detail_path": detail_path,
        "registry_path": registry_path,
        "registry_text": registry_text,
        "registry_row": row,
        "detail_status": _detail_status(detail_path),
        "registry_status": _registry_cell(row, row["status_col"] if row else None),
    }


def _run_git(repo: Path, arguments) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo)] + list(arguments),
                          capture_output=True, text=True, encoding="utf-8",
                          check=False)


def _git_dirty_paths(repo: Path, spec_dir: Path):
    proc = _run_git(repo, ["status", "--porcelain", "--", str(spec_dir)])
    if proc.returncode != 0:
        return None
    paths = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        entry = line[3:] if len(line) >= 3 else line.strip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.append(entry.strip().strip('"'))
    return paths


def _heading_block(text: str, pattern: str) -> Optional[Dict[str, Any]]:
    """The first heading (level 2–6) matching `pattern`, with its body and end index."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,6})\s+(.*)$", line)
        if not match or not re.search(pattern, match.group(2)):
            continue
        level = len(match.group(1))
        body = []
        cursor = index + 1
        while cursor < len(lines):
            inner = re.match(r"^(#{2,6})\s+", lines[cursor])
            if inner and len(inner.group(1)) <= level:
                break
            body.append((cursor + 1, lines[cursor]))
            cursor += 1
        return {"start": index + 1, "start_index": index, "end_index": cursor,
                "level": level, "body": body}
    return None


def _review_summary(text: str) -> Dict[str, int]:
    block = _heading_block(text, r"Findings Summary")
    lines = [line for _line_no, line in block["body"]] if block else text.splitlines()
    counts = {"P0": 0, "P1": 0, "P2": 0}
    for line in lines:
        match = re.match(r"^\|\s*(P0|P1|P2)\s*\|\s*(\d+)\s*\|", line)
        if match:
            counts[match.group(1)] = int(match.group(2))
    return counts


def _finding_blocks(text: str):
    blocks = []
    current = None
    for index, line in enumerate(text.splitlines()):
        heading = re.match(r"^###\s+(.*)$", line)
        if heading:
            if current is not None:
                blocks.append(current)
            title = heading.group(1).strip()
            identifier = re.match(r"^(F\d+)\b", title)
            current = {"id": identifier.group(1) if identifier else title,
                       "title": title, "line": index + 1, "body": []}
            continue
        if current is None:
            continue
        if re.match(r"^##\s+", line):
            blocks.append(current)
            current = None
            continue
        current["body"].append((index + 1, line))
    if current is not None:
        blocks.append(current)
    return blocks


def _fix_pointer_resolves(repo: Path, text: str) -> bool:
    """C-044(a): a path that exists or a commit that git can resolve."""
    tokens = re.findall(r"`([^`]+)`", text)
    tokens += re.findall(r"(?<![\w/.-])([0-9a-f]{7,40})(?![\w-])", text)
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if "/" in token:
            candidate = Path(token)
            if not candidate.is_absolute():
                candidate = repo / token
            if candidate.exists():
                return True
        if re.fullmatch(r"[0-9a-f]{7,40}", token):
            if _run_git(repo, ["cat-file", "-e",
                               token + "^{commit}"]).returncode == 0:
                return True
    return False


def _names_finding(line: str, finding_id: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])"
                     % re.escape(finding_id), line) is not None


def _carrier_waiver(text: str, section_pattern: str, finding_id: str) -> bool:
    block = _heading_block(text, section_pattern)
    if block is None:
        return False
    for _line_no, line in block["body"]:
        if SEAL_USER_WAIVER_RE.match(line) and _names_finding(line, finding_id):
            return True
    return False


def _p0_findings(repo: Path, review_text: str, detail_text: str, carrier: Path,
                 review_label: str = ""):
    """Every P0 finding with its disposition form; C-044 decides 'disposed'.

    `carrier` names the record the finding block was read from and `review_label`
    qualifies the finding id when it comes from a slice record (``<slug>:F1``).
    A split parent's merged `review.md` is a pointer view carrying no finding
    block, so the judgment MUST read the original slice records as well; the
    user-waiver carrier for a slice finding is that slice record's code section.
    """
    findings = []
    for block in _finding_blocks(review_text):
        if not any(SEAL_P0_LINE_RE.match(line) for _line_no, line in block["body"]):
            continue
        fix_text = ""
        for _line_no, line in block["body"]:
            match = SEAL_FIX_RE.match(line)
            if match:
                fix_text = match.group(1)
                break
        by_fix = bool(fix_text) and _fix_pointer_resolves(repo, fix_text)
        by_waiver = (_carrier_waiver(review_text, r"Code Segment", block["id"])
                     and _carrier_waiver(detail_text, r"Latest Review", block["id"]))
        form = "fix" if by_fix else ("user-waiver" if by_waiver else None)
        findings.append({"finding": "%s%s" % (review_label, block["id"]),
                         "line": block["line"], "resolved": form is not None,
                         "form": form, "carrier": carrier})
    return findings


def _run_closure(repo: Path, spec_dir: Path, detail_path: Path, registry_path: Path,
                 args: argparse.Namespace) -> Dict[str, Any]:
    engine = Path(__file__).resolve().parent / "closure-acceptance-check.py"
    argv = [sys.executable, str(engine), "--spec-dir", str(spec_dir),
            "--repo", str(repo), "--json"]
    if args.feature_detail:
        argv += ["--feature-detail", str(detail_path)]
    if args.feature_registry:
        argv += ["--feature-registry", str(registry_path)]
    command = " ".join(argv[1:])
    try:
        proc = subprocess.run(argv, cwd=str(repo), capture_output=True, text=True,
                              encoding="utf-8", check=False)
    except OSError as exc:
        return {"exit_code": None, "command": command, "payload": None,
                "stderr": "%s: %s" % (type(exc).__name__, exc)}
    payload = None
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            payload = None
    return {"exit_code": proc.returncode, "command": command, "payload": payload,
            "stderr": proc.stderr or ""}


def _merge_assessment(repo: Path, spec_dir: Path, slices, ordered):
    """FR-008 completeness from `merge-manifest.json`; names every unmet item."""
    conditions = []
    manifest_path = spec_dir / MANIFEST_NAME
    rel_manifest = _rel_path(repo, manifest_path)
    manifest = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(_read_text(manifest_path))
        except ValueError:
            manifest = "invalid"
    if not isinstance(manifest, dict):
        manifest = None if not manifest_path.is_file() else "invalid"
    slice_slugs = [item["slug"] for item in ordered]
    info = {"manifest": rel_manifest, "slices": slice_slugs,
            "status": "not-applicable" if not slices else "merged", "basis": None}

    if not slices:
        if manifest is None:
            info["manifest"] = None
            info["basis"] = DEFAULT_SLICES_BASIS
            return info, conditions
        if manifest == "invalid":
            conditions.append(_condition(
                "merge-incomplete",
                "%s is unparsable; the empty-slice decision cannot be read"
                % rel_manifest,
                SEAL_FIX_GUIDANCE, "rerun seal after the manifest is repaired"))
            return info, conditions
        merge = manifest.get("merge") or {}
        basis = str(merge.get("basis") or "").strip()
        if merge.get("status") != "not-applicable" or not basis:
            conditions.append(_condition(
                "merge-incomplete",
                "%s does not record `not-applicable` with a basis for the empty "
                "slice set" % rel_manifest,
                SEAL_FIX_GUIDANCE, "rerun seal after the manifest is repaired"))
            return info, conditions
        info["basis"] = merge["basis"]
        return info, conditions

    if manifest is None:
        conditions.append(_condition(
            "merge-incomplete",
            "%d slice(s) are present (%s) but %s is absent"
            % (len(slices), ",".join(slice_slugs), rel_manifest),
            "run merge-apply against this parent before sealing; the manifest is "
            "the completeness record",
            "rerun seal after merge-apply has produced the manifest"))
        return info, conditions
    if manifest == "invalid":
        conditions.append(_condition(
            "merge-incomplete", "%s is unparsable" % rel_manifest,
            SEAL_FIX_GUIDANCE, "rerun seal after the manifest is repaired"))
        return info, conditions
    merge = manifest.get("merge") or {}
    if manifest.get("spec") != spec_dir.name:
        conditions.append(_condition(
            "merge-incomplete",
            "%s names spec %r, not %r" % (rel_manifest, manifest.get("spec"),
                                          spec_dir.name),
            SEAL_FIX_GUIDANCE, "rerun seal after the manifest is repaired"))
    if merge.get("status") != "merged":
        conditions.append(_condition(
            "merge-incomplete",
            "%s records merge status %r while %d slice(s) are present"
            % (rel_manifest, merge.get("status"), len(slices)),
            SEAL_FIX_GUIDANCE, "rerun seal after the merge is completed"))
    recorded_slugs = [entry.get("slug") for entry in manifest.get("slices") or []
                      if isinstance(entry, dict)]
    missing_slugs = [slug for slug in slice_slugs if slug not in recorded_slugs]
    if missing_slugs:
        conditions.append(_condition(
            "merge-incomplete",
            "%s carries no slice record for %s"
            % (rel_manifest, ",".join(missing_slugs)),
            SEAL_FIX_GUIDANCE, "rerun seal after the manifest is repaired"))
    expected = _classify_artifacts(repo, spec_dir, ordered)
    recorded = {row.get("name"): row for row in manifest.get("artifacts") or []
                if isinstance(row, dict)}
    uncovered = [row["name"] for row in expected if row["name"] not in recorded]
    if uncovered:
        conditions.append(_condition(
            "merge-incomplete",
            "%s has no merge record for: %s" % (rel_manifest, ", ".join(uncovered)),
            SEAL_FIX_GUIDANCE, "rerun seal after the manifest is repaired"))
    gaps = []
    for name, row in sorted(recorded.items()):
        per_slice = {entry.get("slice") for entry in row.get("per_slice") or []
                     if isinstance(entry, dict)}
        missing = [slug for slug in slice_slugs if slug not in per_slice]
        if missing:
            gaps.append("%s lacks per_slice rows for %s" % (name, ",".join(missing)))
        if row.get("action") == "not-applicable" \
                and not str(row.get("basis") or "").strip():
            gaps.append("%s is not-applicable without a basis" % name)
    if gaps:
        conditions.append(_condition(
            "merge-incomplete", "; ".join(gaps), SEAL_FIX_GUIDANCE,
            "rerun seal after the manifest is repaired"))
    checks = manifest.get("checks") or {}
    failed = []
    if checks.get("id_continuity") != "pass":
        failed.append("id_continuity=%r" % checks.get("id_continuity"))
    if checks.get("duplicate_ids") != 0:
        failed.append("duplicate_ids=%r" % checks.get("duplicate_ids"))
    if checks.get("dangling_refs") != 0:
        failed.append("dangling_refs=%r" % checks.get("dangling_refs"))
    if checks.get("open_rows") != 0:
        failed.append("open_rows=%r" % checks.get("open_rows"))
    if checks.get("dated_record_hashes_stable") is not True:
        failed.append("dated_record_hashes_stable=%r"
                      % checks.get("dated_record_hashes_stable"))
    if failed:
        conditions.append(_condition(
            "merge-incomplete",
            "%s post-merge checks did not pass: %s" % (rel_manifest, ", ".join(failed)),
            "repair the merged artifacts and run merge-apply again",
            "rerun seal after the merged checks pass"))
    for conflict in manifest.get("conflicts") or []:
        if isinstance(conflict, dict) and conflict.get("status") == "open":
            conditions.append(_condition(
                "conflict-open",
                "%s %s: %s" % (conflict.get("artifact"), conflict.get("unit"),
                               conflict.get("id")),
                "resolve the conflict and rerun merge-apply so the manifest "
                "records the resolution",
                "rerun seal after no conflict remains open"))
    return info, conditions


def _slice_parent_hint(spec_dir: Path) -> Optional[str]:
    text = _read_text(spec_dir / "requirements.md")
    field = re.search(r"(?m)^\*\*Parent spec\*\*:\s*(.+)$", text)
    if field:
        return field.group(1).strip().strip("`")
    body = _heading_block(text, r"Parent Mapping")
    if body is not None:
        for _line_no, line in body["body"]:
            match = re.search(r"\d{3}[a-z]*-[a-z0-9][a-z0-9-]*", line)
            if match:
                return match.group(0)
        return "(declared via `## Parent Mapping`)"
    return None


def _read_seal_core(path: Path) -> Optional[Dict[str, Any]]:
    text = _read_text(path)
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    if len(blocks) != 1:
        return None
    try:
        core = json.loads(blocks[0])
    except ValueError:
        return None
    return core if isinstance(core, dict) else None


def _replace_row_cells(line: str, updates: Dict[int, str]) -> str:
    parts = line.split("|")
    for column, value in updates.items():
        position = column + 1
        if position >= len(parts):
            continue
        cell = parts[position]
        content = cell.strip()
        leading = cell[:len(cell) - len(cell.lstrip())]
        trailing = cell[len(cell.rstrip()):]
        if not content:
            leading = leading or " "
            trailing = trailing or " "
        parts[position] = leading + value + trailing
    return "|".join(parts)


def _registry_sealed_text(text: str, row: Dict[str, Any], date: str) -> str:
    lines = text.split("\n")
    updates = {row["status_col"]: "Sealed"}
    if row["updated_col"] is not None:
        updates[row["updated_col"]] = date
    lines[row["line"]] = _replace_row_cells(lines[row["line"]], updates)
    return _ensure_newline("\n".join(lines))


def _detail_sealed_text(text: str, date: str, short_sha: str) -> str:
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if DETAIL_STATUS_RE.match(line):
            lines[index] = "**Status**: Sealed"
            break
    entry = ("- %s — Sealed by /speckit.seal; receipt: seal.md (pinned %s)."
             % (date, short_sha))
    block = _heading_block("\n".join(lines), r"Latest Review")
    if block is None:
        lines.extend(["", "## Latest Review", "", entry])
    else:
        insert_at = block["end_index"]
        while insert_at - 1 > block["start_index"] and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, entry)
    return _ensure_newline("\n".join(lines))


def _seal_receipt_text(spec_dir: Path, core: Dict[str, Any]) -> str:
    return (
        "# Seal Record — %s\n\n"
        "> Generated by `/speckit.seal`. The machine-readable core below is the "
        "closed field set; it references every measurement at its source and never "
        "restates a second measurement.\n\n"
        "```json\n%s\n```\n"
        % (spec_dir.name, json.dumps(core, indent=2, sort_keys=True,
                                     ensure_ascii=False))
    )


def _write_seal_batch(targets) -> Optional[str]:
    """C-005: one batch; a failure restores the previous bytes of every written file.

    The engine never deletes anything (C-008), so the receipt — the only file that
    may be newly created — is written last: a failure leaves no status change and
    no earlier receipt half-written.
    """
    originals: Dict[Path, Optional[bytes]] = {}
    written = []
    try:
        for path, text in targets:
            originals[path] = path.read_bytes() if path.is_file() else None
            path.write_text(text, encoding="utf-8")
            written.append(path)
    except (OSError, UnicodeError) as exc:
        for path in reversed(written):
            previous = originals.get(path)
            if previous is not None:
                try:
                    path.write_bytes(previous)
                except OSError:
                    pass
        return ("%s: %s; every file this batch had already written was restored "
                "to its previous bytes" % (type(exc).__name__, exc))
    return None


def _seal_error(spec_dir: Path, code: str, evidence: str,
                fix_path: str) -> Tuple[Dict[str, Any], int, None]:
    payload = _payload("seal", spec_dir, "error", EXIT_INPUT_ERROR,
                       [_condition(code, evidence, fix_path,
                                   "rerun seal after the named input is repaired")])
    payload["seal"] = {"outcome": "error", "receipt": None, "from_status": None,
                       "to_status": None, "writes": []}
    return payload, EXIT_INPUT_ERROR, None


def evaluate_seal(args: argparse.Namespace, spec_dir: Path):
    """C-005 judgment phase: read-only; computes every precondition, writes nothing."""
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    judged_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    judged_date = judged_at[:10]

    hint = _slice_parent_hint(spec_dir)
    if hint is not None:
        payload = _payload(
            "seal", spec_dir, "refused", EXIT_REFUSED,
            [_condition(
                "slice-not-sealable",
                "%s declares a parent spec (%s); a slice directory is never the "
                "seal subject" % (spec_dir.name, hint),
                "run seal against the parent spec directory: %s" % hint,
                "rerun with --spec-dir pointing at the parent spec")])
        payload["seal"] = {"outcome": "refused", "receipt": None,
                           "from_status": None, "to_status": None, "writes": []}
        return payload, EXIT_REFUSED, None

    status = _seal_state(repo, spec_dir, args)
    detail_status = status["detail_status"]
    registry_status = status["registry_status"]
    if detail_status is None or registry_status is None \
            or detail_status != registry_status:
        return _seal_error(
            spec_dir, "state-drift",
            "the claimed status pair is inconsistent: detail=%r (%s); registry=%r (%s)"
            % (detail_status, _rel_path(repo, status["detail_path"]),
               registry_status, _rel_path(repo, status["registry_path"])),
            "repair the status pair through the registry reconcile owner; seal "
            "never picks one carrier over the other")

    if detail_status == "Sealed":
        receipt = spec_dir / "seal.md"
        payload = _payload("seal", spec_dir, "ok", EXIT_OK, [])
        payload["seal"] = {
            "outcome": "already-sealed",
            "receipt": _rel_path(repo, receipt) if receipt.is_file() else None,
            "from_status": "Sealed", "to_status": "Sealed", "writes": [],
        }
        return payload, EXIT_OK, None

    receipt_path = spec_dir / "seal.md"
    supersedes = None
    if receipt_path.is_file():
        previous = _read_seal_core(receipt_path)
        pinned = str((previous or {}).get("pinned_commit") or "").strip()
        if not pinned:
            return _seal_error(
                spec_dir, "seal-receipt-invalid",
                "%s exists but carries no readable machine core with a pinned commit"
                % _rel_path(repo, receipt_path),
                "repair or remove the unreadable receipt before resealing")
        supersedes = pinned

    conditions = []
    if detail_status != "Ready for Review":
        conditions.append(_condition(
            "from-status-invalid",
            "the claimed status pair reads %r; seal requires `Ready for Review` "
            "(detail: %s; registry: %s)"
            % (detail_status, _rel_path(repo, status["detail_path"]),
               _rel_path(repo, status["registry_path"])),
            "return the feature to `Ready for Review` through its owner flow, or "
            "seal is not applicable",
            "rerun seal once the status pair reads Ready for Review"))

    review_path = spec_dir / "review.md"
    code_review_path = spec_dir / "code-review.md"
    review_text = _read_text(review_path) if review_path.is_file() else ""
    code_review_text = _read_text(code_review_path) if code_review_path.is_file() else ""
    if not review_path.is_file():
        conditions.append(_condition(
            "review-missing",
            "the current review record is absent: %s" % _rel_path(repo, review_path),
            "produce the review through /speckit.review",
            "rerun seal after review.md is present"))
    if not code_review_path.is_file():
        conditions.append(_condition(
            "review-missing",
            "the current code-review record is absent: %s"
            % _rel_path(repo, code_review_path),
            "produce the code review through /speckit.review",
            "rerun seal after code-review.md is present"))

    # A split parent's merged review/code-review views are pointer views and carry
    # no finding block (C-013/C-021); the judgment therefore reads the original
    # slice records as well — the pointer view never narrows the reading surface.
    slices, _excluded = _discover_slices(spec_dir, repo)
    ordered = _derive_order(repo, spec_dir.name, slices) if slices else []
    review_records = [(review_path, review_text)]
    code_review_records = [(code_review_path, code_review_text)]
    for item in ordered:
        slice_review = item["path"] / "review.md"
        if slice_review.is_file():
            review_records.append((slice_review, _read_text(slice_review)))
        slice_code_review = item["path"] / "code-review.md"
        if slice_code_review.is_file():
            code_review_records.append(
                (slice_code_review, _read_text(slice_code_review)))

    detail_text = _read_text(status["detail_path"]) \
        if status["detail_path"].is_file() else ""
    p0_findings, summary_sources = [], []
    for record_path, record_text in review_records:
        label = "" if record_path == review_path else "%s:" % record_path.parent.name
        record_findings = _p0_findings(repo, record_text, detail_text,
                                       record_path, label)
        p0_findings.extend(record_findings)
        summary_sources.append((record_path,
                                _review_summary(record_text) if record_text
                                else {"P0": 0, "P1": 0, "P2": 0},
                                len(record_findings)))
    summary = {key: sum(source[key] for _path, source, _parsed in summary_sources)
               for key in ("P0", "P1", "P2")}
    unresolved = [entry for entry in p0_findings if not entry["resolved"]]
    unaccounted = sum(max(0, source["P0"] - parsed)
                      for _path, source, parsed in summary_sources)
    for entry in unresolved:
        conditions.append(_condition(
            "p0-unresolved",
            "%s (line %d of %s) has neither a resolvable `- **Fix**:` pointer nor "
            "a user waiver on both carriers"
            % (entry["finding"], entry["line"], _rel_path(repo, entry["carrier"])),
            "fix the finding and record the fix pointer, or record the user's "
            "literal `- **User waiver**:` line on the review's code segment and "
            "the feature detail's `## Latest Review`",
            "rerun seal after the P0 is disposed"))
    for record_path, record_summary, parsed in summary_sources:
        missing = max(0, record_summary["P0"] - parsed)
        if missing:
            conditions.append(_condition(
                "p0-unresolved",
                "the findings summary of %s reports %d P0 finding(s) but only %d "
                "P0 finding block(s) are parseable"
                % (_rel_path(repo, record_path), record_summary["P0"], parsed),
                "make every P0 finding carry a `- **Severity**: P0` block",
                "rerun seal after the findings are repaired"))

    blocking_entries = [(record_path, line) for record_path, record_text
                        in code_review_records for line in record_text.splitlines()
                        if BLOCKING_HEADING_RE.match(line)]
    for record_path, line in blocking_entries:
        conditions.append(_condition(
            "code-review-blocking",
            "a blocking code-review entry remains in %s: %s"
            % (_rel_path(repo, record_path), line.strip()),
            "resolve the blocking entry in the current code-review record",
            "rerun seal after the code review carries no blocking entry"))

    closure = _run_closure(repo, spec_dir, status["detail_path"],
                           status["registry_path"], args)
    closure_payload = closure["payload"]
    final_path = (closure_payload or {}).get("final_path")
    closure_ok = (closure["exit_code"] == 0 and isinstance(closure_payload, dict)
                  and closure_payload.get("verdict") == "accept"
                  and isinstance(final_path, dict)
                  and set(final_path) == set(FINAL_PATH_KEYS_SEAL))
    if not closure_ok:
        if closure["exit_code"] == 1 and isinstance(closure_payload, dict):
            reasons = "; ".join(
                "%s%s" % (reason.get("code"), ": " + str(reason.get("target"))
                          if reason.get("target") else "")
                for reason in closure_payload.get("reasons") or []) \
                or "the closure engine reported block"
            conditions.append(_condition(
                "closure-refused",
                "the closure verdict is block: %s" % reasons,
                "repair the acceptance record named by the closure reasons",
                "rerun seal after the closure verdict is accept"))
        else:
            detail = _first_line(closure.get("stderr")) or "no stderr captured"
            conditions.append(_condition(
                "closure-input-defect",
                "the closure engine exited %r: %s"
                % (closure["exit_code"], detail),
                "repair the acceptance input (every SC carries exactly one trailing "
                "`**Path**` marker and a status row), then rerun the closure engine",
                "rerun seal after the closure engine reads its inputs"))

    slices, _excluded = _discover_slices(spec_dir, repo)
    ordered = _derive_order(repo, spec_dir.name, slices) if slices else []
    review_paths = [_rel_path(repo, review_path),
                    _rel_path(repo, code_review_path)]
    for item in ordered:
        for name in ("review.md", "code-review.md"):
            path = item["path"] / name
            if path.is_file():
                review_paths.append(_rel_path(repo, path))
    merge_info, merge_conditions = _merge_assessment(repo, spec_dir, slices, ordered)
    conditions.extend(merge_conditions)
    for path, line_no, task_id, task_state in _unclosed_slice_rows(repo, ordered):
        conditions.append(_condition(
            "slice-unclosed",
            "%s:%d %s is not closed (state `- [%s]`)"
            % (path, line_no, task_id, task_state),
            "close the slice task, or record its `deferred_tasks=` entry in the "
            "slice verification.md",
            "rerun seal after the slice is closed"))

    head = None
    head_proc = _run_git(repo, ["rev-parse", "HEAD"])
    if head_proc.returncode != 0:
        conditions.append(_condition(
            "git-unavailable",
            "git cannot resolve HEAD under %s: %s"
            % (repo, _first_line(head_proc.stderr)),
            "run seal inside the repository that owns the spec tree",
            "rerun seal from a valid git work tree"))
    else:
        head = head_proc.stdout.strip()
    dirty = _git_dirty_paths(repo, spec_dir)
    if dirty is None:
        conditions.append(_condition(
            "git-unavailable",
            "git cannot read the status of %s" % _rel_path(repo, spec_dir),
            "run seal inside the repository that owns the spec tree",
            "rerun seal from a valid git work tree"))
    elif dirty:
        conditions.append(_condition(
            "dirty-spec-tree",
            "uncommitted paths under the parent spec tree: %s" % "; ".join(dirty),
            "commit or revert the named paths; seal stamps only a settled tree",
            "rerun seal after the parent spec tree is clean"))

    exit_code = EXIT_OK
    if conditions:
        exit_code = EXIT_INPUT_ERROR if any(
            condition["code"] in SEAL_EXIT2_CODES for condition in conditions) \
            else EXIT_REFUSED
    verdict = {EXIT_OK: "ok", EXIT_REFUSED: "refused",
               EXIT_INPUT_ERROR: "error"}[exit_code]
    if exit_code != EXIT_OK:
        payload = _payload("seal", spec_dir, verdict, exit_code, conditions)
        payload["seal"] = {"outcome": verdict, "receipt": None,
                           "from_status": detail_status, "to_status": "Sealed",
                           "writes": []}
        return payload, exit_code, None

    waiver_entries = [
        {"finding": entry["finding"], "form": "user-waiver",
         "source": "%s (code segment); %s (## Latest Review)"
                   % (_rel_path(repo, entry["carrier"]),
                      _rel_path(repo, status["detail_path"]))}
        for entry in p0_findings if entry["form"] == "user-waiver"]
    merge_block = {"manifest": merge_info["manifest"], "slices": merge_info["slices"],
                   "status": merge_info["status"]}
    if merge_info["status"] == "not-applicable":
        merge_block["basis"] = merge_info["basis"]
    core = {
        "judged_at": judged_at,
        "pinned_commit": head,
        "from_status": "Ready for Review",
        "to_status": "Sealed",
        "review": {
            "paths": review_paths,
            "counts": {"p0_unresolved": len(unresolved) + unaccounted,
                       "p1": summary["P1"], "p2": summary["P2"],
                       "blocking": len(blocking_entries)},
        },
        "closure": {"exit_code": closure["exit_code"],
                    "final_path": final_path,
                    "command": closure["command"]},
        "merge": merge_block,
        "waivers": waiver_entries,
        "engine": {"identity": ENGINE_NAME, "version": _engine_version(),
                   "command": "%s --action seal --spec-dir %s --repo %s"
                              % (ENGINE_NAME, _rel_path(repo, spec_dir),
                                 _rel_path(repo, repo))},
    }
    if supersedes:
        core["supersedes"] = supersedes
    payload = _payload("seal", spec_dir, "ok", EXIT_OK, [])
    payload["seal"] = {
        "outcome": "sealed", "receipt": _rel_path(repo, receipt_path),
        "from_status": "Ready for Review", "to_status": "Sealed", "writes": [],
    }
    evaluation = {
        "repo": repo,
        "payload": payload,
        "receipt_text": _seal_receipt_text(spec_dir, core),
        "registry": {"path": status["registry_path"],
                     "row": status["registry_row"]},
        "detail": {"path": status["detail_path"]},
        "date": judged_date,
        "short_sha": (head or "")[:12],
    }
    return payload, EXIT_OK, evaluation


def apply_seal(args: argparse.Namespace, spec_dir: Path,
               evaluation: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """C-005 write phase: one atomic batch; only reached when judgment passed."""
    repo = evaluation["repo"]
    registry_path = evaluation["registry"]["path"]
    detail_path = evaluation["detail"]["path"]
    registry_text = _read_text(registry_path)
    detail_text = _read_text(detail_path)
    row = _registry_row(registry_text, spec_dir.name)
    if row is None or _registry_cell(row, row["status_col"]) != "Ready for Review" \
            or _detail_status(detail_path) != "Ready for Review":
        payload = _payload(
            "seal", spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "state-drift",
                "the claimed status pair changed between judgment and write",
                "redo the judgment on the current tree",
                "rerun seal")],
        )
        payload["seal"] = {"outcome": "error", "receipt": None,
                           "from_status": None, "to_status": "Sealed", "writes": []}
        return payload, EXIT_INPUT_ERROR
    targets = [
        (registry_path,
         _registry_sealed_text(registry_text, row, evaluation["date"])),
        (detail_path,
         _detail_sealed_text(detail_text, evaluation["date"],
                             evaluation["short_sha"])),
        (spec_dir / "seal.md", evaluation["receipt_text"]),
    ]
    failure = _write_seal_batch(targets)
    if failure is not None:
        payload = _payload(
            "seal", spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "seal-write-failed", failure,
                "repair the named write failure; the batch is restored, so no "
                "partial seal survives",
                "rerun seal after the failure is repaired")])
        payload["seal"] = {"outcome": "error", "receipt": None,
                           "from_status": "Ready for Review", "to_status": "Sealed",
                           "writes": []}
        return payload, EXIT_INPUT_ERROR
    payload = evaluation["payload"]
    payload["seal"]["writes"] = [_rel_path(repo, path) for path, _text in targets]
    return payload, EXIT_OK


def action_seal(args: argparse.Namespace, spec_dir: Path) -> Tuple[Dict[str, Any], int]:
    evaluation, code, state = evaluate_seal(args, spec_dir)
    if evaluation["verdict"] != "ok" or state is None:
        return evaluation, code
    if state["payload"]["seal"]["outcome"] == "already-sealed":
        return evaluation, code
    return apply_seal(args, spec_dir, state)


def _gate_waiver_carrier(text: str, section_pattern: str, keys) -> bool:
    """C-044 literal form on one carrier: a `- **User waiver**:` line naming the row."""
    block = _heading_block(text, section_pattern)
    if block is None:
        return False
    return any(SEAL_USER_WAIVER_RE.match(line)
               and any(_names_finding(line, key) for key in keys)
               for _line_no, line in block["body"])


def _gate_ruling_present(spec_dir: Path, status: Dict[str, Any]) -> bool:
    """C-030: a legacy `Completed` row needs the user's ruling on BOTH carriers."""
    keys = [spec_dir.name, spec_dir.name.split("-", 1)[0]]
    review_path = spec_dir / "review.md"
    review_text = _read_text(review_path) if review_path.is_file() else ""
    detail_text = _read_text(status["detail_path"]) \
        if status["detail_path"].is_file() else ""
    return (_gate_waiver_carrier(review_text, r"Code Segment", keys)
            and _gate_waiver_carrier(detail_text, r"Latest Review", keys))


def action_archive_gate(args: argparse.Namespace, spec_dir: Path) -> Tuple[Dict[str, Any], int]:
    """C-030: the single archive-admission owner; read-only, one verdict per query.

    E11 payload: `{target, status, allowed, reason, pointer, exit}` under `gate`.
    `Sealed` (pair agrees, receipt readable) admits; every other status refuses by a
    named reason and points back to `/speckit.seal`; a drifting pair or a `Sealed` row
    without a readable receipt is an input defect (exit 2). A legacy `Completed` row is
    admitted only with the C-044 literal user ruling on both carriers.
    """
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    status = _seal_state(repo, spec_dir, args)
    detail_status = status["detail_status"]
    registry_status = status["registry_status"]
    target = _rel_path(repo, spec_dir)

    def verdict(claimed, allowed, reason, pointer, exit_code, conditions):
        tally = {EXIT_OK: "ok", EXIT_REFUSED: "refused", EXIT_INPUT_ERROR: "error"}
        payload = _payload("archive-gate", spec_dir, tally[exit_code], exit_code,
                           conditions)
        payload["gate"] = {"target": target, "status": claimed, "allowed": allowed,
                           "reason": reason, "pointer": pointer, "exit": exit_code}
        return payload, exit_code

    if detail_status is None or registry_status is None \
            or detail_status != registry_status:
        return verdict(
            None, False, "state-drift", "/speckit.seal", EXIT_INPUT_ERROR,
            [_condition(
                "state-drift",
                "the claimed status pair is inconsistent: detail=%r (%s); registry=%r (%s)"
                % (detail_status, _rel_path(repo, status["detail_path"]),
                   registry_status, _rel_path(repo, status["registry_path"])),
                "repair the status pair through the registry reconcile owner; the gate "
                "never picks one carrier over the other",
                "rerun the archive lane after the status pair agrees")])

    receipt_path = spec_dir / "seal.md"
    if detail_status == "Sealed":
        core = _read_seal_core(receipt_path) if receipt_path.is_file() else None
        pinned = str((core or {}).get("pinned_commit") or "").strip()
        if not pinned:
            return verdict(
                detail_status, False, "seal-receipt-invalid", "/speckit.seal",
                EXIT_INPUT_ERROR,
                [_condition(
                    "seal-receipt-invalid",
                    "the claimed status pair reads `Sealed` but %s is missing or carries "
                    "no readable machine core with a pinned commit"
                    % _rel_path(repo, receipt_path),
                    "restore the seal receipt (git history keeps the previous one) or "
                    "run the audit correction and seal again",
                    "rerun the archive lane after the receipt is readable")])
        return verdict(detail_status, True, "sealed", "seal.md", EXIT_OK, [])

    if detail_status == "Completed":
        if _gate_ruling_present(spec_dir, status):
            return verdict(detail_status, True, "legacy-completed-ruled", "seal.md",
                           EXIT_OK, [])
        return verdict(
            detail_status, False, "legacy-completed-unruled", "/speckit.seal",
            EXIT_REFUSED,
            [_condition(
                "legacy-completed-unruled",
                "the status pair reads the legacy value `Completed`; no C-044 literal "
                "`- **User waiver**:` ruling naming this feature exists on both "
                "carriers (%s code segment and %s `## Latest Review`)"
                % (_rel_path(repo, spec_dir / "review.md"),
                   _rel_path(repo, status["detail_path"])),
                "record the user's literal `- **User waiver**:` line naming this feature "
                "on both carriers, or keep the row out of the archive; seal does not "
                "accept `Completed` as a from state",
                "rerun the archive lane after the ruling is recorded")])

    return verdict(
        detail_status, False, "not-sealed", "/speckit.seal", EXIT_REFUSED,
        [_condition(
            "not-sealed",
            "the claimed status pair reads %r; only a `Sealed` spec is admitted to "
            "archive" % detail_status,
            "run /speckit.seal on this spec, or keep it out of the archive",
            "rerun the archive lane once the status pair reads Sealed")])


# ---------------------------------------------------------------------------
# archive-plan — preconditions, classification and the manifest candidate
# (100 C-102…C-104, C-201…C-212, C-301…C-311)
# ---------------------------------------------------------------------------

def _archive_plan_payload(spec_dir: Path, verdict: str, exit_code: int,
                          conditions=(), action: str = "archive-plan") -> Dict[str, Any]:
    payload = _payload(action, spec_dir, verdict, exit_code, conditions)
    payload["outcome"] = None
    payload["archive"] = {
        "moves": [],
        "manifest": None,
        "merge_amendments": [],
        "unresolved_before": None,
        "unresolved_after": None,
        "unclassified": None,
        "basis": None,
    }
    return payload


def _archive_refusal_state(conditions) -> Dict[str, Any]:
    codes = [condition["code"] for condition in conditions]
    exit_code = (EXIT_INPUT_ERROR if any(code in ARCHIVE_ERROR_CODES for code in codes)
                 else EXIT_REFUSED)
    return {"kind": "error" if exit_code == EXIT_INPUT_ERROR else "refused",
            "exit_code": exit_code, "conditions": conditions}


def _git_head(repo: Path) -> Optional[str]:
    proc = _run_git(repo, ["rev-parse", "HEAD"])
    value = proc.stdout.strip() if proc.returncode == 0 else ""
    return value if ARCHIVE_HEX_RE.match(value) else None


def _load_merge_document(spec_dir: Path) -> Dict[str, Any]:
    path = spec_dir / MANIFEST_NAME
    if not path.is_file():
        raise ArchiveManifestError(
            "merge-manifest-missing",
            "%s is absent; archive has no merge state to read" % MANIFEST_NAME)
    try:
        document = json.loads(_read_text(path))
    except ValueError as exc:
        raise ArchiveManifestError(
            "merge-manifest-invalid", "%s is unparsable: %s" % (MANIFEST_NAME, exc))
    if not isinstance(document, dict):
        raise ArchiveManifestError(
            "merge-manifest-invalid", "%s does not carry a JSON object" % MANIFEST_NAME)
    settings = document.get("merge")
    status = settings.get("status") if isinstance(settings, dict) else None
    if status not in ("merged", "not-applicable"):
        raise ArchiveManifestError(
            "merge-manifest-invalid",
            "%s merge.status reads %r; merged/not-applicable is the closed input set"
            % (MANIFEST_NAME, status))
    if not isinstance(document.get("slices"), list):
        raise ArchiveManifestError(
            "merge-manifest-invalid", "%s slices is not a list" % MANIFEST_NAME)
    if not isinstance(document.get("conflicts", []), list):
        raise ArchiveManifestError(
            "merge-manifest-invalid", "%s conflicts is not a list" % MANIFEST_NAME)
    return document


def _merge_recorded_slices(document: Dict[str, Any]):
    recorded = []
    for position, entry in enumerate(document.get("slices") or [], 1):
        if not isinstance(entry, dict) or not isinstance(entry.get("slug"), str) \
                or not entry["slug"]:
            raise ArchiveManifestError(
                "merge-manifest-invalid",
                "%s slices[%d] carries no usable slug" % (MANIFEST_NAME, position))
        recorded.append((entry["slug"], entry.get("order")))
    return recorded


def _archive_slice_rel(slug: str) -> str:
    return ".specify/specs/%s" % slug


def _archive_destination_rel(parent_slug: str, slug: str) -> str:
    return ".specify/specs/%s/%s/%s" % (parent_slug, ARCHIVE_SLICES_DIR, slug)


def _archive_side_presence(repo: Path, spec_dir: Path, recorded) -> Dict[str, str]:
    presence = {}
    for slug, _order in recorded:
        source = (repo / _archive_slice_rel(slug)).is_dir()
        destination = (repo / _archive_destination_rel(spec_dir.name, slug)).is_dir()
        if source and destination:
            presence[slug] = "both"
        elif source:
            presence[slug] = "source"
        elif destination:
            presence[slug] = "destination"
        else:
            presence[slug] = "missing"
    return presence


def _archive_dirty_paths(repo: Path, spec_dir: Path, recorded):
    pathspecs = [_rel_path(repo, spec_dir)]
    for slug, _order in recorded:
        pathspecs.append(_archive_slice_rel(slug))
    pathspecs.extend([
        ".specify/register.md", ".specify/glossary.md",
        ".specify/instructions.md", ".specify/features.md", ".specify/features",
        ".specify/memory", ".specify/history", "shared", ".specify/shared", "tests",
    ])
    proc = _run_git(repo, ["status", "--porcelain", "--"] + pathspecs)
    if proc.returncode != 0:
        return None
    dirty = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        entry = line[3:] if len(line) >= 3 else line.strip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry.rsplit("/", 1)[-1] == ARCHIVE_MANIFEST_NAME:
            continue
        dirty.append(entry)
    return dirty


def _archive_slice_files(directory: Path) -> list:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            rows.append({"path": path.relative_to(directory).as_posix(),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return rows


def _archive_runtime_rows(repo: Path, spec_dir: Path, slugs) -> list:
    state_root = repo / ".specify" / "state"
    carriers = [".specify/state/%s.md" % spec_dir.name] + [
        ".specify/state/%s.md" % slug for slug in slugs]
    rows = []
    for carrier in carriers:
        path = repo / carrier
        if not state_root.is_dir() or not path.is_file():
            rows.append({
                "carrier": carrier, "status": "absent",
                "reason": "the state root or the record is absent in this tree",
                "updates": [],
            })
            continue
        updates = []
        for line_no, line in enumerate(_read_text(path).splitlines(), 1):
            hits = find_reference_hits(line, slugs, parent_slug=spec_dir.name,
                                       carrier_rel=carrier)
            if hits:
                updates.append({"line": line_no, "before": line,
                                "after": rewrite_line(line, hits)})
        rows.append({"carrier": carrier, "status": "runtime-updated",
                     "reason": None, "updates": updates})
    return rows


def _merge_json_value_hits(line: str, slugs, parent_slug: str) -> list:
    """C-301: only whole path-form string values in the merge manifest are live."""
    hits = []
    for match in re.finditer(r'"((?:[^"\\]|\\.)*)"', line):
        value = match.group(1)
        for slug in sorted(slugs, key=len, reverse=True):
            frm = _archive_slice_rel(slug)
            if value == frm or value.startswith(frm + "/"):
                to = _archive_destination_rel(parent_slug, slug)
                hits.append({
                    "slug": slug, "form": "F1",
                    "start": match.start(1), "end": match.end(1),
                    "replacement": to + value[len(frm):],
                })
                break
        else:
            for slug in sorted(slugs, key=len, reverse=True):
                if value.startswith(slug + "/"):
                    to = _archive_destination_rel(parent_slug, slug)
                    hits.append({
                        "slug": slug, "form": "F2",
                        "start": match.start(1), "end": match.end(1),
                        "replacement": to + "/" + value[len(slug) + 1:],
                    })
                    break
    return sorted(hits, key=lambda hit: hit["start"])


def _archive_scan_files(repo: Path, spec_dir: Path, ordered) -> list:
    files = {}
    for path in spec_dir.rglob("*"):
        if path.is_file():
            files[_rel_path(repo, path)] = path
    for item in ordered:
        for path in item["path"].rglob("*"):
            if path.is_file():
                files[_rel_path(repo, path)] = path
    for rel in (".specify/register.md", ".specify/features.md",
                ".specify/glossary.md", ".specify/instructions.md"):
        if (repo / rel).is_file():
            files[rel] = repo / rel
    for rel in (".specify/features", ".specify/memory", ".specify/history",
                "shared", ".specify/shared", "tests"):
        root = repo / rel
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file():
                    files[_rel_path(repo, path)] = path
    return [(rel, files[rel]) for rel in sorted(files)]


def _archive_reference_scan(repo: Path, spec_dir: Path, ordered):
    parent = spec_dir.name
    slugs = [item["slug"] for item in ordered]
    rows, findings = [], []
    for rel, path in _archive_scan_files(repo, spec_dir, ordered):
        kind = archive_carrier_kind(rel, parent, slugs)
        if kind in (None, "excluded"):
            continue
        raw = path.read_bytes()
        if b"\x00" in raw:
            continue
        lines = raw.decode("utf-8", errors="replace").splitlines()
        covered = set()
        for line_no, line in enumerate(lines, 1):
            if kind == "merge-json":
                hits = _merge_json_value_hits(line, slugs, parent)
                if not hits:
                    continue
                rows.append({
                    "carrier": rel, "line": line_no, "before": line,
                    "after": rewrite_line(line, hits), "kind": "live-rewrite",
                })
                covered.update(hit["slug"] for hit in hits)
                continue
            hits = find_reference_hits(
                line, slugs, parent_slug=parent, carrier_rel=rel,
                tests_carrier=rel.startswith("tests/"))
            loose = loose_source_hits(line, slugs, hits=hits)
            if kind == "unclassified":
                forms = ([hit["form"] for hit in loose]
                         or [hit["form"] for hit in hits])
                if forms:
                    findings.append({"carrier": rel, "line": line_no,
                                     "forms": forms})
                continue
            if not hits and not loose:
                continue
            live = kind == "live" or (
                kind == "mixed" and mixed_section_kind(lines, line_no) == "live")
            if live and loose:
                findings.append({"carrier": rel, "line": line_no,
                                 "forms": [hit["form"] for hit in loose]})
                continue
            rows.append({
                "carrier": rel, "line": line_no, "before": line,
                "after": rewrite_line(line, hits) if live and hits else line,
                "kind": "live-rewrite" if live and hits else "dated-preserved",
            })
            covered.update(hit["slug"] for hit in hits)
            covered.update(hit["slug"] for hit in loose)
        if kind == "merge-json":
            continue
        if kind == "unclassified":
            continue
        joined = "".join(line.strip() for line in lines)
        for slug in slugs:
            needle = _archive_slice_rel(slug)
            if needle not in joined or slug in covered:
                continue
            if kind == "dated":
                start = _joined_needle_line(lines, needle)
                first = lines[start - 1]
                rows.append({
                    "carrier": rel, "line": start, "before": first,
                    "after": first, "kind": "dated-preserved",
                })
            else:
                findings.append({"carrier": rel, "line": 1,
                                 "forms": ["cross-line: " + needle]})
    rows.sort(key=lambda row: (row["carrier"], row["line"]))
    return rows, findings


def _dated_prefix_resolves(repo: Path, slug: str, slices) -> bool:
    """C-307(b): a dated row's old prefix maps onto an existing archived path.

    The judgment lands on the `to` prefix layer, so a dated record naming a
    tail file that never existed stays readable through the mapping.
    """
    for item in slices:
        if item["slug"] == slug:
            return _projected_path_exists(repo, item["to"], slices)
    return False


def _archive_unresolved(repo: Path, spec_dir: Path, ordered, rows) -> list:
    slugs = [item["slug"] for item in ordered]
    pairs = [{"slug": item["slug"],
              "from": _archive_slice_rel(item["slug"]),
              "to": _archive_destination_rel(spec_dir.name, item["slug"])}
             for item in ordered]
    unresolved = []
    for row in rows:
        hits = find_reference_hits(
            row["before"], slugs, parent_slug=spec_dir.name,
            carrier_rel=row["carrier"],
            tests_carrier=row["carrier"].startswith("tests/"))
        dated = row["kind"] == "dated-preserved"
        for hit in hits:
            tail = _reference_tail(row["before"], hit["end"])
            target = _hit_target(hit, spec_dir.name, tail)
            if _projected_path_exists(repo, target, pairs):
                continue
            if dated and _dated_prefix_resolves(repo, hit["slug"], pairs):
                continue
            unresolved.append({"carrier": row["carrier"],
                               "line": row["line"], "target": target})
    return unresolved


def _archive_manifest_candidate(repo: Path, spec_dir: Path, ordered, merge_doc,
                                rows, runtime, unresolved_before,
                                unresolved_after, head: str):
    slices = []
    for item in ordered:
        pointer_line = None
        for line_no, line in enumerate(item["text"].splitlines(), 1):
            if line.startswith("**Merged into**:"):
                pointer_line = line_no
                break
        if pointer_line is None:
            raise ValueError(
                "slice %s carries no `**Merged into**` line; merge-apply owns it"
                % item["slug"])
        files = _archive_slice_files(item["path"])
        slices.append({
            "slug": item["slug"],
            "from": _archive_slice_rel(item["slug"]),
            "to": _archive_destination_rel(spec_dir.name, item["slug"]),
            "order": item["order"],
            "file_count": len(files),
            "files": files,
            "merged_into_pointer": {
                "path": _archive_destination_rel(spec_dir.name, item["slug"])
                        + "/requirements.md",
                "line": pointer_line,
            },
        })
    pairs = [{"slug": item["slug"], "from": _archive_slice_rel(item["slug"]),
              "to": _archive_destination_rel(spec_dir.name, item["slug"])}
             for item in ordered]
    amended = amended_merge_document(merge_doc, pairs)
    basis = ordered[0]["order_basis"]
    source = ordered[0]["order_source"] if basis == "split-record" \
        else "directory-name-order"
    live = sum(1 for row in rows if row["kind"] == "live-rewrite")
    dated = sum(1 for row in rows if row["kind"] == "dated-preserved")
    document = {
        "schema_version": 1,
        "spec": spec_dir.name,
        "spec_path": ".specify/specs/%s" % spec_dir.name,
        "generated_by": {
            "engine": ENGINE_NAME,
            "version": _engine_version(),
            "command": "%s --action archive-apply --spec-dir .specify/specs/%s"
                       % (ENGINE_NAME, spec_dir.name),
        },
        "pinned_commit": head,
        "order_basis": basis,
        "order_source": source,
        "slices": slices,
        "references": {"rows": rows, "runtime": runtime},
        "merge_manifest": {
            "path": MANIFEST_NAME,
            "digest_before": amended["digest_before"],
            "digest_after": amended["digest_after"],
        },
        "checks": {
            "preconditions": {
                "merge_status": "merged",
                "open_conflicts": 0,
                "slices_closed": True,
                "dirty_spec_tree": False,
                "side_presence": {entry["slug"]: "source" for entry in slices},
            },
            "moved_files": sum(entry["file_count"] for entry in slices),
            "live_rewrite": live,
            "dated_preserved": dated,
            "unclassified": 0,
            "unresolved_before": unresolved_before,
            "unresolved_after": unresolved_after,
            "runtime_carriers": len(runtime),
            "files_match": True,
        },
    }
    document["digest"] = archive_manifest_digest(document)
    return document, amended["amendments"]


def _archive_plan_state(repo: Path, spec_dir: Path) -> Dict[str, Any]:
    """C-102/C-104/C-105/C-108: the read-only plan both archive actions recompute.

    `archive-plan` reports it; `archive-apply` runs the same computation as its
    read-only stage and writes only when it returns `would-archive`.
    """
    git_check = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    head = _git_head(repo)
    if git_check.returncode != 0 or git_check.stdout.strip() != "true" or head is None:
        return _archive_refusal_state([_condition(
            "not-a-git-tree",
            "archive requires a git work tree with a HEAD commit; %s does not "
            "provide one" % repo,
            "run the archive action inside the repository work tree (never a "
            "plain `mv`)",
            "rerun the same archive action from the git work tree")])

    archive_doc = _read_archive_manifest(spec_dir)
    if archive_doc is not None:
        _archived_slice_records(repo, spec_dir, archive_doc)
        return {"kind": "already-archived", "document": archive_doc, "head": head}

    merge_doc = _load_merge_document(spec_dir)
    status = merge_doc["merge"]["status"]
    if status == "not-applicable":
        return {"kind": "not-applicable",
                "basis": (merge_doc["merge"].get("basis")
                          or "the merge manifest records an empty slice set"),
                "head": head}
    recorded = _merge_recorded_slices(merge_doc)
    if not recorded:
        return {"kind": "not-applicable",
                "basis": "the merge manifest records an empty slice set",
                "head": head}

    presence = _archive_side_presence(repo, spec_dir, recorded)
    conditions = []
    for slug, state in presence.items():
        if state == "both":
            conditions.append(_condition(
                "destination-exists",
                "slice %s exists at both %s and %s"
                % (slug, _archive_slice_rel(slug),
                   _archive_destination_rel(spec_dir.name, slug)),
                "remove one side after inspecting it; archive never picks a side",
                "rerun archive-plan once exactly one side remains"))
        elif state == "missing":
            conditions.append(_condition(
                "slice-missing",
                "slice %s is absent at both %s and %s"
                % (slug, _archive_slice_rel(slug),
                   _archive_destination_rel(spec_dir.name, slug)),
                "restore the slice tree or repair merge-manifest.json",
                "rerun archive-plan after the slice set agrees with the tree"))
    states = set(presence.values())
    if states == {"source", "destination"}:
        conditions.append(_condition(
            "partial-archive",
            "the slice set is split across the two sides: %s"
            % ", ".join("%s=%s" % pair for pair in sorted(presence.items())),
            "finish or reverse the interrupted archive; archive never guesses",
            "rerun archive-plan once all slices are on the same side"))
    elif states == {"destination"}:
        conditions.append(_condition(
            "archive-drift",
            "every slice is at its destination but %s is absent"
            % ARCHIVE_MANIFEST_NAME,
            "restore the archive manifest from history or complete the interrupted "
            "move deliberately",
            "rerun archive-plan after the record exists and agrees with the tree"))

    open_conflicts = [item for item in merge_doc.get("conflicts") or []
                      if isinstance(item, dict) and item.get("status") == "open"]
    for item in open_conflicts:
        conditions.append(_condition(
            "conflict-open",
            "%s records an open conflict: %s"
            % (MANIFEST_NAME,
               item.get("id") or json.dumps(item, ensure_ascii=False, sort_keys=True)),
            "resolve the conflict through the merge owner",
            "rerun archive-plan after the conflict is closed"))

    views = []
    for slug, _order in recorded:
        source = repo / _archive_slice_rel(slug)
        destination = repo / _archive_destination_rel(spec_dir.name, slug)
        path = source if source.is_dir() else (
            destination if destination.is_dir() else None)
        if path is not None:
            views.append({"slug": slug, "path": path})
    unclosed = _unclosed_slice_rows(repo, views)
    for path_rel, line_no, task_id, task_state in unclosed:
        conditions.append(_condition(
            "slice-unclosed",
            "%s:%d %s is not closed (state `- [%s]`)"
            % (path_rel, line_no, task_id, task_state),
            "close the slice task, or record its `deferred_tasks=` entry in the "
            "slice verification.md",
            "rerun archive-plan after the slice is closed"))

    dirty = _archive_dirty_paths(repo, spec_dir, recorded)
    if dirty is None:
        conditions.append(_condition(
            "not-a-git-tree",
            "`git status --porcelain` cannot answer for %s" % repo,
            "run archive-plan inside the repository work tree",
            "rerun archive-plan from the git work tree"))
    else:
        for path_rel in dirty:
            conditions.append(_condition(
                "dirty-spec-tree",
                "uncommitted change outside the archive batch: %s" % path_rel,
                "commit or revert the change, then rerun; the archive batch starts "
                "from a settled tree",
                "rerun archive-plan on the settled tree"))

    if conditions:
        return _archive_refusal_state(conditions)

    slices, _excluded = _discover_slices(spec_dir, repo)
    ordered = _derive_order(repo, spec_dir.name, slices)
    recorded_slugs = [slug for slug, _order in recorded]
    if [item["slug"] for item in ordered] != recorded_slugs:
        return _archive_refusal_state([_condition(
            "merge-manifest-invalid",
            "%s records slices %r while the tree scan reads %r"
            % (MANIFEST_NAME, recorded_slugs,
               [item["slug"] for item in ordered]),
            "repair the merge manifest or restore the slice directories",
            "rerun archive once the record and the tree agree")])
    for position, (_slug, order) in enumerate(recorded):
        if _is_int(order) and order != position + 1:
            return _archive_refusal_state([_condition(
                "merge-manifest-invalid",
                "%s records order %r for %s, but the derived order is %d"
                % (MANIFEST_NAME, order, ordered[position]["slug"], position + 1),
                "repair the merge manifest's slice order",
                "rerun archive once the record and the split record agree")])

    rows, findings = _archive_reference_scan(repo, spec_dir, ordered)
    conditions = [
        _condition(
            "unclassified-reference",
            "%s:%d carries a source-path shape outside the declared F1/F2/F3 "
            "forms and carrier roster (%s)"
            % (finding["carrier"], finding["line"], ", ".join(finding["forms"])),
            "rewrite the line into a declared carrier/form or fix the reference; "
            "the classifier never guesses",
            "rerun archive-plan after the line is classified")
        for finding in findings
    ]
    unresolved = _archive_unresolved(repo, spec_dir, ordered, rows)
    if unresolved:
        conditions.append(_condition(
            "unresolved-references",
            "%d reference target(s) will not exist after the move: %s"
            % (len(unresolved),
               "; ".join("%s:%d -> %s" % (item["carrier"], item["line"],
                                          item["target"])
                         for item in unresolved)),
            "fix the dangling reference or add the missing target",
            "rerun archive-plan after every target resolves"))
    if conditions:
        return _archive_refusal_state(conditions)

    runtime = _archive_runtime_rows(
        repo, spec_dir, [item["slug"] for item in ordered])
    document, amendments = _archive_manifest_candidate(
        repo, spec_dir, ordered, merge_doc, rows, runtime, 0, 0, head)
    validate_archive_manifest(document, spec_dir.name)
    return {"kind": "would-archive", "document": document,
            "amendments": amendments, "merge_doc": merge_doc,
            "head": head, "writes": []}


def _archive_report(action: str, spec_dir: Path,
                    state: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Turn one read-only state into the closed verdict/outcome payload (C-103)."""
    kind = state["kind"]
    if kind in ("refused", "error"):
        return _archive_plan_payload(spec_dir, kind, state["exit_code"],
                                     state["conditions"], action=action), \
            state["exit_code"]
    payload = _archive_plan_payload(spec_dir, "ok", EXIT_OK, (), action=action)
    payload["outcome"] = kind
    archive = payload["archive"]
    if kind == "not-applicable":
        archive["basis"] = state["basis"]
        return payload, EXIT_OK
    document = state["document"]
    checks = document["checks"]
    archive.update({
        "manifest": document,
        "unresolved_before": (checks["unresolved_after"]
                              if kind == "already-archived"
                              else checks["unresolved_before"]),
        "unresolved_after": checks["unresolved_after"],
        "unclassified": checks["unclassified"],
    })
    if kind == "would-archive":
        archive["moves"] = [{"slug": entry["slug"], "from": entry["from"],
                             "to": entry["to"], "order": entry["order"],
                             "file_count": entry["file_count"]}
                            for entry in document["slices"]]
        archive["merge_amendments"] = state["amendments"]
    return payload, EXIT_OK


def _archive_serialized(document: Dict[str, Any]) -> str:
    """C-202: the one canonical serialization for the record and its payload."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _archive_move(repo: Path, source_rel: str, destination_rel: str) -> None:
    proc = _run_git(repo, ["mv", "--", source_rel, destination_rel])
    if proc.returncode != 0:
        raise OSError("git mv %s -> %s failed: %s"
                      % (source_rel, destination_rel, _first_line(proc.stderr)))


def _archive_write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _archive_line_text(text: str, updates, carrier: str) -> str:
    """C-308: deterministic whole-line replacement against the planned text."""
    lines = text.splitlines()
    for update in sorted(updates, key=lambda item: item["line"]):
        index = update["line"] - 1
        if index < 0 or index >= len(lines) or lines[index] != update["before"]:
            raise OSError(
                "%s:%d no longer carries the planned line; the tree moved "
                "under the batch" % (carrier, update["line"]))
        lines[index] = update["after"]
    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + trailing


def _archive_restore(repo: Path, document, journal) -> list:
    """C-108: restore the batch by its original bytes; report what failed."""
    failures = []
    manifest_path = journal.get("manifest")
    if manifest_path is not None and manifest_path.exists():
        try:
            manifest_path.unlink()
        except OSError as exc:
            failures.append("remove %s: %s" % (manifest_path, exc))
    for source_rel, destination_rel in reversed(journal["moved"]):
        proc = _run_git(repo, ["mv", "--", destination_rel, source_rel])
        if proc.returncode != 0:
            failures.append("inverse git mv %s -> %s: %s"
                            % (destination_rel, source_rel,
                               _first_line(proc.stderr)))
    for carrier, original in journal["files"].items():
        try:
            (repo / carrier).write_bytes(original)
        except OSError as exc:
            failures.append("restore %s: %s" % (carrier, exc))
    created = journal.get("created_dir")
    if created is not None and created.is_dir() and not any(created.iterdir()):
        try:
            created.rmdir()
        except OSError as exc:
            failures.append("remove %s: %s" % (created, exc))
    return failures


class _ArchiveMirrorMismatch(OSError):
    """C-310: the source/mirror pair stopped matching inside one batch."""


def _archive_apply_batch(repo: Path, spec_dir: Path,
                         state: Dict[str, Any]) -> Optional[tuple]:
    """C-106/C-108/C-308…C-311: one write batch, restored byte for byte."""
    document = state["document"]
    pairs = [{"slug": entry["slug"], "from": entry["from"], "to": entry["to"]}
             for entry in document["slices"]]
    amendment = amended_merge_document(state["merge_doc"], pairs)
    journal = {"moved": [], "created_dir": None, "files": {}, "manifest": None}
    written: list = []
    dated = {row["carrier"] for row in document["references"]["rows"]
             if row["kind"] == "dated-preserved"}
    merge_path = spec_dir / MANIFEST_NAME
    merge_rel = _rel_path(repo, merge_path)
    live_rows: Dict[str, list] = {}
    for row in document["references"]["rows"]:
        if row["kind"] == "live-rewrite" and row["carrier"] != merge_rel:
            live_rows.setdefault(row["carrier"], []).append(row)
    moved_prefixes = tuple(entry["from"] + "/" for entry in document["slices"])
    dated = {carrier for carrier in dated
             if not carrier.startswith(moved_prefixes)}
    pure_dated = sorted(dated - set(live_rows))
    mixed = sorted(dated & set(live_rows))
    dated_before = {carrier: hashlib.sha256((repo / carrier).read_bytes()).hexdigest()
                    for carrier in pure_dated if (repo / carrier).is_file()}
    mixed_before = {carrier: mixed_dated_sections((repo / carrier).read_bytes())
                    for carrier in mixed if (repo / carrier).is_file()}
    slices_dir = spec_dir / ARCHIVE_SLICES_DIR
    failure = None
    try:
        if not slices_dir.is_dir():
            slices_dir.mkdir(parents=True)
            journal["created_dir"] = slices_dir
        for entry in document["slices"]:
            source = repo / entry["from"]
            for row in entry["files"]:
                journal["files"].setdefault(
                    entry["from"] + "/" + row["path"],
                    (source / row["path"]).read_bytes())
            _archive_move(repo, entry["from"], entry["to"])
            journal["moved"].append((entry["from"], entry["to"]))
        for carrier in sorted(live_rows):
            path = repo / carrier
            original = path.read_bytes()
            journal["files"].setdefault(carrier, original)
            _archive_write_text(
                path, _archive_line_text(original.decode("utf-8"),
                                         live_rows[carrier], carrier))
            written.append(carrier)
        for row in document["references"]["runtime"]:
            if row["status"] != "runtime-updated" or not row["updates"]:
                continue
            path = repo / row["carrier"]
            original = path.read_bytes()
            journal["files"].setdefault(row["carrier"], original)
            _archive_write_text(
                path, _archive_line_text(original.decode("utf-8"),
                                         row["updates"], row["carrier"]))
            written.append(row["carrier"])
        journal["files"].setdefault(merge_rel, merge_path.read_bytes())
        _archive_write_text(merge_path,
                            json.dumps(amendment["document"], indent=2,
                                       ensure_ascii=False) + "\n")
        written.append(merge_rel)
        for entry in document["slices"]:
            after = _archive_slice_files(repo / entry["to"])
            if after != entry["files"]:
                raise OSError(
                    "slice %s no longer matches its recorded file hashes: the "
                    "zero-loss check failed" % entry["slug"])
        for carrier, digest in dated_before.items():
            if hashlib.sha256((repo / carrier).read_bytes()).hexdigest() != digest:
                raise OSError("dated carrier %s changed during the batch" % carrier)
        for carrier, dated_region in mixed_before.items():
            if mixed_dated_sections((repo / carrier).read_bytes()) != dated_region:
                raise OSError(
                    "mixed carrier %s changed in its dated sections during the "
                    "batch" % carrier)
        for carrier in sorted(live_rows):
            if not carrier.startswith(".specify/shared/"):
                continue
            mirror = ".specify/" + carrier
            if (repo / mirror).is_file() and \
                    (repo / carrier).read_bytes() != (repo / mirror).read_bytes():
                raise _ArchiveMirrorMismatch(
                    "source/mirror pair %s does not agree after the batch"
                    % carrier)
        manifest_path = spec_dir / ARCHIVE_MANIFEST_NAME
        journal["manifest"] = manifest_path
        _archive_write_text(manifest_path, _archive_serialized(document))
        written.append(_rel_path(repo, manifest_path))
    except OSError as exc:
        failures = _archive_restore(repo, document, journal)
        detail = str(exc)
        if failures:
            detail += "; restore reported: " + "; ".join(failures)
        code = ("mirror-copy" if isinstance(exc, _ArchiveMirrorMismatch)
                else "write-failed")
        failure = (code, detail)
    state["writes"] = sorted(written)
    return failure


def action_archive_plan(args: argparse.Namespace,
                        spec_dir: Path) -> Tuple[Dict[str, Any], int]:
    """C-102…C-105 / C-301…C-307: read-only precondition, classification and preview."""
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    return _archive_report("archive-plan", spec_dir,
                           _archive_plan_state(repo, spec_dir))


def action_archive_apply(args: argparse.Namespace,
                         spec_dir: Path) -> Tuple[Dict[str, Any], int]:
    """C-105/C-106/C-108: recompute the plan, then land one restorable batch."""
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    state = _archive_plan_state(repo, spec_dir)
    if state["kind"] == "would-archive":
        failure = _archive_apply_batch(repo, spec_dir, state)
        if failure is not None:
            failure_code, failure_detail = failure
            return _archive_plan_payload(
                spec_dir, "error", EXIT_INPUT_ERROR,
                [_condition(
                    failure_code,
                    "the archive write batch stopped and was restored from its "
                    "original bytes: %s" % failure_detail,
                    "inspect the named step; the tree is archive-ready again",
                    "rerun archive-apply once the named failure is repaired")],
                action="archive-apply"), EXIT_INPUT_ERROR
    payload, code = _archive_report("archive-apply", spec_dir, state)
    if state["kind"] == "would-archive":
        payload["outcome"] = "archived"
        payload["archive"]["writes"] = state.get("writes", [])
    return payload, code


HANDLERS = {
    "merge-plan": action_merge_plan,
    "merge-apply": action_merge_apply,
    "seal": action_seal,
    "archive-gate": action_archive_gate,
    "archive-plan": action_archive_plan,
    "archive-apply": action_archive_apply,
}


# ---------------------------------------------------------------------------
# CLI surface (C-003 / C-004) and dispatch
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=ENGINE_NAME,
        description="Seal engine for /speckit.seal: merge-back, seal judgment, "
                    "archive admission and slice-archive planning/apply.",
    )
    _sig_configure(
        parser,
        effects="merge-plan, archive-gate and archive-plan write nothing; merge-apply "
                "and seal write only within the allowlisted paths (the parent spec "
                "directory, one slice requirements.md marker line and recorded "
                "factory-doc resolutions); archive-apply carries the slice-archive "
                "write batch; a flag-only invocation writes nothing",
        codes="0 success or idempotent; 1 a precondition refused; 2 an input or "
              "environment error",
    )
    parser.add_argument("--action", required=True, choices=ACTIONS,
                        help="one of the six closed actions")
    parser.add_argument("--spec-dir", required=True,
                        help="target spec directory (required, no default)")
    parser.add_argument("--repo", default=None,
                        help="repository root for state and registry lookups "
                             "(default: the invocation cwd)")
    parser.add_argument("--feature-detail", default=None,
                        help="override the feature-detail carrier path (test fixtures only)")
    parser.add_argument("--feature-registry", default=None,
                        help="override the feature-registry path (test fixtures only)")
    parser.add_argument("--json", action="store_true",
                        help="emit one stable JSON payload instead of the human rendering")
    _sig_add_version(parser)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    line = list(sys.argv[1:] if argv is None else argv)
    _sig_guard(line, declared=DECLARED_OPTIONS)
    parser = build_parser()
    args = parser.parse_args(line)

    if args.action in WRITE_ACTIONS and is_mirror_copy():
        payload = _payload(
            args.action, None, "error", EXIT_INPUT_ERROR,
            [_condition(
                MIRROR_CODE,
                "this engine is the .specify/scripts/python/ mirror copy; write actions "
                "MUST run from the framework source to keep the pair byte-identical",
                "run .specify/scripts/python/seal-utils.py from the framework source tree",
                "rerun the same command against the framework source copy",
            )],
        )
        render(payload, args.json)
        return EXIT_INPUT_ERROR

    spec_dir = resolve_spec_dir(args.spec_dir)
    if spec_dir is None:
        payload = _payload(
            args.action, None, "error", EXIT_INPUT_ERROR,
            [_condition(
                SPEC_DIR_CODE,
                "not a spec directory (missing, or carries no %s): %s"
                % (SPEC_CONTRACT_FILE, args.spec_dir),
                "pass --spec-dir pointing at a directory that contains %s"
                % SPEC_CONTRACT_FILE,
                "rerun the same command with a corrected --spec-dir",
            )],
        )
        render(payload, args.json)
        return EXIT_INPUT_ERROR

    try:
        payload, code = HANDLERS[args.action](args, spec_dir)
    except ArchiveManifestError as exc:
        payload = _archive_manifest_error(args.action, spec_dir, exc)
        code = EXIT_INPUT_ERROR
    except (OSError, ValueError, StopIteration) as exc:
        payload = _payload(
            args.action, spec_dir, "error", EXIT_INPUT_ERROR,
            [_condition(
                "engine-input-error",
                "the %s judgment cannot be derived from this tree: %s"
                % (args.action, exc),
                "repair the named input (spec tree, status carriers or merge record)",
                "rerun the same command after the input is repaired",
            )],
        )
        code = EXIT_INPUT_ERROR
    render(payload, args.json)
    return code


if __name__ == "__main__":
    sys.exit(main())
