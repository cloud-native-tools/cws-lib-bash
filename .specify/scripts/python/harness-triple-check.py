#!/usr/bin/env python3
"""Judge the declaration layer: `coverage`, `verify`, `lookup`. Read-only, stdlib only.

Feature 084 (harness triple structure). Contract: `contracts/harness-triple-check.contract.md`
C-026…C-041. Value domains (exit codes, kinds, states, reasons, required keys) are **not** in this file:
they are read from `.specify/shared/declarations/contract.yaml` through `declaration_reader.load_contract`.

**Read-only (C-026/C-039).** This engine opens no write point of any kind. Its only outputs are stdout,
stderr, and — only when `--json-out` is given — one JSON report at the path asked for. No model
judgement, no network, no subprocess, no environment-dependent branch: the same tree and the same
declaration set always produce the same verdict, and two consecutive `coverage` runs print byte-identical
output (C-029/C-038).

**The read point is a textual locator, not a proof of semantics (C-032, `data-model.md` E-6 R-6).**
Completeness condition (c) is satisfied when a consumer engine's source text references the shared read
entry (`declaration_reader`) *and* the fact's slug. That is decidable by a program and it is deliberately
weak: a green (c) says "the read point is locatable", never "the engine's use of the value is correct".
Reading it as a proof of semantics is the false green this feature exists to remove.

**Six findings, no seventh (FR-017 / C-035).** The instance form of each finding is
``code + ": " + arguments``, and the codes are carried here the way
`.specify/scripts/python/closure-acceptance-check.py` carries its reason codes: the literal template text and its
argument grammar are owned by `requirements.md` § Shared Strings, and
`tests/contract/test_harness_triple_structure.py` derives its expectations from that table instead of
re-spelling anything. Two of the six are filled by conditions whose own name is not in the set, and each
choice is named here so review can challenge the boundary rather than discover it later:

* **Two declarations claiming one slug** is emitted as `duplicated-fact-literal` with the *declaration*
  path as its argument. The residual-literal side of that template (a carrier restating the value) is the
  reused `duplicate-fact` face of `.specify/scripts/python/doc-consistency-check.py` and is **delegated**, never
  reimplemented: FR-010 forbids a second scanner and C-038 forbids a subprocess, so this engine reports
  that face as `residual-literals: delegated` and never as a pass.
* **A unit named by both a declaration and an exclusion row** (`data-model.md` E-2 R-4) is emitted as
  `unclassified-candidate`: its disposition cannot be derived at all, which is what that code names.

**Exit codes (C-036).** `0` no finding; `1` at least one finding; `2` input error or degraded wiring. In
`coverage` a `pending` unit is a **reading, not a failure** (C-043): the exit-0 criterion is "zero
unclassified candidates", never "zero pending".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import declaration_reader as declarations  # noqa: E402  (import follows the sys.path entry above)

#: The candidate screen's three carrier surfaces (C-030). `.specify/shared/definitions/*.md` is deliberately absent:
#: definition documents own facts, they do not get a disposition.
CARRIER_PATTERNS = (
    ".specify/templates/commands/*.md",
    "skills/external/*/SKILL.md",
    "skills/internal/*/SKILL.md",
    ".specify/shared/workflow/*.md",
)

#: C-030's engine-reference test: a text token pointing at a framework-internal deterministic engine.
ENGINE_REFERENCE = re.compile(
    r"(.specify/scripts/python/[A-Za-z0-9_.-]+\.py"
    r"|skills/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/scripts/[A-Za-z0-9_.-]+)")

#: The six finding codes (see the module docstring for the argument each one takes).
FINDING_CODES = {
    "STR-009": "third-layer-missing",
    "STR-010": "declaration-outside-subset",
    "STR-011": "duplicated-fact-literal",
    "STR-012": "exclusion-anchor-unresolvable",
    "STR-013": "unclassified-candidate",
    "STR-014": "declaration-absent",
}

IN_SCOPE = "in-scope"
EXCLUDED = "excluded"
UNCLASSIFIED = "unclassified"


class InputError(Exception):
    """An input the check cannot run on: exit 2 with a label, never a traceback (C-037)."""


def exit_codes(repo):
    """C-036 — the three codes are read from the contract, never restated here.

    A degraded layer cannot be asked, and the only code that path can report is the input error, so the
    fallback carries exactly that one value.
    """
    try:
        contract = declarations.load_contract(repo)
    except declarations.DeclarationError:
        return {"input-error": 2}
    return {str(key): int(value) for key, value in (contract.get("exit_codes") or {}).items()}


def finding(identity, *args):
    """Render one finding instance: the code, `": "`, and the arguments joined by ``@``."""
    return "%s: %s" % (FINDING_CODES[identity], "@".join(str(arg) for arg in args))


# --------------------------------------------------------------------------- #
# the tree under judgement
# --------------------------------------------------------------------------- #
def resolve_repo(explicit=None):
    """C-028 — the root is the directory that contains ``.specify/scripts/python/``, never a `.specify` match."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "scripts" / "python" / here.name).is_file():
            return parent
    return here.parents[2]


