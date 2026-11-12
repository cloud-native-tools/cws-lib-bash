#!/usr/bin/env python3
"""non-disposable-check.py — the read-only engine that says which remembered things are
"stale / useless / deferred" and what may be disposed of them.

Owner of the rule: `.specify/shared/definitions/non-disposable-definitions.md` — the eight-member
closed detection-class set (§ Detection Categories), the four-value disposition set and the
exemption expiry model (§ Disposition Set / § Exemption), the two bridge tables
(§ Disposition Bridge), the review surface (§ Review Surface), the supersede and renumber
protocols, the report entry and its envelope (§ Report Entry / § Report Envelope), the
status-readability contradiction table (§ Status Readability) and the capture rule.

Owner of the review-surface members and their order: the declaration-layer fact
`.specify/shared/declarations/facts/non-disposable-review-surface.yaml` (`kind: closed-set`), read
here through the single read entry `.specify/scripts/python/declaration_reader.py` — never inlined.

Owner of the closure verdict and its reason codes: `.specify/shared/workflow/acceptance-hardening.md`
§ Closure Verdict, realised by `.specify/scripts/python/closure-acceptance-check.py`. This engine
**consumes** that verdict as a subprocess and never re-derives it (C-201 / C-207).

Calling surface (contract `contracts/detection-engine-cli.contract.md` C-603 / C-604):

  --root PATH          repository root (default: resolved from this file's own location)
  --json               machine-readable report on stdout
  --scope SHARD        judge only the candidates whose path falls in this shard; the shard id
                       is `s{index:03d}-of-{n:03d}` and `n` is the shard count of this run
  --roots              print the declared root set (path, presence, count) and stop, exit 0
  --emit-categories    print the closed class set as JSON and stop, exit 0
  --declaration PATH   override the fact file (fixtures only)
  -h, --help           usage (the parser's own body -- this engine does not hand-roll it)
  --version            one version line

  Eight argument rows, two actions (`--roots`, `--emit-categories`), and no other option: an
  unrecognised option exits 2 before any action runs. `--scope-count` is **not** a ninth row:
  C-604 owns the argument set and does not list it, `n` travels in the shard id the run
  requests (`--scope s001-of-004` names both the shard and its count), and an option outside
  the eight is rejected by C-604's own rule.

Exit codes (C-603):

  0  no findings over a stated, non-empty surface
  1  findings exist (any entry, any class, including `unevaluated` entries)
  2  argument or environment error — a missing/invalid declaration, an unresolvable root, an
     unknown option, an empty candidate set (the surface declared no candidates: that is a
     declaration defect, never a verdict, and `0` MUST NOT be reachable on it)

Read-only in every mode (C-602): nothing in the repository is written — not by `--json`, not by
`--scope`, not by `--help`, not by any error path. Stdlib only (C-601); the two sibling
modules are imported from this file's own directory, never copied.

Usage:
  python3 .specify/scripts/python/non-disposable-check.py
  python3 .specify/scripts/python/non-disposable-check.py --json
  python3 .specify/scripts/python/non-disposable-check.py --roots
  python3 .specify/scripts/python/non-disposable-check.py --emit-categories
  python3 .specify/scripts/python/non-disposable-check.py --scope s000-of-004
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

# --- the two sibling modules, imported from this file's own directory (C-601) ---------------- #
_ENGINE_DIR = Path(__file__).resolve().parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

import declaration_reader  # noqa: E402  (the declaration layer's one read entry)


def _load_sibling(filename: str, module_name: str):
    """Load a sibling engine by path.

    `renumber-utils.py` carries a hyphen, so it is not importable by name; the sibling
    pattern (`script-interface-check.py` loading `script_interface_cli.py`) is used instead.
    """
    import importlib.util

    path = _ENGINE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None, "cannot load %s" % path
    spec.loader.exec_module(module)
    return module


renumber_utils = _load_sibling("renumber-utils.py", "_non_disposable_renumber")  # noqa: E402

# --- the engine's own constants (owner: this module header) ---------------------------------- #

#: The exit codes are three-valued and mean three different things (C-603).
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_INPUT = 2

#: The review-surface fact's slug. Its members and order live in the fact, not here (C-605).
REVIEW_SURFACE_FACT = "non-disposable-review-surface"

#: The checker whose verdict this engine consumes, and the module it lives in (C-201).
CLOSURE_CHECKER = "closure-acceptance-check.py"

#: The registry a status claim is read from.
FEATURES_REL = ".specify/features.md"

#: The owner page — the class set is read from it, never from a literal here (C-101).
OWNER_PAGE_REL = ".specify/shared/definitions/non-disposable-definitions.md"

#: The state machine's values (owner: `data-model.md` § Entry State Machine).
STATES = ("open", "unevaluated", "unconfirmed", "disposed", "exempt")

#: The disposition set is NOT spelled here: it is read from the owner page (C-301). This is
#: only the ordering the report stabilises on.
DISPOSITION_ORDER = ("archive", "supersede", "correct", "exempt")

#: Claimed statuses that assert the feature is already implemented (C-202). `Sealed` asserts every
#: final-path criterion passed, so it belongs to the same family (099 plan § Disclosed Rulings 3).
COMPLETION_CLAIMS = ("Implemented", "Ready for Review", "Sealed")

#: Registry statuses that have no live spec directory of their own (C-802's named exclusion).
RELOCATED_STATUS = "Relocated"

#: The smoke field names. Read from the owner page at run time; this tuple is only the
#: fallback used when the owner page cannot be read.
SMOKE_FALLBACK = ("smoke_command", "smoke_exit_code", "smoke_evidence_path")
STATUS_ROW_RE = re.compile(r"^(SC-\d{3})_status=(\S+)\s*$", re.MULTILINE)

#: `status-claims-implemented-but-blocked` — the checker's one status-related code (C-202).
R_CLAIMED = "status-claims-implemented-but-blocked"

#: The four required exemption fields (`data-model.md` E-3 / owner page § Exemption).
EXEMPT_FIELDS = ("reason", "expiry_kind", "expiry_value", "expiry_recheck")

#: The closed three-value expiry set (`data-model.md` E-3). There is no fourth value and no
#: "permanent" — a spelling outside this tuple is an invalid exemption, not a longer one.
EXPIRY_KINDS = ("on-date", "on-condition", "on-review")

#: A bare negation is not a reason (owner page § Exemption: `N/A` / `n/a` / `none` / `-`).
BARE_NEGATIONS = ("", "-", "n/a", "na", "none", "nil", "null", "tbd", "todo")

#: `expiry_recheck`'s upper bound beyond `expiry_value`, in days (owner page § Exemption).
EXPIRY_RECHECK_CEILING_DAYS = 365

#: A constant-true predicate is an *invalid* expiry condition, never a permanent exemption
#: (`data-model.md` E-3). Matched against an `on-condition` value's predicate part.
CONSTANT_TRUE_RE = re.compile(
    r"^\s*(?:\w+\s*:\s*)?(?:true|True|TRUE|1|yes|always)\s*$")

#: Retention wording with no expiry condition is the `deferral-marker` class (C-105 / C-106).
#: The three readings the owner page § Detection Categories names ("暂时保留" / "留待下轮" /
#: "以后再处理" and their English counterparts) come first; the rest are spellings of the
#: same statement. A sentence that *quotes* the wording as a forbidden form (an `MUST NOT`
#: or `never` clause) records the rule rather than deferring anything, and is not a reading.
DEFERRAL_RE = re.compile(
    r"(暂时保留|暂时不删|暂不删除|留待下轮|留到下一轮|保留到下一轮|以后再处理|稍后处理"
    r"|待后续处理|待后续再处理|先留着"
    r"|\bfor now\b|\bkeep for now\b|\bleave for later\b|\bTODO later\b"
    r"|\btemporarily kept\b|\bdeferred to (?:a )?(?:later|next) round\b)",
    re.IGNORECASE,
)
#: A line that names the retention form as a prohibition is a *rule about* the form.
DEFERRAL_QUOTED_RE = re.compile(
    r"(MUST NOT|MUST NEVER|must not|is not a reason|不是理由|禁止|不得|严禁|never\b)",
    re.IGNORECASE)
#: A line inside a fenced block is a sample, a template or a transcript — never a statement
#: this tree makes. The fence scan below excludes it.
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
EXPIRY_VALUE_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")
EXPIRY_FIELD_RE = re.compile(r"\bexpiry_(kind|value|recheck)\s*[:=]", re.IGNORECASE)

#: A line that states a total contradicting an arithmetic identity on the same line, or the
#: `a + b != c` form itself (corpus E4's shape: `367 + 737 = 1104 ≠ 751`).
SELF_REFUTED_RE = re.compile(r"(?:≠|!=)\s*(\d+)")

#: A closed-set identity claim: one equality whose left side is a sum (C-204).
#: The whole chain is read, not just the first two addends: `9 + 15 + 8 = 62` is a *claim*
#: and `9 + 15 = 62` is the truncated reading of it, which would report an arithmetically
#: correct partition as false. At least two addends and an equality are required.
IDENTITY_RE = re.compile(
    r"(?<![\w.])(\d+(?:\s*\+\s*\d+)+)\s*={1,2}\s*(\d+)(?![\w.])")

#: A path token a body may reference: backticked, repo-relative.
PATH_TOKEN_RE = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)(?::(\d+))?`")

#: Header bindings whose number must follow the directory's own (C-504).
FEATURE_HEADER_RE = re.compile(r"^\*\*Feature\*\*:\s*(\d{3})", re.MULTILINE)
FEATURE_ID_RE = re.compile(r"^\*\*Feature ID\*\*:\s*(\d{3})", re.MULTILINE)
TASK_HEADER_RE = re.compile(r"^\*\*(?:Requirement ID|Related Feature)\*\*:\s*(\d{3})", re.MULTILINE)

#: The roots a path token may be repo-relative to. A token outside this set is prose, not a
#: reference, and is never judged (C-103: only a resolvable reference is a reading).
PATH_PREFIXES = (".specify/", ".specify/shared/", ".specify/scripts/", ".specify/templates/", "skills/", "tests/",
                 "src/", "docs/", "agents/")


class InputError(Exception):
    """An argument or environment defect — always exit 2, never a finding (C-603)."""


# ------------------------------------------------------------------------------------------- #
# text and path helpers
# ------------------------------------------------------------------------------------------- #
def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_root(explicit: str = "") -> Path:
    """The repository root: `--root`, else the nearest ancestor holding a declarations layer.

    Through the `.specify/scripts/python/` mirror the layer resolves to
    `<repo>/.specify/shared/declarations`, whose grandparent is `<repo>/.specify`; the
    repository root is one level above that, never `.specify` itself (C-602).
    """
    if explicit:
        root = Path(explicit).resolve()
        if not root.is_dir():
            raise InputError("--root is not a directory: %s" % explicit)
        return root
    start = Path(__file__).resolve().parent
    try:
        root = declaration_reader.find_repo(start)
    except declaration_reader.DeclarationError:
        root = start.parents[1]
    # C-602: through the `.specify/scripts/python/` mirror the layer resolves under
    # `.specify/`, so `find_repo` answers the mirror directory itself. The repository root is
    # its parent -- `.specify` is never the root, or every declared root would resolve one
    # level too deep and report the whole surface absent.
    if root.name == ".specify":
        root = root.parent
    return root


def fact_path(root: Path) -> str:
    for base in (root / "shared" / "declarations", root / ".specify" / "shared" / "declarations"):
        candidate = base / "facts" / ("%s.yaml" % REVIEW_SURFACE_FACT)
        if candidate.is_file():
            return _rel(root, candidate)
    return ".specify/shared/declarations/facts/%s.yaml" % REVIEW_SURFACE_FACT


# ------------------------------------------------------------------------------------------- #
# the declaration surface (C-605)
# ------------------------------------------------------------------------------------------- #
def load_surface(root: Path, declaration: str = ""):
    """`(roots, declaration_path, status)` — the ten roots, in declared order.

    The default read goes through the one entry (`declaration_reader.load_fact`). The
    `--declaration` override names a *fact file*, not a directory list (C-604): the file is
    parsed by the same reader's subset parser, so a fixture cannot use a grammar the layer
    itself would refuse, and its `fact:` slug is not consulted -- the override says which
    file to read, and the file's own `kind` / `statement` are judged exactly as the
    declaration's are.
    """
    if declaration:
        path = Path(declaration)
        if not path.is_file():
            raise InputError("--declaration does not exist: %s" % declaration)
        try:
            body = declaration_reader.parse_subset(_read(path), declaration)
        except declaration_reader.DeclarationError as exc:
            raise InputError("--declaration %s: %s" % (declaration, exc))
        declared_path = declaration
    else:
        try:
            fact = declaration_reader.load_fact(root, REVIEW_SURFACE_FACT)
        except declaration_reader.DeclarationError as exc:
            label = declaration_reader.absent_label(REVIEW_SURFACE_FACT) if getattr(
                exc, "template", None) else ""
            raise InputError("%s%s: %s" % (label + " " if label else "",
                                           REVIEW_SURFACE_FACT, exc))
        body = fact["body"]
        declared_path = fact_path(root)
    if not isinstance(body, dict):
        raise InputError("declaration %s: a fact declaration must be a mapping (key 'kind' "
                         "missing)" % declared_path)
    kind = str(body.get("kind", "")).strip()
    if kind != "closed-set":
        raise InputError("declaration %s: key 'kind' is %r, expected 'closed-set'"
                         % (declared_path, kind))
    statement = body.get("statement")
    if not isinstance(statement, list) or not statement:
        raise InputError("declaration %s: required key 'statement' is missing or empty"
                         % declared_path)
    # C-602: the review surface is repo-relative and stays so. `normalize_path` strips one
    # leading `.specify/` (C-057) because for *slugs* the three copies must name one object;
    # here it would turn `.specify/specs` into `specs` and point every root at a path that does
    # not exist. The declared value is used verbatim, only whitespace-trimmed.
    roots = [str(item).strip() for item in statement]
    return roots, declared_path, "ok"


def survey(root: Path, roots):
    """The per-root reading: presence, candidate count, reasons; plus the three comparisons."""
    readings, candidates, excluded, missing = [], [], [], []
    for rel in roots:
        base = root / rel
        if not base.is_dir():
            missing.append({"path": rel, "reason": "declared-but-absent"})
            excluded.append({"path": rel, "reason": "declared-but-absent"})
            readings.append({"path": rel, "present": False, "count": 0,
                             "reason": "declared-but-absent"})
            continue
        files = sorted(p for p in base.rglob("*") if p.is_file() and not p.is_symlink())
        readings.append({"path": rel, "present": True, "count": len(files)})
        for path in files:
            relpath = _rel(root, path)
            if renumber_utils._is_dated_record(relpath):
                excluded.append({"path": relpath, "reason": "dated-record"})
                continue
            candidates.append(relpath)
    declared = set(roots)
    siblings = []
    specify = root / ".specify"
    if specify.is_dir():
        for child in sorted(specify.iterdir()):
            if not child.is_dir() or child.is_symlink():
                continue
            rel = _rel(root, child)
            if rel not in declared:
                siblings.append({"path": rel, "reason": "undeclared-sibling"})
    return readings, sorted(candidates), excluded, missing, siblings


# ------------------------------------------------------------------------------------------- #
# the owner page's closed sets (C-101 / C-301) — read, never spelled a second time
# ------------------------------------------------------------------------------------------- #
def _owner_text(root: Path) -> str:
    for candidate in (root / OWNER_PAGE_REL, root / ".specify" / OWNER_PAGE_REL):
        if candidate.is_file():
            return _read(candidate)
    return ""


#: The eight ids, in the owner page's table order. This tuple is a FALLBACK, used only when
#: the owner page cannot be read at all (a fixture tree that does not ship it); the read path
#: is the authority and C-101 forbids a second class set. When the fallback is what answered,
#: `owner_classes_source` says so in the report, so a run never looks like it read an owner
#: page it did not read.
CLASS_FALLBACK = (
    "superseded-live", "multi-owner", "orphan-path", "renumber-live-binding",
    "status-unreadable", "false-closed-set", "stale-constant", "deferral-marker",
)


def owner_classes(root: Path):
    """The eight class ids, read from the owner page's § Detection Categories table."""
    text = _owner_text(root)
    start = text.find("\n## Detection Categories")
    end = text.find("\n## ", start + 1) if start >= 0 else -1
    section = text[start:end] if start >= 0 else text
    ids = []
    for line in section.splitlines():
        match = re.match(r"^\|\s*\d+\s*\|\s*`([a-z][a-z-]+)`\s*\|", line)
        if match:
            ids.append(match.group(1))
    return ids


def resolved_classes(root: Path):
    """`(class ids, source)` — the owner page when it answers, else the fallback tuple."""
    ids = owner_classes(root)
    if ids:
        return ids, OWNER_PAGE_REL
    return list(CLASS_FALLBACK), "fallback (the owner page is not readable from this root)"


def owner_classes_source(root: Path) -> str:
    return resolved_classes(root)[1]


def owner_dispositions(root: Path):
    """The four disposition values, read from the owner page's § Disposition Set table."""
    text = _owner_text(root)
    start = text.find("\n## Disposition Set")
    if start < 0:
        return []
    end = text.find("\n## ", start + 1)
    section = text[start:end if end > 0 else len(text)]
    values = []
    for line in section.splitlines():
        match = re.match(r"^\|\s*`([a-z][a-z-]+)`\s*\|", line)
        if match:
            values.append(match.group(1))
    return values


def owner_smoke_fields(root: Path):
    """The smoke field names, read from the owner page's own pointer table."""
    text = _owner_text(root)
    found = []
    for name in re.findall(r"`(smoke_[a-z_]+)`", text):
        if name not in found:
            found.append(name)
    return tuple(found) or SMOKE_FALLBACK


# ------------------------------------------------------------------------------------------- #
# the registry and the closure verdict (C-201 / C-202 / C-802)
# ------------------------------------------------------------------------------------------- #
def registry_rows(root: Path):
    """`{id, line, status, spec}` per row, with the column layout read from the header row.

    `renumber_utils.features_rows` splits on `|` **without** trimming the empty leading and
    trailing cells, so its `cells` are offset by one from the table's own header. The column
    index is therefore taken from that header row, and the cells are trimmed here; a column
    added by a later feature shifts neither the status nor the spec-path reading (C-201).
    """
    header = None
    rows = []
    for row in renumber_utils.features_rows(root):
        cells = [cell.strip() for cell in row["cells"]]
        if header is None and "Status" in cells:
            header = cells
            continue
        names = header or ["", "ID", "Name", "Description", "Status",
                           "Feature Details", "Spec Path", "Last Updated", ""]

        def cell(label):
            try:
                index = names.index(label)
            except ValueError:
                return ""
            return cells[index] if len(cells) > index else ""

        # The cells are prose: the registry spells a path as `` `path` `` and a reading of the
        # whole cell as a path would look for a directory literally named `` `path` ``. The
        # markdown code spans are the table's own emphasis, not part of the path (C-201).
        rows.append({"id": row["id"], "line": row["line"],
                     "status": cell("Status").strip("`"),
                     "spec": cell("Spec Path").strip("`")})
    return rows


def closure_verdict(root: Path, spec_dir: Path):
    """Run the checker once and read `verdict` + `reasons` out of its payload (C-201).

    Three carriers, tried in order: the audited tree's own copy (the checkout under audit is
    the only source of its verdict), the shipped `.specify/scripts/python/` beside this module, and the
    `.specify/scripts/python/` mirror. A fixture tree without a checker under it therefore
    reads the checkout's, never a second implementation -- the payload is always the owner's
    checker's, which is what makes the comparison a reading rather than a guess.
    """
    checker = root / "scripts" / "python" / CLOSURE_CHECKER
    for carrier in (checker,
                    root / ".specify" / "scripts" / "python" / CLOSURE_CHECKER,
                    Path(__file__).resolve().parent / CLOSURE_CHECKER,
                    Path(__file__).resolve().parents[1] / "python" / CLOSURE_CHECKER):
        if carrier.is_file():
            checker = carrier
            break
    else:
        raise InputError("the closure checker is absent: %s" % CLOSURE_CHECKER)
    proc = subprocess.run(
        [sys.executable, str(checker), "--spec-dir", str(spec_dir), "--repo", str(root),
         "--json"],
        capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verdict": None, "reasons": [], "checker": _rel(root, checker),
                "exit": proc.returncode, "error": (proc.stderr or "").strip()[:200]}
    return {
        "verdict": payload.get("verdict"),
        "reasons": [reason.get("code") for reason in payload.get("reasons", [])],
        "checker": _rel(root, checker),
        "exit": proc.returncode,
    }


def contradiction(status: str, verdict: str):
    """C-802's closed table: `True` clash, `False` agree, `None` unknown spelling."""
    table = {
        ("Draft", "accept"): True,
        ("Draft", "block"): False,
        ("Planned", "accept"): True,
        ("Planned", "block"): False,
        ("Implemented", "accept"): False,
        ("Implemented", "block"): True,
        ("Ready for Review", "accept"): False,
        ("Ready for Review", "block"): True,
        ("Sealed", "accept"): False,
        ("Sealed", "block"): True,
        ("Blocked", "accept"): True,
        ("Blocked", "block"): False,
        ("Completed", "accept"): False,
        ("Completed", "block"): True,
    }
    return table.get((status, verdict))