def carrier_units(repo):
    """Every markdown carrier on the three surfaces that references a framework engine, sorted."""
    units = []
    for pattern in CARRIER_PATTERNS:
        for path in sorted(repo.glob(pattern)):
            rel = path.relative_to(repo).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            engines = sorted(set(ENGINE_REFERENCE.findall(text)))
            if engines:
                units.append({"unit": rel, "text": text, "engines": engines})
    return sorted(units, key=lambda item: item["unit"])


def resolves(repo, value):
    """A path value resolves in the tree: existing file or directory, after normalization (C-010)."""
    text = declarations.normalize_path(value)
    if not text:
        return False
    candidate = (repo / text).resolve()
    return candidate.exists()


def anchor_resolves(repo, anchor):
    """An exclusion anchor is `path` or `path#section`; the path must exist and the section must appear."""
    text = declarations.normalize_path(str(anchor).strip())
    path_text, _, section = text.partition("#")
    if not resolves(repo, path_text):
        return False
    if not section.strip():
        return True
    try:
        body = (repo / path_text).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return section.strip() in body


def has_pointer(text, fact_path):
    """(b) — the carrier points at the declaration (path plus a key path), it does not restate it."""
    normalized = text.replace(".specify/", "")
    if declarations.normalize_path(fact_path) not in normalized:
        return False
    tail = normalized.split(declarations.normalize_path(fact_path), 1)[1]
    return tail.startswith("#/") or "#/" in tail.split("\n", 1)[0]


def has_read_point(repo, engine_path, slug):
    """(c) — the engine's text references the read entry *and* the fact's slug (a textual locator)."""
    path = repo / declarations.normalize_path(engine_path)
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return declarations.READ_ENTRY in text and slug in text