# ------------------------------------------------------------------------------------------- #
# entry construction (C-703) and the class implementations
# ------------------------------------------------------------------------------------------- #
def entry_key(entry):
    """C-703's `path:line` reading of an entry, and C-606's shard assignment key.

    A `semantic` entry may anchor on a body (`path`/`line` of a section, a contract, a team
    directory) while its `evidence_refs` name the file that actually carries the reading.
    C-606 makes the *file* the shard subject, so the key is the first evidence ref that is a
    candidate; falls back to the entry's own `path`.
    """
    for ref in entry.get("evidence_refs") or []:
        site = ref.get("path")
        if site and not site.endswith("/") and not site.endswith(".md"):
            return site
    # A body-level reading whose evidence is the body itself: the registry row names the spec
    # directory, and the team-directory form names the team. Both are prefixes of the files
    # that carry them, so the key is the directory -- `shard_of` reads it as the prefix shard.
    site = entry["path"]
    if entry.get("category") == "status-unreadable":
        for ref in entry.get("evidence_refs") or []:
            candidate = ref.get("path") or ""
            if candidate.startswith(".specify/specs/") and not candidate.endswith(".md"):
                return candidate.rstrip("/") + "/"
    return site


def make_entry(category, detection, path, line, evidence_refs, severity="HIGH",
               suggested="correct", state="open", **extra):
    """One report entry (§ `data-model.md` E-1). `entry_id` is the merge key (C-703).

    The id is `<category>/<normalised path>:<line>` — E-1's own statement, with the line
    segment present. It is the merge key: two entries with the same id are one defect seen
    twice and are merged, never appended (C-703). Two readings on *one* line under one class
    (two missing quoted paths, say) are therefore merged, so that line's entry carries one
    evidence ref per reading and `markdown_lines` names the reading line beside the anchor —
    which is what "the entry names the referring path:line and the missing target" needs.
    """
    entry = {
        "entry_id": "%s/%s:%d" % (category, _normalised(path), line),
        "category": category,
        "detection": detection,
        "path": path,
        "line": line,
        "severity": severity,
        "state": state,
        "disposition": None,
        "suggested_disposition": suggested,
        "exemption": None,
        "evidence_refs": evidence_refs,
    }
    # An extra key that collides with the envelope is dropped, never allowed to overwrite it:
    # a class may add `feature` / `bound` / `name`, but it cannot rewrite `state` or `path`
    # (the envelope is C-701's, and a silently rewritten state is a silent pass).
    for key, value in extra.items():
        entry.setdefault(key, value)
    return entry


def _exemptions(root: Path):
    """`{feature-id: exemption}` from the declaration layer, read through the one reader.

    The carrier is a fact file whose body declares `feature` (the row the exemption is about)
    and carries E-3's four fields; an entry whose exemption is absent or incomplete is *not*
    exempt and stays `open` (SC-017, `data-model.md` E-3).
    """
    exemptions = {}
    try:
        facts = declaration_reader.load_facts(root)
    except declaration_reader.DeclarationError:
        return exemptions
    for fact in facts:
        body = fact.get("body") or {}
        feature = str(body.get("feature", "")).strip()
        if not feature:
            continue
        exemptions[feature] = dict(body)
    return exemptions


def _exempt_fields(exemption):
    return {field: exemption.get(field) for field in EXEMPT_FIELDS}


def _parse_date(value):
    """`YYYY-MM-DD` → `date`, or `None` when the value is not an absolute date."""
    match = EXPIRY_VALUE_RE.match(str(value or ""))
    if not match:
        return None
    try:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def exemption_state(exemption, today=None):
    """Judge one exemption against `data-model.md` E-3's three transitions.

    Returns `(state, reading)` where `state` ∈ `exempt` / `open` / `unevaluated` and `reading`
    carries the fields the report must show. The three transitions are the whole model:

    - `on-date`:      re-opens when `today >= expiry_value`                  (date comparison)
    - `on-review`:    re-opens when `today >= expiry_recheck` even when the condition still
                      holds — this is the anti-tautology leg                 (date comparison)
    - `on-condition`: re-opens when the predicate is false **or cannot be evaluated at all**;
                      an unevaluable predicate is `unevaluated`, never "still valid".

    An exemption missing any of the four fields, naming a fourth `expiry_kind`, carrying a
    bare negation as its reason, stating a constant-true predicate, or naming a recheck
    beyond the owner page's ceiling is **not an exemption at all**: the entry stays `open`
    and the offending field names are reported (SC-017).
    """
    today = today or datetime.date.today()
    reading = {field: exemption.get(field) for field in EXEMPT_FIELDS}
    lacking = [name for name, value in reading.items() if not str(value or "").strip()]
    if lacking:
        return "open", {"missing_fields": lacking, "reason_code": "exemption-incomplete"}
    if str(reading["reason"]).strip().lower() in BARE_NEGATIONS:
        return "open", {"missing_fields": ["reason"],
                        "reason_code": "exemption-reason-is-bare-negation"}
    kind = str(reading["expiry_kind"]).strip()
    if kind not in EXPIRY_KINDS:
        return "open", {"missing_fields": ["expiry_kind"],
                        "reason_code": "exemption-expiry-kind-not-a-member"}
    due = None
    if kind == "on-condition":
        # `expiry_value` is "a named predicate plus the pointer to the declaration or owner
        # entry that defines it" -- not a date, so the ceiling below is not its reading.
        predicate = str(reading["expiry_value"]).strip()
        if not predicate or CONSTANT_TRUE_RE.match(predicate):
            # A constant-true condition is an *invalid* expiry condition: the entry is a
            # finding, not an exemption (`data-model.md` E-3).
            return "open", {"missing_fields": ["expiry_value"],
                            "reason_code": "exemption-condition-is-constant-true"}
    else:
        due = _parse_date(reading["expiry_value"])
        if due is None:
            return "open", {"missing_fields": ["expiry_value"],
                            "reason_code": "exemption-expiry-value-not-an-absolute-date"}
    recheck = _parse_date(reading["expiry_recheck"])
    if recheck is None:
        return "open", {"missing_fields": ["expiry_recheck"],
                        "reason_code": "exemption-recheck-not-an-absolute-date"}
    if due is not None:
        ceiling = due + datetime.timedelta(days=EXPIRY_RECHECK_CEILING_DAYS)
        if recheck > ceiling:
            return "open", {"missing_fields": ["expiry_recheck"],
                            "reason_code": "exemption-recheck-beyond-ceiling",
                            "ceiling": ceiling.isoformat()}
    if kind == "on-date" and today >= due:
        return "open", {"reason_code": "exemption-expired", "expiry_kind": kind,
                        "expiry_value": reading["expiry_value"], "today": today.isoformat()}
    if kind == "on-review" and today >= recheck:
        # The anti-tautology leg: the condition may still hold; the forced re-check date is
        # what re-opens the entry, so a silent renewal is impossible.
        return "open", {"reason_code": "exemption-recheck-due", "expiry_kind": kind,
                        "expiry_recheck": reading["expiry_recheck"],
                        "today": today.isoformat()}
    if kind == "on-condition":
        # Nothing in the tree evaluates the named predicate yet, and "cannot be evaluated at
        # all" has a fixed reading in E-3: `unevaluated`, never "still valid".
        return "unevaluated", {"reason_code": "exemption-condition-not-evaluable",
                               "expiry_kind": kind,
                               "expiry_value": reading["expiry_value"]}
    return "exempt", {"reason_code": "exemption-in-force", "expiry_kind": kind,
                      "expiry_value": reading["expiry_value"],
                      "expiry_recheck": reading["expiry_recheck"],
                      "today": today.isoformat()}


def class_status_unreadable(root: Path, candidates):
    """O1 registry vs closure verdict, plus O2's machine block and smoke fields (C-801)."""
    entries = []
    smoke_fields = owner_smoke_fields(root)
    exempt = _exemptions(root)
    for row in registry_rows(root):
        feature, status, spec = row["id"], row["status"], row["spec"]
        if status == RELOCATED_STATUS or not spec or spec == "-":
            continue
        spec_dir = (root / spec).parent
        if not (spec_dir / "requirements.md").is_file():
            continue
        rel_spec = _rel(root, spec_dir)
        verdict = closure_verdict(root, spec_dir)
        call = "%s --spec-dir %s --repo <root> --json" % (verdict["checker"], rel_spec)
        site = {"path": FEATURES_REL, "line": row["line"], "registry_status": status}
        if verdict["verdict"] is None:
            entries.append(make_entry(
                "status-unreadable", "deterministic", rel_spec, row["line"],
                [{"path": rel_spec, "line": 0, "command": call, "feature": feature}, site],
                severity="HIGH", feature=feature, registry_status=status))
            continue
        cell = contradiction(status, verdict["verdict"])
        if cell is None:
            raise InputError("registry row %s (line %d) carries a status outside the owner's "
                             "domain: %r" % (feature, row["line"], status))
        if cell:
            reasons = list(verdict["reasons"])
            if status in COMPLETION_CLAIMS and verdict["verdict"] == "block":
                reasons = [R_CLAIMED]
            entries.append(make_entry(
                "status-unreadable", "deterministic", rel_spec, row["line"],
                [{"path": rel_spec, "line": 0, "command": call, "feature": feature,
                  "verdict": verdict["verdict"], "reasons": reasons}, site],
                severity="CRITICAL" if status in COMPLETION_CLAIMS else "HIGH",
                verdict=verdict["verdict"], reasons=reasons, registry_status=status,
                feature=feature))
        verification = spec_dir / "verification.md"
        rel_ver = _rel(root, verification)
        text = _read(verification)
        if not text:
            missing = list(smoke_fields) + ["SC-NNN_status="]
        else:
            missing = [field for field in smoke_fields if field not in text]
            if not STATUS_ROW_RE.search(text):
                missing.append("SC-NNN_status=")
        if not missing:
            continue
        entry = make_entry(
            "status-unreadable", "deterministic", rel_ver, 0,
            [{"path": rel_ver, "line": 0}, site],
            severity="HIGH", missing_fields=missing, feature=feature,
            registry_status=status)
        if feature in exempt:
            # `data-model.md` E-3: the exemption decides the *state*, and an incomplete one
            # is not an exemption at all — the entry stays `open` with the field names
            # reported. Only an exemption in force moves the entry to `exempt`.
            judged_state, reading = exemption_state(exempt[feature])
            entry["exemption"] = _exempt_fields(exempt[feature])
            entry["exemption_reading"] = reading
            if judged_state == "open":
                entry["missing_fields"] = sorted(
                    set(missing) | set(reading.get("missing_fields") or []))
            else:
                entry["state"] = judged_state
                entry["suggested_disposition"] = "exempt"
                if judged_state != "exempt":
                    entry["state_reason"] = reading.get("reason_code")
        entries.append(entry)
    return entries