# --------------------------------------------------------------------------- #
# the layer, read once
# --------------------------------------------------------------------------- #
class Layer:
    """Everything one run needs from the declaration layer, plus the findings reading it produced."""

    def __init__(self, repo):
        self.repo = repo
        self.contract = declarations.load_contract(repo)
        self.findings = []

        self.required_fact_keys = list(self.contract.get("required_fact_keys") or [])
        self.required_exclusion_keys = list(self.contract.get("required_exclusion_keys") or [])
        self.fact_kinds = [str(value) for value in (self.contract.get("fact_kinds") or [])]
        self.exclusion_reasons = [str(value) for value in (self.contract.get("exclusion_reasons") or [])]
        codes = {str(key): int(value) for key, value in (self.contract.get("exit_codes") or {}).items()}
        self.exit_ok = codes.get("ok", 0)
        self.exit_finding = codes.get("finding", 1)
        self.exit_input = codes.get("input-error", 2)
        self.complete_state = str((self.contract.get("completeness_states") or ["complete"])[0])
        self.pending_state = str((self.contract.get("completeness_states") or ["complete", "pending"])[1])

        # A declaration outside the subset is a finding about that file (C-008); it must not hide the
        # other declarations, and it must not be argued with: no best-effort parse, no second chance.
        self.parse_errors = []
        self.facts = declarations.load_facts(repo, self.parse_errors)
        for error in self.parse_errors:
            self.findings.append(finding(error.template, error.path))
        self.exclusions = declarations.load_exclusions(repo)

        #: `{slug: [declarations]}`, filled by :meth:`claimed_slugs`; completeness condition (a) reads
        #: it, because "how many declarations claim this fact" is a verdict from the run.
        self.claimed = {}

    # -- facts ------------------------------------------------------------- #
    def check_fact_schema(self):
        """Required keys, unknown keys, the closed kind set, and slug/stem agreement (C-003/C-004)."""
        for fact in self.facts:
            body, rel = fact["body"], fact["path"]
            missing = [key for key in self.required_fact_keys if key not in body]
            if missing:
                raise InputError("%s: missing required key(s) %s" % (rel, ", ".join(missing)))
            unknown = sorted(set(body) - set(self.required_fact_keys) - {"note"})
            if unknown:
                raise InputError("%s: unknown top-level key(s) %s" % (rel, ", ".join(unknown)))
            slug = str(body.get("fact", "")).strip()
            kind = str(body.get("kind", "")).strip()
            if kind not in self.fact_kinds:
                raise InputError("%s: kind %r is outside the closed set" % (rel, kind))
            for key in ("consumers", "former_carriers"):
                value = body.get(key)
                if value is None:
                    body[key] = []
                    continue
                if not isinstance(value, list):
                    raise InputError("%s: %s must be a sequence" % (rel, key))
            shared = set(body.get("consumers") or []) & set(body.get("former_carriers") or [])
            if shared:
                raise InputError(
                    "%s: consumers and former_carriers overlap (%s)" % (rel, ", ".join(sorted(shared))))

    def claimed_slugs(self):
        """`{slug: [facts]}`; a slug claimed twice is the duplicate-declaration finding (STR-011)."""
        claimed = self.claimed
        for fact in self.facts:
            slug = str(fact["body"].get("fact", "")).strip()
            claimed.setdefault(slug, []).append(fact)
        for slug, group in sorted(claimed.items()):
            if len(group) < 2:
                if group[0]["stem"] != slug:
                    raise InputError(
                        "%s: the `fact` key %r must equal the filename stem" % (group[0]["path"], slug))
                continue
            # The claimant is the file whose name matches the slug (C-003's stem rule); with no such
            # file the path-sorted first one claims it. Everything else claiming it is the finding.
            ordered = sorted(group, key=lambda item: (item["stem"] != slug, item["path"]))
            for duplicate in ordered[1:]:
                self.findings.append(finding("STR-011", slug, duplicate["path"]))
        return claimed

    # -- exclusions -------------------------------------------------------- #
    def check_exclusions(self):
        seen = {}
        for row in self.exclusions:
            body, rel, reason = row["body"], row["path"], row["reason"]
            missing = [key for key in self.required_exclusion_keys if key not in body]
            if missing:
                raise InputError("%s: exclusion row missing key(s) %s" % (rel, ", ".join(missing)))
            if reason not in self.exclusion_reasons:
                raise InputError("%s: %r is not a closed exclusion reason" % (rel, reason))
            unit = str(body.get("unit", "")).strip()
            if unit in seen:
                raise InputError("%s: unit %r is named by two exclusion rows" % (rel, unit))
            seen[unit] = row
            carrier = str(body.get("carrier", "")).strip()
            if carrier and not resolves(self.repo, carrier):
                raise InputError("%s: carrier %r does not resolve" % (rel, carrier))
            if not anchor_resolves(self.repo, body.get("anchor", "")):
                self.findings.append(finding("STR-012", unit))
        return seen

    # -- dispositions ------------------------------------------------------ #
    def dispositions(self, exclusions_by_unit):
        """C-031 — fixed order: declaration ⇒ in-scope; else row ⇒ excluded; else unclassified."""
        by_unit = {}
        for fact in self.facts:
            body = fact["body"]
            for key in ("consumers", "former_carriers"):
                for path in body.get(key) or []:
                    by_unit.setdefault(declarations.normalize_path(path), []).append(fact)

        result = {}
        for unit in carrier_units(self.repo):
            name = unit["unit"]
            declared = by_unit.get(name, [])
            row = exclusions_by_unit.get(name)
            if declared and row is not None:
                self.findings.append(finding("STR-013", name))
                result[name] = {"disposition": UNCLASSIFIED, "facts": [], "unit": unit}
                continue
            if declared:
                result[name] = {"disposition": IN_SCOPE, "facts": declared, "unit": unit}
            elif row is not None:
                result[name] = {"disposition": EXCLUDED, "reason": row["reason"], "facts": [],
                                "unit": unit}
            else:
                self.findings.append(finding("STR-013", name))
                result[name] = {"disposition": UNCLASSIFIED, "facts": [], "unit": unit}
        return result

    # -- completeness ------------------------------------------------------- #
    def completeness(self, name, entry):
        """E-6 — the three conditions conjunctively, and the false-green red line enforced here.

        (a) each of the unit's facts is claimed by **exactly one** declaration — the count comes from the
        run (`claimed_slugs`), because *a declaration file existing is not evidence for (a)*; (b) the
        unit's carrier holds a pointer to that declaration; (c) at least one engine named in `consumers`
        holds a locatable read point. A missing read point keeps the unit `pending` even when (a) and (b)
        are green (`data-model.md` § E-6 R-6).

        Schema and subset validity are preconditions rather than conditions here: a fact outside the
        subset never reaches `self.facts` (it is reported as STR-010 and its unit loses the declaration
        that named it), and a fact failing the required keys raises the exit-2 input error in
        :meth:`check_fact_schema` before this runs — so neither can ever be read as `complete`.
        """
        if entry["disposition"] != IN_SCOPE:
            return None, None
        for fact in entry["facts"]:
            slug = str(fact["body"].get("fact", "")).strip()
            if len(self.claimed.get(slug) or []) != 1:
                # Two declarations claiming one fact: (a) fails, and the pending reason names the
                # finding that reports it rather than a silent `complete`.
                return self.pending_state, FINDING_CODES["STR-011"]
            if not has_pointer(entry["unit"]["text"], fact["path"]):
                return self.pending_state, FINDING_CODES["STR-009"]
            body = fact["body"]
            engines = [path for path in (body.get("consumers") or [])
                       if str(path).endswith(".py") or "/scripts/" in str(path)]
            if not any(has_read_point(self.repo, path, slug) for path in engines):
                return self.pending_state, FINDING_CODES["STR-009"]
        return self.complete_state, None

    # -- both-direction consistency (C-033) --------------------------------- #
    def consistency(self, result):
        forward_matched = forward_total = 0
        for fact in self.facts:
            slug = str(fact["body"].get("fact", "")).strip()
            for path in fact["body"].get("consumers") or []:
                forward_total += 1
                if str(path).endswith(".py") or "/scripts/" in str(path):
                    if has_read_point(self.repo, path, slug):
                        forward_matched += 1
                else:
                    target = self.repo / declarations.normalize_path(path)
                    if target.is_file() and has_pointer(
                            target.read_text(encoding="utf-8", errors="ignore"), fact["path"]):
                        forward_matched += 1

        backward_matched = backward_total = 0
        for name, entry in sorted(result.items()):
            text = entry["unit"]["text"].replace(".specify/", "")
            for fact in self.facts:
                slug = str(fact["body"].get("fact", "")).strip()
                if declarations.normalize_path(fact["path"]) not in text and slug not in text:
                    continue
                backward_total += 1
                named = set(declarations.normalize_path(path)
                            for path in (fact["body"].get("consumers") or [])
                            + (fact["body"].get("former_carriers") or []))
                if name in named:
                    backward_matched += 1
        return (forward_matched, forward_total), (backward_matched, backward_total)


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #
def run_coverage(repo):
    layer = Layer(repo)
    layer.check_fact_schema()
    layer.claimed_slugs()
    exclusions_by_unit = layer.check_exclusions()
    result = layer.dispositions(exclusions_by_unit)

    rows = []
    pending = 0
    for name in sorted(result):
        entry = result[name]
        row = {"unit": name, "disposition": entry["disposition"]}
        state, reason = layer.completeness(name, entry)
        if entry["disposition"] == EXCLUDED:
            row["reason"] = entry["reason"]
        if state is not None:
            row["state"] = state
            if reason:
                row["reason"] = reason
            if state == layer.pending_state:
                pending += 1
        row["facts"] = sorted(str(fact["body"].get("fact", "")).strip()
                              for fact in entry["facts"])
        rows.append(row)

    findings = sorted(set(layer.findings))
    blocking = [item for item in findings
                if item.startswith(FINDING_CODES["STR-011"]) or
                item.startswith(FINDING_CODES["STR-012"]) or
                item.startswith(FINDING_CODES["STR-013"]) or
                item.startswith(FINDING_CODES["STR-010"])]
    return {
        "action": "coverage",
        "candidates": len(rows),
        "pending": pending,
        "unclassified": sum(1 for row in rows if row["disposition"] == UNCLASSIFIED),
        "findings": findings,
        "units": rows,
    }, (layer.exit_finding if blocking else layer.exit_ok)


def run_verify(repo):
    layer = Layer(repo)
    layer.check_fact_schema()
    layer.claimed_slugs()
    exclusions_by_unit = layer.check_exclusions()
    result = layer.dispositions(exclusions_by_unit)

    for name in sorted(result):
        entry = result[name]
        state, reason = layer.completeness(name, entry)
        # A pending unit is named by the reason that actually failed (FR-007): a missing declaration or
        # read point is STR-009 for that unit, while a fact claimed twice is already reported as STR-011
        # by `claimed_slugs` — repeating it here under the other code would name the wrong reason.
        if state == layer.pending_state and reason == FINDING_CODES["STR-009"]:
            layer.findings.append(finding("STR-009", name))

    forward, backward = layer.consistency(result)
    findings = sorted(set(layer.findings))
    return {
        "action": "verify",
        "declarations": len(layer.facts),
        "candidates": len(result),
        "consistency_declarations_to_carriers": forward,
        "consistency_carriers_to_declarations": backward,
        "residual_literals": "delegated: doc-consistency-check.py --faces duplicate "
                             "(this engine opens no subprocess and never re-scans)",
        "findings": findings,
    }, (layer.exit_finding if findings else layer.exit_ok)


def run_lookup(repo, unit_id=None, fact_slug=None):
    layer = Layer(repo)
    layer.check_fact_schema()
    layer.claimed_slugs()
    exclusions_by_unit = layer.check_exclusions()

    if fact_slug:
        matched = [fact for fact in layer.facts
                   if str(fact["body"].get("fact", "")).strip() == fact_slug]
        if not matched:
            return {
                "action": "lookup",
                "fact": fact_slug,
                "state": layer.pending_state,
                "findings": [finding("STR-014", fact_slug)],
            }, layer.exit_finding
        fact = matched[0]
        body = fact["body"]
        payload = {
            "action": "lookup",
            "fact": fact_slug,
            "kind": str(body.get("kind", "")).strip(),
            "consumers": [str(path) for path in body.get("consumers") or []],
            "former_carriers": [str(path) for path in body.get("former_carriers") or []],
            "declaration": fact["path"],
        }
        result = layer.dispositions(exclusions_by_unit)
        holders = [name for name, entry in sorted(result.items())
                   if fact_slug in [str(item["body"].get("fact", "")).strip()
                                    for item in entry["facts"]]]
        payload["state"] = layer.pending_state
        for name in holders:
            state, _reason = layer.completeness(name, result[name])
            if state == layer.complete_state:
                payload["state"] = layer.complete_state
        payload["findings"] = sorted(set(layer.findings))
        return payload, (layer.exit_finding if payload["findings"] else layer.exit_ok)

    result = layer.dispositions(exclusions_by_unit)
    entry = result.get(declarations.normalize_path(unit_id))
    if entry is None:
        raise InputError("%r is not a candidate unit on this tree" % unit_id)
    state, reason = layer.completeness(declarations.normalize_path(unit_id), entry)
    payload = {
        "action": "lookup",
        "unit": declarations.normalize_path(unit_id),
        "disposition": entry["disposition"],
        "facts": [{"fact": str(fact["body"].get("fact", "")).strip(),
                   "kind": str(fact["body"].get("kind", "")).strip()} for fact in entry["facts"]],
        "findings": sorted(set(layer.findings)),
    }
    if entry["disposition"] == EXCLUDED:
        payload["reason"] = entry["reason"]
    if state is not None:
        payload["state"] = state
        if reason:
            payload["reason"] = reason
    return payload, (layer.exit_finding if payload["findings"] else layer.exit_ok)


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def render_text(payload):
    """Deterministic, sorted, flat ``key: value`` lines — no time, host, user or locale (C-038)."""
    lines = ["# harness-triple-check — %s" % payload["action"]]
    if payload["action"] == "coverage":
        lines.append("candidates: %d" % payload["candidates"])
        lines.append("pending: %d" % payload["pending"])
        lines.append("unclassified: %d" % payload["unclassified"])
        lines.append("findings: %d" % len(payload["findings"]))
    elif payload["action"] == "verify":
        lines.append("declarations: %d" % payload["declarations"])
        lines.append("candidates: %d" % payload["candidates"])
        lines.append("consistency-declarations-to-carriers: %d/%d"
                     % payload["consistency_declarations_to_carriers"])
        lines.append("consistency-carriers-to-declarations: %d/%d"
                     % payload["consistency_carriers_to_declarations"])
        lines.append("residual-literals: %s" % payload["residual_literals"])
        lines.append("findings: %d" % len(payload["findings"]))
    else:
        for key in ("unit", "disposition", "state", "reason", "fact", "kind", "declaration"):
            if key in payload:
                lines.append("%s: %s" % (key, payload[key]))
        for key in ("consumers", "former_carriers"):
            if key in payload:
                lines.append("%s: %s" % (key, ", ".join(payload[key]) or "-"))
        for item in payload.get("facts") or []:
            lines.append("fact: %s kind=%s" % (item["fact"], item["kind"]))
        lines.append("findings: %d" % len(payload["findings"]))

    for row in payload.get("units") or []:
        lines.append("unit: %s" % row["unit"])
        lines.append("disposition: %s" % row["disposition"])
        if "state" in row:
            lines.append("state: %s" % row["state"])
        if "reason" in row:
            lines.append("reason: %s" % row["reason"])
        for slug in row["facts"]:
            lines.append("fact: %s" % slug)

    for item in payload["findings"]:
        lines.append("finding: %s" % item)
    return "\n".join(lines)


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