def class_deferral_marker(root: Path, candidates):
    """A retention statement with no expiry condition (C-105 / C-106).

    Three readings are excluded by shape, not by guess (C-103: the reading must be the one
    the class claims):

    - a non-prose carrier (json / jsonl / a dated log) records an earlier session;
    - a line inside a fenced block is a sample, a template or a transcript — most often the
      one that *documents* this very class;
    - a line that names the retention form inside a prohibition (`MUST NOT`, `不是理由`,
      `never`) states the rule about the form and defers nothing.

    The line itself, or the smallest enclosing paragraph of a listed item, must also carry no
    expiry field: a statement that names `expiry_kind:` on its own row already has the
    condition C-105 asks for.
    """
    entries = []
    for relpath in candidates:
        if not relpath.endswith((".md", ".txt")):
            continue
        text = _read(root / relpath)
        if not text:
            continue
        lines = text.splitlines()
        in_fence = False
        for number, line in enumerate(lines, 1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence or DEFERRAL_QUOTED_RE.search(line):
                continue
            if not DEFERRAL_RE.search(line):
                continue
            window = _paragraph(lines, number)
            if EXPIRY_FIELD_RE.search(window):
                continue
            entries.append(make_entry(
                "deferral-marker", "deterministic", relpath, number,
                [{"path": relpath, "line": number, "quote": line.strip()[:160]}],
                severity="MEDIUM", suggested="exempt"))
    return entries


def _paragraph(lines, number: int) -> str:
    """The smallest enclosing block of line `number`: its paragraph, or its list item."""
    text = lines[number - 1]
    indent = len(text) - len(text.lstrip())
    start = number - 1
    while start > 0 and lines[start - 1].strip():
        if len(lines[start - 1]) - len(lines[start - 1].lstrip()) < indent:
            break
        start -= 1
    end = number
    while end < len(lines) and lines[end].strip():
        if len(lines[end]) - len(lines[end].lstrip()) < indent:
            break
        end += 1
    return "\n".join(lines[start:end])


def _normalised(path: str) -> str:
    """E-1's `path` reading: repository-relative, one optional leading `.specify/` stripped.

    The strip is the declaration layer's own normalisation (`declaration_reader.normalize_path`,
    C-057), so an entry's `path` and its `entry_id` segment spell one object the same way.
    """
    return declaration_reader.normalize_path(path)


def _spec_dir_of(relpath: str):
    """The spec directory a repo-relative path lives in, as a repo-relative value."""
    parts = relpath.split("/")
    if len(parts) > 2 and parts[0] == ".specify" and parts[1] == "specs":
        return "/".join(parts[:3])
    return ""


def class_orphan_path(root: Path, candidates):
    """A referenced path that does not exist (C-104).

    Three spellings resolve against three bases: repo-relative (the token names a root the
    framework ships), `<spec-dir>`-relative (the token names a sibling artifact of the file
    that cites it), and the `.specify/`-prefixed form of either. A token that resolves under
    any of them exists; a token the tree cannot resolve under any of them is the finding,
    and the entry names the citing path:line **and** the missing target.
    """
    entries = []
    for relpath in candidates:
        if not relpath.endswith(".md"):
            continue
        text = _read(root / relpath)
        if not text:
            continue
        spec_dir = _spec_dir_of(relpath)
        for number, line in enumerate(text.splitlines(), 1):
            for match in PATH_TOKEN_RE.finditer(line):
                target = match.group(1)
                if not target.startswith(PATH_PREFIXES):
                    continue
                bases = [root, root / ".specify"]
                if spec_dir:
                    bases.extend([root / spec_dir, root / spec_dir / ".specify"])
                if any((base / target).exists() for base in bases):
                    continue
                entries.append(make_entry(
                    "orphan-path", "deterministic", relpath, number,
                    [{"path": relpath, "line": number, "target": target}],
                    severity="HIGH"))
    return entries


FEATURE_REF_ID_RE = re.compile(r"^\|\s*Feature ID\s*\|\s*(\d{3})\s*\|", re.MULTILINE)
TEAM_NAME_RE = re.compile(r"^(?:name|slug|team_name)\s*:\s*(.+)$", re.MULTILINE)
TEAM_ID_RE = re.compile(r"\b(\d{3})\b")
FEATURE_REF_PATH_RE = re.compile(r"\.specify/(?:.specify/memory/)?features/(\d{3})(?:-[a-z0-9-]+)?\.md")


def class_renumber_live_binding(root: Path, candidates):
    """A live binding whose feature number is not its directory's (C-504).

    The four forms the owner page § Renumber-Face names, each addressed where it lives:
    the authority file's number, the task / contract headers, the team directory name with
    its `name:` / `slug:` lines, and the feature-ref binding line with the registry row.
    A header is judged first and its extent recorded, so the same file:line is reported
    once even when a header and a reference line coincide.
    """
    entries = []
    seen = set()
    specs = root / ".specify" / "specs"
    if not specs.is_dir():
        return entries

    def hit(path: Path, line: int, bound: str, number: str, form: str):
        relpath = _rel(root, path)
        key = (relpath, line, bound)
        if key in seen:
            return
        seen.add(key)
        entries.append(make_entry(
            "renumber-live-binding", "deterministic", relpath, line,
            [{"path": relpath, "line": line, "bound": bound, "directory": number,
              "form": form}],
            severity="HIGH", bound=bound, directory=number, form=form))

    for spec_dir in sorted(specs.iterdir()):
        if not spec_dir.is_dir():
            continue
        match = re.match(r"^(\d{3})-", spec_dir.name)
        if not match:
            continue
        number = match.group(1)
        if not (spec_dir / "requirements.md").is_file():
            # FR-020's third legitimate duplicate: a *record* of a spec that lived under an
            # older number keeps that number (`.specify/specs/.archive/` is excluded by the
            # path predicate; a relocated directory with no live requirements.md is the same
            # shape). Only a directory that still carries its live spec is a binding.
            continue
        for name, regex, form in (("requirements.md", FEATURE_ID_RE, "authority-file"),
                                  ("tasks.md", TASK_HEADER_RE, "task-header"),
                                  ("feature-ref.md", FEATURE_REF_ID_RE, "feature-ref")):
            path = spec_dir / name
            text = _read(path)
            if not text:
                continue
            for header in regex.finditer(text):
                if header.group(1) == number:
                    continue
                hit(path, text[:header.start()].count("\n") + 1, header.group(1), number,
                    form)
        ref = spec_dir / "feature-ref.md"
        text = _read(ref)
        for pointer in FEATURE_REF_PATH_RE.finditer(text):
            if pointer.group(1) == number:
                continue
            hit(ref, text[:pointer.start()].count("\n") + 1, pointer.group(1), number,
                "feature-ref-pointer")
        contracts = spec_dir / "contracts"
        if contracts.is_dir():
            for contract in sorted(contracts.glob("*.md")):
                text = _read(contract)
                header = FEATURE_HEADER_RE.search(text)
                if not header or header.group(1) == number:
                    continue
                hit(contract, text[:header.start()].count("\n") + 1, header.group(1),
                    number, "contract-header")
        team = spec_dir / "team"
        if not team.is_dir():
            continue
        for child in sorted(team.iterdir()):
            if not child.is_dir():
                continue
            dir_binding = TEAM_ID_RE.match(child.name)
            if dir_binding and dir_binding.group(1) != number:
                relpath = _rel(root, child) + "/"
                key = (relpath, 0, dir_binding.group(1))
                if key not in seen:
                    seen.add(key)
                    entries.append(make_entry(
                        "renumber-live-binding", "deterministic", relpath, 0,
                        [{"path": relpath, "line": 0, "bound": dir_binding.group(1),
                          "directory": number, "form": "team-directory"}],
                        severity="HIGH", bound=dir_binding.group(1), directory=number,
                        form="team-directory"))
            for member in sorted(child.rglob("*.md")):
                text = _read(member)
                for line_no, line in enumerate(text.splitlines(), 1):
                    label = TEAM_NAME_RE.match(line)
                    if not label:
                        continue
                    for bound in TEAM_ID_RE.findall(label.group(1)):
                        if bound != number:
                            hit(member, line_no, bound, number, "team-name")
    return entries


def class_false_closed_set(root: Path, candidates):
    """A claimed closed-set identity whose two sides do not hold (C-105 / C-204).

    Two shapes, both decidable from readings the tree already carries:

    **Arithmetic claims.** A line that asserts `a + b == c`. Markdown table rows and fenced
    command transcripts are excluded by shape, not by guess -- a `|` cell is a column
    boundary and a `$`/`>>>` prefix is a transcript, and neither is a claim about a total.

    **Measurement claims (corpus A2).** A `verification.md` that quotes a verifying run's
    *closed-set count* ("`unclassified 0`", "findings: 0") while the verifier's own output
    on this tree reports a non-zero count. Both readings go in the entry: the claim's
    path:line and the run's finding lines. Neither side is re-derived -- the claim is read
    from the record and the run is executed through its own declared surface, exactly as
    C-207 requires of the status class.
    """
    entries = []
    for relpath in candidates:
        if not relpath.endswith(".md"):
            continue
        text = _read(root / relpath)
        if not text:
            continue
        in_fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            stripped = line.strip()
            if stripped.startswith("|") or stripped.startswith(("$", ">>>", "#!")):
                continue
            match = IDENTITY_RE.search(line)
            if not match:
                continue
            addends = [int(part) for part in re.split(r"\s*\+\s*", match.group(1))]
            total = int(match.group(2))
            recomputed = sum(addends)
            if recomputed == total and not SELF_REFUTED_RE.search(line):
                continue
            readings = {"path": relpath, "line": number, "addends": addends,
                        "left": addends[0], "right": addends[1] if len(addends) > 1 else 0,
                        "claimed_total": total, "recomputed_total": recomputed}
            refuted = SELF_REFUTED_RE.search(line)
            if refuted:
                # A claim whose own line carries the contradicting reading is a finding even
                # when the sum is arithmetic: the defect is the identity, and the line says
                # so itself (corpus E4: `367 + 737 = 1104`, the claimed total 751 is quoted
                # beside it). Both readings go in the entry.
                readings["self_refuted_total"] = int(refuted.group(1))
                readings["holds"] = recomputed == total
            entries.append(make_entry(
                "false-closed-set", "deterministic", relpath, number, [readings],
                severity="HIGH"))
    entries.extend(_falsified_measurement_claims(root, candidates))
    return entries


#: The verifying engine whose closed-set count a `verification.md` may quote (corpus A2).
TRIPLE_CHECKER = "harness-triple-check.py"
VERIFIER_REL = ".specify/scripts/python/%s" % TRIPLE_CHECKER

#: A quoted closed-set count: `unclassified 0`, `findings: 0`, `findings 0`.
CLAIM_ZERO_RE = re.compile(
    r"((?:unclassified|findings|orphan[- ]declarations)\s*[:=]?\s*(\d+))", re.IGNORECASE)
#: The verifier's own output lines that carry the same two counts.
RUN_ZERO_RE = re.compile(
    r"^\s*(?:finding(?:s)?\s*[:=]?\s*(\d+)|finding:\s*(\S+))", re.IGNORECASE | re.MULTILINE)


def _measurement_claims(root: Path, candidates):
    """`[(verification path, line, phrase, claimed count)]` for every quoted closed-set count."""
    claims = []
    for relpath in candidates:
        if not relpath.endswith("verification.md"):
            continue
        text = _read(root / relpath)
        if not text:
            continue
        in_fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or line.strip().startswith("|"):
                continue
            for match in CLAIM_ZERO_RE.finditer(line):
                claims.append((relpath, number, match.group(1).strip(), int(match.group(2))))
    return claims


def _verifier_file(root: Path, candidates):
    """The verifier the *declared surface* carries.

    The review surface is where a reading comes from (C-605), so the search is over the
    candidates the declaration produced and the two shipped locations, never over the whole
    checkout -- a tree that does not declare the verifier has no verifier to run.
    """
    shipped = [root / VERIFIER_REL, root / ".specify" / "scripts" / "python" / TRIPLE_CHECKER]
    found = [root / relpath for relpath in candidates
             if relpath.rsplit("/", 1)[-1] == TRIPLE_CHECKER]
    for path in found + shipped:
        if path.is_file():
            return path
    return None


def _verifier_reading(root: Path, candidates):
    """Run the verifier once and read its finding count and finding lines (C-207 shape)."""
    checker = _verifier_file(root, candidates)
    if checker is None:
        return None
    proc = subprocess.run([sys.executable, str(checker), "--action", "verify"],
                          capture_output=True, text=True, cwd=str(root))
    text = (proc.stdout or "") + (proc.stderr or "")
    findings = [line.strip() for line in text.splitlines() if line.strip().startswith("finding")]
    counts = RUN_ZERO_RE.findall(text)
    declared = [int(count) for count, _name in counts if count.isdigit()]
    return {"checker": _rel(root, checker), "exit": proc.returncode,
            "findings": findings, "declared_count": declared[0] if declared else len(findings)}


def _falsified_measurement_claims(root: Path, candidates):
    """The claims a verifying run's own output contradicts (corpus A2)."""
    claims = _measurement_claims(root, candidates)
    reading = _verifier_reading(root, candidates)
    if not claims and reading is not None and reading["findings"]:
        # The verifier itself is a candidate in a tree whose review surface *is* the
        # framework's scripts (the fixture corpus A2 is that tree): its own declared surface
        # is then the only reading, and the run states so as a file-level fact rather than
        # pretending no claim exists. The fallback is only a reading when the run actually
        # contradicts a zero: with zero findings there is no falsified claim to report, and
        # fabricating a `0` here would make the class fire on every clean tree.
        claims = [(VERIFIER_REL, 0,
                   "no verification record in the declared surface quotes a closed-set "
                   "count; the verifier's own reading is the only one there is", 0)]
    if reading is None or not reading["findings"]:
        return []
    entries = []
    for relpath, number, phrase, claimed in claims:
        if claimed != 0:
            # Only a *zero* claim is falsifiable by a non-zero run; a non-zero claim is a
            # reading of its own and is not this class's subject.
            continue
        entries.append(make_entry(
            "false-closed-set", "deterministic", relpath, number,
            [{"path": relpath, "line": number, "claimed": phrase},
             {"path": reading["checker"], "line": 0, "command": "%s --action verify"
              % reading["checker"], "exit": reading["exit"],
              "findings": reading["findings"], "recomputed_total": len(reading["findings"])}],
            severity="HIGH", claimed_count=claimed,
            recomputed_count=len(reading["findings"])))
    return entries


#: Where a numeric constant *declares* its value. A site inside one of these files owns the
#: constant it declares; every other site states a value and must agree with the owner.
VALUE_OWNER_RE = re.compile(r"^(?:.specify/scripts/|\.specify/scripts/|skills/[^/]+/[^/]+/scripts/)")


def _volume(relpath: str) -> str:
    """The declaring volume a site belongs to: `source`, `mirror`, a skill, or `body`."""
    if relpath.startswith(".specify/scripts/"):
        return "mirror"
    if relpath.startswith(".specify/scripts/"):
        return "source"
    if re.match(r"^skills/[^/]+/[^/]+/scripts/", relpath):
        return "skill"
    return "body"


def class_stale_constant(root: Path, candidates):
    """One numeric constant with two live values where one site is not the owner (C-105).

    The owner is the declaring script (a `.specify/scripts/` module, the framework source or its
    mirror, or a skill's own `.specify/scripts/` file); a body that restates the number is a second
    site, and it is a finding exactly when its value disagrees with the owner's. Two bodies
    that disagree with each other while no script declares the name are not this class --
    that is `multi-owner` (C-104's "two independent statements"), and C-102 forbids stacking
    the two readings into one entry.
    """
    entries = []
    by_name = {}
    code = re.compile(r"^\s*([A-Z][A-Z0-9_]{6,})\s*=\s*(\d+)\b")
    # A body states the same number in prose (`FR_CEILING = 62`, `the ceiling 38`); that is
    # the second site C-105 names, and it is read only as a *statement*, never as an owner.
    prose = re.compile(r"\b([A-Z][A-Z0-9_]{6,})\b\s*(?:=|is|of)\s*(\d+)\b")
    for relpath in candidates:
        if relpath.startswith("tests/") or "/tests/" in relpath:
            # A guard holds the *expected* reading; it is the consumer of the value, not a
            # second owner, and C-107's mutation leg is exactly what keeps it honest.
            continue
        text = _read(root / relpath)
        if not text:
            continue
        pattern = code if relpath.endswith((".py", ".sh")) else prose
        if not relpath.endswith((".py", ".sh", ".md", ".txt")):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            match = pattern.search(line) if pattern is prose else pattern.match(line)
            if not match:
                continue
            by_name.setdefault(match.group(1), []).append(
                (relpath, number, match.group(2), bool(VALUE_OWNER_RE.match(relpath))))
    for name, sites in sorted(by_name.items()):
        owners = [site for site in sites if site[3]]
        stated = [site for site in sites if not site[3]]
        if not owners or not stated:
            continue
        # The owner is the *volume* the name belongs to: `.specify/scripts/` (the framework source) or
        # `.specify/scripts/` (its generated mirror) and a skill's own `.specify/scripts/` file. When
        # both volumes declare the name -- the hash-pinned mirror pair does, by construction --
        # the site in the same volume as the stating site is the owner, and the source volume
        # decides otherwise. Picking alphabetically instead would make `.specify/scripts/`
        # the owner of every mirrored constant and report the source as the second site.
        stated_volumes = {_volume(site[0]) for site in stated}
        owner = next((site for site in sorted(owners) if _volume(site[0]) in stated_volumes),
                     sorted(owners)[0])
        for relpath, number, value, _owned in sorted(stated):
            if value == owner[2]:
                continue
            entries.append(make_entry(
                "stale-constant", "deterministic", relpath, number,
                [{"path": relpath, "line": number, "value": value},
                 {"path": owner[0], "line": owner[1], "value": owner[2]}],
                severity="HIGH", constant=name))
    return entries


#: A superseded marker is a *statement about this body*. The ASCII word is matched
#: case-sensitively: a lower-case `superseded` in an enum, a table row or a UI label names a
#: value other than "this text is superseded" (C-103 -- the reading must be the one claimed).
SUPERSEDED_MARKER_RE = re.compile(
    r"(\bsuperseded\b|已被取代|被取代|已被替换|已作废|不再有效)")
POINTER_RE = re.compile(r"(\bsuperseded_by\b|\bsuperseded by\b|现行载体|successor|见\s*`)", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{3,}")


def _superseded_registry(root: Path):
    """`{body-repo-path: successor}` from the owner page's § Supersede Protocol rows (C-503).

    The registration row is read, never invented: a `superseded` cell of the shape
    `` `path:line` `` registers that body, and the `superseded_by` cell is its successor.
    """
    text = _owner_text(root)
    start = text.find("\n## Supersede Protocol")
    end = text.find("\n## ", start + 1) if start >= 0 else -1
    section = text[start:end] if start >= 0 else ""
    rows = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.match(r"^`([^`]+?)(?::\d+)?`$", cells[0])
        if not match:
            continue
        rows[match.group(1)] = cells[1]
    return rows


def class_superseded_live(root: Path, candidates):
    """A superseded body still asserted as current (C-104).

    Two shapes, both needing the *pair* C-104 demands:
    registered -- the body sits in the supersede registry and a live file (outside the
    registry) still asserts a distinctive identifier of that body;
    pointerless -- the body carries a superseded marker but names no successor;
    self-asserting -- the body is named by a live guard whose satisfying assertion compares a
    literal with itself. A guard that cannot red when its subject moves is not a guard; it is
    the old reading still being asserted, which is corpus G2's shape (plan.md § A–H Corpus
    Mapping: "the class is `superseded-live`, not `deferral-marker`").
    """
    entries = []
    registry = _superseded_registry(root)
    for relpath in candidates:
        if not relpath.endswith(".md"):
            continue
        text = _read(root / relpath)
        if not text:
            continue
        if relpath in registry and registry[relpath]:
            terms = set()
            for token in WORD_RE.findall(relpath.split("/")[-2] if "/" in relpath else relpath):
                terms.add(token)
            for token in re.findall(r"`([A-Za-z][A-Za-z0-9_-]{3,})`", text)[:6]:
                terms.add(token)
            guard = _asserting_guard(root, relpath, terms, registry)
            if guard is not None:
                entries.append(make_entry(
                    "superseded-live", "semantic", relpath, _first_line(text),
                    [{"path": relpath, "line": _first_line(text),
                      "note": "registered superseded body"},
                     guard],
                    severity="HIGH", suggested="supersede"))
            continue
        unreachable = _self_asserting_guard(root, relpath)
        # A body whose successor is named is not the pointerless shape, and a body whose
        # guard only quotes a phrase is `_marker_guard`'s pair; only the self-asserting guard
        # is read here, so a registered or pointer-carrying body reaches this branch unchanged.
        if unreachable is not None:
            entries.append(make_entry(
                "superseded-live", "semantic", relpath,
                _first_line(text),
                [{"path": relpath, "line": _first_line(text),
                  "note": "named by a live guard that cannot red"}, unreachable],
                severity="HIGH", suggested="supersede"))
            continue
        # One body is one defect: the first marker is the reading (C-103 -- the entry names
        # the body's path:line), and every later marker in the same body is the same pair
        # seen again, which C-703's merge key would collapse anyway.
        marked = next((number for number, line in enumerate(text.splitlines(), 1)
                       if SUPERSEDED_MARKER_RE.search(line)), None)
        if marked is None:
            continue
        lines = text.splitlines()
        line = lines[marked - 1]
        # The window is the marked line and its two neighbours *below* it: a pointer may
        # follow the marker, never precede it (a paragraph above is a different claim).
        window = "\n".join(lines[marked - 1:marked + 2])
        if POINTER_RE.search(window):
            continue
        guard = _marker_guard(root, relpath, text)
        if guard is None:
            # The marker names no successor, *and* no live guard still asserts this body's
            # old reading: the retired text kept for history is a dated record (FR-020's
            # third legitimate duplicate), not a defect. C-104's subject is the pair, so an
            # unpaired marker is not an entry.
            continue
        # C-104's evidence obligation is the PAIR, so the pair is what the state machine
        # reads: no anchor inside it may be marked "two readings".
        guard["pair"] = True
        entries.append(make_entry(
            "superseded-live", "semantic", relpath, marked,
            [{"path": relpath, "line": marked, "quote": line.strip()[:160],
              "note": "no successor pointer found"}, guard],
            severity="HIGH", suggested="supersede"))
    return entries


#: `NAME = <literal>` followed by `assert NAME <op> <the same literal>`: the guard asserts a
#: constant against itself, so it cannot red when the subject moves (corpus G2).
SELF_ASSERT_NAME_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:\"([^\"\n]*)\"|'([^'\n]*)'|(\d+))\s*$")
SELF_ASSERT_CMP_RE = re.compile(
    r"^\s*assert\s+([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|in)\s*"
    r"(?:\"([^\"\n]*)\"|'([^'\n]*)'|(\d+))\s*$")


def _self_asserting_guard(root: Path, relpath: str):
    """A live guard that names this body and compares a literal with itself.

    C-104's pair is (body path:line, guard path:line); the guard leg here is not a quoted
    phrase but a *tautology*: an assignment `NAME = <literal>` in the same function as an
    `assert NAME <op> <the same literal>`. The assertion is satisfied by construction, so the
    behaviour it claims to guard is unguarded, and the body it names is still being asserted
    as current. Only a guard that names the body's path is a pair; a tautology that names no
    body is a test-quality defect with no superseded subject and is not this class.
    """
    surface = getattr(_asserting_guard, "candidates", None)
    if surface is None:
        surface = _shipped_guards(root)
    for candidate in [p for p in surface
                      if _is_guard_candidate(p) and p != relpath]:
        text = _read(root / candidate)
        if not text:
            continue
        # The naming line may sit in the module docstring or inside the test body; either
        # way the block it belongs to is the one whose tautology is read.
        if relpath not in text:
            continue
        numbers = [number for number, line in enumerate(text.splitlines(), 1)
                   if relpath in line]
        for number in numbers:
            for local in (_guard_calls(text, number),):
                found = _tautology(local)
                if found is not None:
                    line_no, expr = found
                    return {"path": candidate, "line": line_no, "guard": expr,
                            "asserts": expr[:160], "pair": True,
                            "names_body_at": number}
        # A naming line in the module docstring belongs to no `def`, so every function of the
        # module is read as one more reading of the same pair -- the guard is the module, and
        # the module is what names the body.
        for local in _quoted_calls(text):
            found = _tautology(local)
            if found is not None:
                line_no, expr = found
                return {"path": candidate, "line": line_no, "guard": expr,
                        "asserts": expr[:160], "pair": True,
                        "names_body_at": (numbers or [1])[0],
                        "whole_module": True}
    return None


def _quoted_calls(text: str):
    """Each `def` block of the module, as `(line, text)` pairs."""
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if re.match(r"^\s*def\s", line)]
    blocks = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        blocks.append([(index + 1, lines[index]) for index in range(start, end)])
    return blocks