def main(argv=None):
    _sig_guard(argv, declared=['--action', '--repo', '--format', '--json-out', '--unit-id', '--fact'])  # answer --version / reject an undeclared option
    parser = argparse.ArgumentParser(
        description="Judge the declaration layer (read-only; three actions, three exit codes).")
    _sig_configure(parser)

    parser.add_argument("--action", required=True, choices=("coverage", "verify", "lookup"))
    parser.add_argument("--repo", default=None,
                        help="repository root (default: the directory holding .specify/scripts/python/)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--json-out", default=None,
                        help="write JSON report here (triggers the write)")
    parser.add_argument("--unit-id", default=None, help="lookup: a carrier path")
    parser.add_argument("--fact", default=None, help="lookup: a fact slug")
    args = parser.parse_args(argv)

    repo = resolve_repo(args.repo)
    codes = exit_codes(repo)

    if args.action == "lookup" and (bool(args.unit_id) == bool(args.fact)):
        print("input-error: lookup takes exactly one of --unit-id / --fact", file=sys.stderr)
        return codes["input-error"]
    try:
        if args.action == "coverage":
            payload, status = run_coverage(repo)
        elif args.action == "verify":
            payload, status = run_verify(repo)
        else:
            payload, status = run_lookup(repo, args.unit_id, args.fact)
    except declarations.DeclarationError as error:
        print("input-error: %s" % error, file=sys.stderr)
        return codes["input-error"]
    except InputError as error:
        print("input-error: %s" % error, file=sys.stderr)
        return codes["input-error"]

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(render_text(payload))
    return status


if __name__ == "__main__":
    sys.exit(main())