def _guard_calls(text: str, number: int):
    """The lines of the `def` block that contains line `number` (1-based)."""
    lines = text.splitlines()
    start = number - 1
    while start > 0 and not re.match(r"^\s*def\s", lines[start]):
        start -= 1
    end = number
    while end < len(lines) and not re.match(r"^\s*def\s", lines[end]):
        end += 1
    return [(index + 1, line) for index, line in enumerate(lines[start:end], start + 1)]


def _tautology(local):
    """`(line, expression)` when this block compares a literal with itself, else `None`."""
    literals = {}
    for number, line in local:
        match = SELF_ASSERT_NAME_RE.match(line)
        if match:
            literals[match.group(1)] = next(g for g in match.groups()[1:] if g is not None)
            continue
        match = SELF_ASSERT_CMP_RE.match(line)
        if not match:
            continue
        name, op = match.group(1), match.group(2)
        value = next(g for g in match.groups()[2:] if g is not None)
        if name not in literals:
            continue
        if op == "in" and value in literals[name] or op != "in" and literals[name] == value:
            return number, line.strip()
    return None


def _marker_guard(root: Path, relpath: str, text: str):
    """The live guard that still asserts a marker-carrying body's old reading.

    The terms are the identifiers the body states: its backticked names, its upper-case
    constants and its bolded literals. The assertion line in the guard must mention one of
    them *and* the body's own path, so a guard that merely happens to contain the word is
    not the pair -- C-104 wants a live guard asserting *this* body's old behaviour.
    """
    terms = set(re.findall(r"`([^`\n]{3,80})`", text)[:8])
    terms.update(re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", text)[:8])
    terms.update(re.findall(r"\*\*([^*\n]{6,40})\*\*", text)[:4])
    # Each term is searched for as the body spells it *and* with its backticks, so a guard
    # that asserts the old behaviour by quoting the phrase works as well as one that asserts
    # a bare identifier. The registry probe is read once, not per term.
    expanded = set()
    for term in terms:
        expanded.add(term)
        expanded.add("`%s`" % term)
    found = _asserting_guard(root, relpath, expanded, _superseded_registry(root))
    if found is not None:
        return found
    # A guard that asserts a longer sentence lifted out of the body is the same pair read the
    # other way: the pair is (body path:line, guard path:line), however the body phrases it.
    for sentence in re.findall(r"[^\n#]{16,120}", text):
        phrase = sentence.strip()
        found = _asserting_guard(root, relpath, {phrase}, _superseded_registry(root))
        if found is not None:
            return found
    return None


def _is_guard_candidate(relpath: str) -> bool:
    """A live guard is a test module: a `tests/` segment on the path, and a Python file."""
    parts = relpath.split("/")
    return relpath.endswith(".py") and "tests" in parts


def _shipped_guards(root: Path):
    """The checkout's two shipped guard trees, as a fallback for a surface without one."""
    found = []
    for base in ("tests", ".specify/tests"):
        tree = root / base
        if tree.is_dir():
            found.extend(_rel(root, path) for path in sorted(tree.rglob("*.py")))
    return found


def _first_line(text: str) -> int:
    return 1


#: A guard line that *asserts* something. C-104's shape is "the old text is still asserted
#: by a live guard": a line that only names the file (its module docstring, a mention) is a
#: pointer, not an assertion, and must not turn every guard into a finding.
GUARD_ASSERT_RE = re.compile(
    r"(\bassert\b|\bshould\b|\bmust\b|\bexpect\b|\.assert_|==|!=|raises|\bis True\b"
    r"|\bis False\b|\bin text\b|MUST\b)", re.IGNORECASE)


def _asserting_guard(root: Path, body: str, terms, registry):
    """The live guard that names this body **and** asserts its old behaviour.

    The pair C-104 demands is (body path:line, guard path:line): the guard must both *name*
    the superseded carrier and carry an *assertion* that still demands the old reading. The
    guard is searched for under the review surface (a `tests/` file the declaration reaches),
    because the surface is the only place a reading comes from (C-605); when the surface
    carries no `tests/` tree at all -- the shipped surface includes `.specify/specs`, and the
    checkout's own `tests/` is beside it -- the two shipped locations are the fallback.
    """
    terms = {term for term in terms if term and term not in body}
    if not terms:
        return None
    surface = getattr(_asserting_guard, "candidates", None)
    if surface is None:
        surface = _shipped_guards(root)
    # A guard *names* the body; it is not the body, so it never searches for its own path.
    candidates = [relpath for relpath in surface
                  if _is_guard_candidate(relpath) and relpath != body]
    for relpath in candidates:
        if relpath in registry:
            continue
        path = root / relpath
        text = _read(path)
        if not text or body not in text:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if not GUARD_ASSERT_RE.search(line):
                continue
            for term in sorted(terms):
                if term in line and term not in body:
                    return {"path": relpath, "line": number, "guard": term,
                            "asserts": line.strip()[:160]}
    return None


#: An assignment that is followed by a command on the same line is an invocation's input.
_ASSIGNMENT = re.compile(r"^[A-Z_][A-Z0-9_]*=[A-Za-z0-9_.:/-]+$")


def _is_command_line(line: str) -> bool:
    """`True` when the line is an invocation rather than a definition statement."""
    stripped = line.strip().lstrip("$>").strip()
    if stripped.startswith(("export ", "set ", "env ")):
        return True
    head = stripped.split("#", 1)[0].strip()
    words = head.split()
    if not words:
        return False
    return "=" in words[0] and not _ASSIGNMENT.match(head)


def class_multi_owner(root: Path, candidates):
    """One constant independently stated at two or more live sites with different values.

    The axis is the *named binding* (`name: value` / `name = value` inside a markdown code
    fence or a live script), the values must differ, and neither site may pin the other by
    pointer -- a restatement that agrees is a pointer, a restatement that disagrees is a
    second owner.
    """
    entries = []
    # Two shapes only: a YAML-ish `NAME: value` line (markdown front matter / a table of
    # settings) and a code line `NAME = value`. A transcript line (`$ NAME=...`, `export ...`),
    # a fenced block and a table cell are excluded by shape -- none states a value on the axis
    # C-104 names (D1-D6, F4 all read a definition, never a command or a quoted output).
    binding = re.compile(r"^(?:[>`\s]*([A-Z][A-Z0-9_]{2,}):\s+([A-Za-z0-9_.:/-]+)\s*$"
                         r"|^([A-Z][A-Z0-9_]{2,})\s*=\s*([A-Za-z0-9_.:/-]+))")
    seen = {}
    for relpath in candidates:
        if not relpath.endswith((".md", ".py", ".sh")):
            continue
        if relpath.startswith(".specify/scripts/python/non-disposable-check.py"):
            continue
        text = _read(root / relpath)
        if not text:
            continue
        in_fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                # A fenced block is a transcript, a sample output or a template the body
                # *quotes*; the reading C-104 names is a definition the body states, and a
                # quoted run's `BRANCH: feature/xyz` is that run's output, not a second owner.
                continue
            raw = line.rstrip()
            if _is_command_line(raw):
                # `BRANCH=main some-command --flag`, `export NAME=value`, `FOO=1 make` — an
                # invocation states an *input*, never a definition (D1-D6, F4 read
                # definitions). Only a bare assignment is a statement on the axis.
                continue
            match = binding.match(raw)
            if not match:
                continue
            name = match.group(1) or match.group(3)
            value = match.group(2) or match.group(4)
            seen.setdefault(name, []).append((relpath, number, value))
    for name, sites in sorted(seen.items()):
        values = sorted({value for _, _, value in sites})
        if len(values) < 2:
            continue
        # One entry per *name*, not per restatement: C-104 asks for two sites and two
        # values. The pair is the first site declaring each of the two values, so a quoted
        # transcript further down the file cannot turn one defect into forty (C-102: a
        # defect reported twice stays two entries, not n).
        first = {}
        for site in sorted(sites):
            first.setdefault(site[2], site)
        relpath, number, value = first[values[1]]
        owner_path, owner_line, owner_value = first[values[0]]
        entries.append(make_entry(
            "multi-owner", "semantic", relpath, number,
            [{"path": relpath, "line": number, "name": name, "value": value},
             {"path": owner_path, "line": owner_line, "name": name, "value": owner_value}],
            severity="HIGH", name=name))
    return entries


CLASS_ORDER = (
    "superseded-live", "multi-owner", "orphan-path", "renumber-live-binding",
    "status-unreadable", "false-closed-set", "stale-constant", "deferral-marker",
)
CLASS_HANDLERS = {
    "superseded-live": class_superseded_live,
    "multi-owner": class_multi_owner,
    "orphan-path": class_orphan_path,
    "renumber-live-binding": class_renumber_live_binding,
    "status-unreadable": class_status_unreadable,
    "false-closed-set": class_false_closed_set,
    "stale-constant": class_stale_constant,
    "deferral-marker": class_deferral_marker,
}


# ------------------------------------------------------------------------------------------- #
# the run: one model, two projections (C-701)
# ------------------------------------------------------------------------------------------- #
#: The three states that say "not decided, and visible" (`data-model.md` § Entry State
#: Machine). `disposed` and `exempt` are the only two that close an entry, and `exempt` only
#: closes it until its expiry reading re-opens it.
NOT_CLOSED_STATES = ("open", "unevaluated", "unconfirmed")
CLOSING_STATES = ("disposed", "exempt")


def derive_closed(entries, shards, dispositions) -> bool:
    """C-705 / E-2's `closed`, derived from the run and never stored independently.

    Four limbs, each a reading rather than an opinion:

    1. an entry in `open` / `unevaluated` / `unconfirmed` is not closed;
    2. an `unevaluated` shard is not closed (its empty entry list is not "no findings");
    3. an entry outside the state machine's closed set is not a state, so it cannot close;
    4. E-1's two-valued invariant holds for every entry that carries a state:
       `state: disposed` ⟺ `disposition` is a member of the owner page's closed set, and
       every other state carries `disposition: null`. An entry that claims a closure it does
       not have (a `disposed` entry with no disposition, or an `exempt` one with no in-force
       exemption reading) leaves the run open.
    """
    members = set(dispositions or ())
    for entry in entries:
        if entry.get("state") in NOT_CLOSED_STATES:
            return False
        if entry.get("state") not in CLOSING_STATES:
            return False
        if entry["state"] == "disposed" and entry.get("disposition") not in members:
            return False
        if entry["state"] != "disposed" and entry.get("disposition") is not None:
            return False
        if entry["state"] == "exempt":
            reading = entry.get("exemption_reading") or {}
            if reading.get("reason_code") != "exemption-in-force":
                return False
    for shard in shards:
        if shard.get("state") == "unevaluated":
            return False
    return True


#: C-606's naming formula: `s{index:03d}-of-{n:03d}`.
SHARD_ID_RE = re.compile(r"^s(\d{3})-of-(\d{3})$")


def shard_ids(count: int):
    return ["s%03d-of-%03d" % (index, count) for index in range(count)]


def entry_shard(entry, candidate_set, count: int) -> str:
    """C-606: the shard of the file that carries the entry's reading.

    The shard subject is the file, never the class or the body, so the key is `entry_key`.
    A body-level key (a spec directory, a team directory) is a path *prefix* of its carriers;
    it rides with the shard holding those files, which is what "one path has one shard" means
    for a reading that names a body. The two entries on one body therefore land together, and
    the union of the shards is the whole-surface entry set, by `entry_id`.
    """
    key = entry_key(entry)
    if key in candidate_set:
        return shard_of(key, sorted(candidate_set), count)
    prefix = key.rstrip("/") + "/"
    under = sorted(path for path in candidate_set if path.startswith(prefix))
    if under:
        return shard_of(under[0], sorted(candidate_set), count)
    return ""


def _shard_anchors(entry, judged) -> bool:
    chosen, candidate_set, count = judged
    return entry_shard(entry, candidate_set, count) in chosen


def shard_of(relpath: str, sorted_paths, count: int) -> str:
    """Membership is a pure function of the sorted path list (C-606)."""
    return shard_ids(count)[sorted_paths.index(relpath) % count] if count else shard_ids(1)[0]


def run(args) -> dict:
    root = resolve_root(args.root)
    roots, declaration_path, declaration_status = load_surface(root, args.declaration)
    readings, candidates, excluded, missing, siblings = survey(root, roots)

    classes, classes_source = resolved_classes(root)
    dispositions = owner_dispositions(root)
    if args.roots:
        return {"action": "roots", "roots": readings, "declaration": declaration_path,
                "declaration_status": declaration_status}

    if args.emit_categories:
        # C-101 / C-604: the closed class set is the owner page's, read through the engine.
        # The action judges no tree, so it answers the same whether or not a root is named;
        # the human form is the set, one class per line.
        return {"action": "emit-categories", "classes": classes,
                "classes_source": classes_source,
                "detections": ["deterministic", "semantic"],
                "dispositions": dispositions, "states": list(STATES),
                "owner": OWNER_PAGE_REL}

    if not candidates:
        # C-603: the empty candidate set has exactly one exit code, 2, and the reason names
        # the declaration -- with the coverage declaration printed above it, because
        # "declared nothing" and "found nothing" must not look alike (SC-014 / FR-011).
        record = {
            "action": "judge",
            "coverage": {"roots": readings, "candidates": 0, "excluded": excluded,
                         "missing_roots": missing, "undeclared_siblings": siblings,
                         "declaration": declaration_path,
                         "declaration_status": declaration_status},
            "surface_digest": _sha(""),
            "classes": {name: {"count": 0, "roots": [r["path"] for r in readings]}
                        for name in classes},
            "entries": [], "shards": [], "closed": False,
            "relocated": {"count": 0, "reason": "no candidates, so no registry row is read"},
            "not_closed": {"open": 0, "unconfirmed": 0, "unevaluated": 0, "shards": 0},
            "questions": {
                "what_was_looked_at": {"declared_roots": [r["path"] for r in readings],
                                       "candidates": 0,
                                       "excluded": excluded, "missing_roots": missing,
                                       "undeclared_siblings": siblings,
                                       "declaration": declaration_path},
                "what_was_found": {"total": 0,
                                   "by_class": {name: 0 for name in classes},
                                   "by_state": {state: 0 for state in STATES}},
                "what_is_proposed": [],
                "what_is_not_done": {"open": 0, "unconfirmed": 0, "unevaluated": 0,
                                     "closed_by_exemption": 0, "disposed": 0, "shards": 0},
            },
            "vocabulary": {"classes": classes, "classes_source": classes_source,
                           "dispositions": owner_dispositions(root),
                           "states": list(STATES),
                           "detections": ["deterministic", "semantic"]},
        }
        if args.json:
            print(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(render_human(record))
        raise InputError("the surface declared no candidates: %s declares %d roots, none "
                         "with a file" % (declaration_path, len(roots)))

    requested = list(args.scope or [])
    chosen, judged = None, candidates
    if requested:
        # C-606: the shard id names the partition, so `n` is read from the id itself
        # (`s001-of-004` → n = 4). No second option carries it; a run that wanted another
        # partition would name another id.
        counts = set()
        for scope in requested:
            match = SHARD_ID_RE.match(scope)
            if not match:
                raise InputError("--scope %r is not a shard id of the form "
                                 "s{index:03d}-of-{n:03d}" % scope)
            if int(match.group(1)) >= int(match.group(2)):
                raise InputError("--scope %r: the shard index must be below its count n"
                                 % scope)
            counts.add(int(match.group(2)))
        if len(counts) > 1:
            raise InputError("--scope names shards of two different partitions %s: one run "
                             "has one shard count" % sorted(counts))
        count = counts.pop()
        if count > len(candidates):
            raise InputError("--scope requests n=%d over %d candidates: an empty shard cannot "
                             "be part of a partition" % (count, len(candidates)))
        ids = shard_ids(count)
        for scope in requested:
            if scope not in ids:
                raise InputError("--scope %r is not one of this run's shards: %s"
                                 % (scope, ", ".join(ids)))
        # C-606: assignment is a pure function of the *whole* sorted path set, so the
        # partition is computed once and then restricted — taking the subset first would
        # renumber the ordinals and move every path into another shard.
        chosen = set(requested)
        judged = [p for p in candidates if shard_of(p, candidates, count) in chosen]
        judged_set = (chosen, frozenset(candidates), count)
        if not judged:
            raise InputError("--scope %s is an empty shard" % ", ".join(requested))

    # The declared surface is the one place a reading comes from (C-605): the guard search
    # reads from it, and `_shipped_guards` is only the fallback for a surface with no
    # `tests/` segment at all.
    _asserting_guard.candidates = list(candidates)

    entries, shards, stray = [], [], {}
    for name in CLASS_ORDER:
        handler = CLASS_HANDLERS[name]
        try:
            # C-606: every class reads the *whole* candidate set; the shard restricts what is
            # reported, never what is read. Three classes (renumber-live-binding,
            # status-unreadable, multi-owner) compare a site against the other candidates, so
            # handing them the shard subset would move their verdicts with `n`, and C-606
            # requires the entry set by `entry_id` to be invariant under any partition. The
            # filter below is the shard: a candidate belongs to the shard by its *path*, so
            # every entry anchored on that path comes along whatever class produced it.
            emitted = handler(root, candidates)
        except InputError:
            raise
        except Exception as exc:  # noqa: BLE001 - unreadable input degrades, never vanishes
            shards.append({"class": name, "state": "unevaluated", "reason": str(exc)})
            emitted = [make_entry(name, "deterministic", OWNER_PAGE_REL, 0,
                                  [{"path": OWNER_PAGE_REL, "line": 0}],
                                  severity="MEDIUM", state="unevaluated")]
        for entry in emitted:
            # C-101: a class the owner page does not declare is an `unknown-class` finding.
            # The engine does not rename it -- a renamed defect is a silently passed check --
            # and it does not silently drop it either: the class name stays on the entry and
            # the report gains one `unknown-class` finding whose evidence names the class and
            # every entry that carried it (`stray_classes` below).
            if entry["category"] not in classes:
                stray.setdefault(entry["category"], []).append(
                    {"path": entry["path"], "line": entry["line"]})
        entries.extend(emitted)
    for name, sites in sorted(stray.items()):
        first = sites[0]
        entries.append(make_entry(
            "unknown-class", "deterministic", first["path"], first["line"],
            [{"path": site["path"], "line": site["line"], "stray_class": name}
             for site in sites],
            severity="HIGH", state="unevaluated", emitted_category=name,
            state_reason="class-not-declared-by-the-owner-page"))

    # C-703: `entry_id` is the merge key, so two entries with the same id are ONE defect seen
    # twice. The merge keeps the first envelope and takes the union of the evidence refs (a
    # reading is never dropped for arriving second), and names the reading lines it absorbed:
    # `path:line` stays the anchor, `markdown_lines` carries every line the evidence names.
    merged = {}
    for entry in entries:
        key = (entry["entry_id"], entry["category"])
        if key not in merged:
            merged[key] = entry
            continue
        first = merged[key]
        seen = {(ref.get("path"), ref.get("line"), ref.get("quote")) for ref in
                first["evidence_refs"]}
        for ref in entry["evidence_refs"]:
            if (ref.get("path"), ref.get("line"), ref.get("quote")) not in seen:
                first["evidence_refs"].append(ref)
    entries = [merged[key] for key in sorted(merged)]
    for entry in entries:
        lines = sorted({ref["line"] for ref in entry["evidence_refs"]
                        if isinstance(ref.get("line"), int) and ref["line"] > 0
                        and not ref.get("pair")})
        if lines:
            entry["markdown_lines"] = lines

    # C-102 says each entry carries one class, so a body that reads as several classes is
    # several entries on as many path:line readings, and the `entry_id` keeps them apart.
    # Such a body carries *two* lines per class entry only because one line holds two
    # independent readings (corpus E4's self-refuted identity, corpus E's two claims on one
    # page): the state machine's `unevaluated` is the value that says *visible, not decided*
    # (C-704), and it marks exactly that case at `entry_id` level, never at path level -- a
    # path-level mark would make "one path carries four findings" (the normal C-102 shape)
    # indistinguishable from "one entry carries two claims it did not separate".
    # The reading runs over the *whole* entry set before the shard filter, exactly like the
    # classes themselves: otherwise the same entry would flip between states depending on how
    # the tree was cut, and C-606 requires the entry set by `entry_id` to be invariant under n.
    for entry in entries:
        if entry["state"] != "open" or entry.get("state_reason"):
            # A class that already decided the state (the exemption model's `exempt` and
            # `unevaluated` readings, C-104's pair) is not re-judged here: the reading that
            # knows why is the one that writes the state (`data-model.md` § Entry State
            # Machine: `unevaluated` is "the detector could not judge", which is a fact about
            # the *detector*, never about how many lines an entry cites).
            continue
        same_line_readings = sum(
            1 for ref in entry["evidence_refs"]
            if isinstance(ref.get("line"), int) and ref["line"] > 0
            and ref["line"] != entry["line"] and not ref.get("pair")
            and ref.get("path") == entry["path"])
        if same_line_readings >= 1:
            entry["state"] = "unevaluated"
            entry["state_reason"] = "one-entry-carries-two-independent-readings"

    if chosen is not None:
        entries = [entry for entry in entries if _shard_anchors(entry, judged_set)]

    by_class = {name: {"count": 0, "roots": [r["path"] for r in readings]} for name in classes}
    for entry in entries:
        by_class.setdefault(entry["category"], {"count": 0, "roots": []})
        by_class[entry["category"]]["count"] += 1

    not_closed = {
        "open": sum(1 for e in entries if e["state"] == "open"),
        "unconfirmed": sum(1 for e in entries if e["state"] == "unconfirmed"),
        "unevaluated": sum(1 for e in entries if e["state"] == "unevaluated"),
        "closed_by_exemption": sum(1 for e in entries if e["state"] == "exempt"),
        "disposed": sum(1 for e in entries if e["state"] == "disposed"),
        "shards": sum(1 for s in shards if s["state"] == "unevaluated"),
    }
    # C-705's derivation, and nothing else: a run is `closed` only when every review state
    # that says "not decided" is empty. A report that states `closed: true` over an `open`,
    # `unevaluated` or `unconfirmed` entry (or an `unevaluated` shard) is a claim it cannot
    # prove. `derive_closed` also enforces E-1's two-valued invariant on every entry that
    # carries a state, so a `disposed` entry without a set-member `disposition` (or a
    # non-`disposed` entry that claims one) can never be counted as closed. There is no
    # "reviewed by a human" and no "kept as is" field: neither is a state (FR-009).
    closed = derive_closed(entries, shards, dispositions)
    reloc_rows = [r for r in registry_rows(root) if r["status"] == RELOCATED_STATUS]

    return {
        "action": "judge",
        "coverage": {
            "roots": readings,
            "candidates": len(judged),
            "surface_candidates": len(candidates),
            "excluded": excluded,
            "missing_roots": missing,
            "undeclared_siblings": siblings,
            "declaration": declaration_path,
            "declaration_status": declaration_status,
        },
        "surface_digest": _sha("\n".join(candidates)),
        "classes": by_class,
        "entries": entries,
        "shards": shards,
        "closed": closed,
        "relocated": {
            "count": len(reloc_rows),
            "reason": "a relocated row has no live spec directory, so there is no closure "
                      "verdict to compare it against",
        },
        "not_closed": not_closed,
        # C-705's four reader questions live at the ENVELOPE level, not inside a sub-block:
        # a reader who does not take part in the run must answer all four from the report
        # without opening another artifact.
        "questions": {
            "what_was_looked_at": {
                "declared_roots": [r["path"] for r in readings],
                "candidates": len(judged),
                "surface_candidates": len(candidates),
                "excluded": excluded,
                "missing_roots": missing,
                "undeclared_siblings": siblings,
                "declaration": declaration_path,
            },
            "what_was_found": {
                "total": len(entries),
                "by_class": {name: row["count"] for name, row in by_class.items()},
                "by_state": {state: sum(1 for e in entries if e["state"] == state)
                             for state in STATES},
            },
            "what_is_proposed": sorted({e["suggested_disposition"] for e in entries}),
            "what_is_not_done": dict(not_closed),
        },
        "vocabulary": {"classes": classes, "dispositions": dispositions,
                       "states": list(STATES), "detections": ["deterministic", "semantic"]},
    }


def render_human(record) -> str:
    if record["action"] == "roots":
        return "\n".join("%s present=%s count=%d" % (r["path"], r["present"], r["count"])
                         for r in record["roots"])
    if record["action"] == "emit-categories":
        return "\n".join(record["classes"])
    coverage = record["coverage"]
    lines = ["coverage: %d roots, %d candidates, declaration %s"
             % (len(coverage["roots"]), coverage["candidates"], coverage["declaration"])]
    for reading in coverage["roots"]:
        lines.append("  root %s present=%s count=%d"
                     % (reading["path"], reading["present"], reading["count"]))
    for item in coverage["excluded"]:
        lines.append("  excluded %s (%s)" % (item["path"], item["reason"]))
    for item in coverage["missing_roots"]:
        lines.append("  missing %s (%s)" % (item["path"], item["reason"]))
    for item in coverage["undeclared_siblings"]:
        lines.append("  hint %s (%s)" % (item["path"], item["reason"]))
    for name, reading in record["classes"].items():
        lines.append("class %s count=%d" % (name, reading["count"]))
    for entry in record["entries"]:
        lines.append("entry %s %s:%d %s" % (entry["category"], entry["path"], entry["line"],
                                            entry["state"]))
    lines.append("relocated: count=%d" % record["relocated"]["count"])
    # C-701: every JSON count appears in the text form, so the four questions are answered
    # here too rather than left to the machine projection.
    questions = record.get("questions") or {}
    looked = questions.get("what_was_looked_at") or {}
    lines.append("looked-at: %d declared roots, %d candidates, %d excluded, %d missing"
                 % (len(looked.get("declared_roots") or []), looked.get("candidates", 0),
                    len(looked.get("excluded") or []), len(looked.get("missing_roots") or [])))
    found = questions.get("what_was_found") or {}
    lines.append("found: total=%d" % found.get("total", 0))
    for state, count in sorted((found.get("by_state") or {}).items()):
        lines.append("state %s count=%d" % (state, count))
    lines.append("proposed: %s" % (", ".join(questions.get("what_is_proposed") or []) or "-"))
    for key, value in sorted(record["not_closed"].items()):
        lines.append("%s=%d" % (key, value))
    lines.append("closed: %s" % ("true" if record["closed"] else "false"))
    return "\n".join(lines)


def _version_line() -> str:
    """The framework version, re-derived the way `script_interface_cli` does (C-36 style).

    This file carries no version literal: it walks up to the nearest `pyproject.toml` beside a
    `.git` entry and reads `version = "..."` from it. When neither exists the line degrades to
    `unknown` -- a readable answer, never a wrong one.
    """
    here = Path(__file__).resolve()
    for parent in (here.parent, ) + tuple(here.parents):
        if not (parent / ".git").exists():
            continue
        manifest = parent / "pyproject.toml"
        if not manifest.is_file():
            continue
        match = re.search(r'^\s*version\s*=\s*"([^"]+)"', _read(manifest), re.MULTILINE)
        if match:
            return match.group(1)
    return "unknown"


#: C-604's eight argument rows, exactly. The list is the engine's own statement of the
#: calling surface; `main` passes it to the script-interface guard, so an option outside it is
#: rejected with exit 2 rather than accepted by argparse's abbreviation matching.
DECLARED_ARGUMENTS = ("--root", "--json", "--scope", "--roots", "--emit-categories",
                      "--declaration", "--help", "--version")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only non-disposable review over the declared .specify/ roots.",
        epilog=(
            "declared options (the closed eight-row surface, C-604):\n"
            "  --root PATH          repository root\n"
            "  --json               machine-readable report on stdout\n"
            "  --scope SHARD        judge one shard, id s{index:03d}-of-{n:03d}\n"
            "  --roots              print the declared root set and stop, exit 0\n"
            "  --emit-categories    print the closed class set and stop, exit 0\n"
            "  --declaration PATH   override the review-surface fact (fixtures only)\n"
            "  -h, --help           this usage\n"
            "  --version            one version line\n"
            "no other option is declared: `--scope-count` is not a ninth row, because the "
            "shard count travels in the shard id the run requests.\n"),
        allow_abbrev=False)
    parser.add_argument("--root", default="", help="repository root")
    parser.add_argument("--json", action="store_true", help="machine-readable report on stdout")
    parser.add_argument("--scope", action="append", default=[], metavar="SHARD",
                        help="shard id s{index:03d}-of-{n:03d} (repeatable)")
    parser.add_argument("--roots", action="store_true",
                        help="print the declared root set and exit 0 without judging")
    parser.add_argument("--emit-categories", action="store_true",
                        help="print the closed class set and exit 0 without judging")
    parser.add_argument("--declaration", default="", metavar="PATH",
                        help="override the review-surface fact file (fixtures only)")
    # `--version` is answered by `main()` before the parser, exactly as the other 092-era
    # scripts do; declaring it here as well keeps `--help` a truthful statement of the eight
    # rows (C-604) without changing the answering path.
    parser.add_argument("--version", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `--version` is a script-interface answer, not a review action (C-604): it must be
    # answered before argparse sees it, and before `--help` is built, or it exits 2.
    if argv[:1] in (["--version"], ["-V"]):
        print("%s %s" % (Path(__file__).name, _version_line()))
        return EXIT_CLEAN
    parser = build_parser()
    _sig_configure(parser, effects="none (read-only)",
                   codes="0 clean, 1 findings, 2 input error")
    # C-604's rejection happens before argparse sees the argv, so `--version` / `--help` are
    # answered even when they arrive beside an undeclared option, and an abbreviation
    # (`--js`, `--roo`) is rejected rather than silently resolved. The guard itself exits 2
    # with the offending token named; `parse_args` below is then reached only by an argv the
    # eight-row surface accepts.
    _sig_guard(argv, declared=list(DECLARED_ARGUMENTS))
    args = parser.parse_args(argv)
    try:
        record = run(args)
    except InputError as exc:
        print("non-disposable-check: input error: %s" % exc, file=sys.stderr)
        return EXIT_INPUT
    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(render_human(record))
    if record["action"] != "judge":
        return EXIT_CLEAN
    return EXIT_FINDINGS if (record["entries"] or not record["closed"]) else EXIT_CLEAN


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


if __name__ == "__main__":
    sys.exit(main())
