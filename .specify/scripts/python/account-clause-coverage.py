#!/usr/bin/env python3
"""Account clause and FR coverage for a feature spec, as set differences over named items.

Program-First discipline (.specify/shared/guidelines/token-efficiency.md): "every contract clause
is claimed by exactly one task row" is a fixed set relation, so it is computed here once
instead of being re-asserted in prose on every run.

Two lanes, deliberately never merged into one count (FR-026) — their universes come from
different owners and so do their claimed subsets:

  clause lane   universe  every contract file under `<corpus-root>/*/contracts/`, cut into
                clause blocks by the forms the syntax owner declares
                (`.specify/shared/definitions/contract-clause-definitions.md`); per-form counts are
                owned by that spec's `notes/clause-form-census.md` and are NOT restated here
                claimed   the `[green: <contract>#<clause>]` declarations on that spec's own
                tasks.md rows, parsed by validate-tasks.py so the mention/fence rules have
                one implementation
  FR lane       universe  the `FR-nnn` definition rows of that spec's requirements.md, read
                outside fenced blocks and inline code spans
                claimed   the `(FR-nnn)` in each clause block's CITATION GROUP — the block's
                last FR/SC-bearing parenthetical — never a task row; FR is not a legal
                `[green:]` target (FR-015/FR-016)

Both lanes call the same sibling extractor, `clause_extract.py`; neither re-implements a
clause rule privately.

Checks performed:
  clause-uncovered  the clause universe minus the claimed subset, printed as a sorted name
                    list one per line with the STR-009 `UNCOVERED:` prefix; fails when any
                    item is new relative to the frozen baseline
  fr-uncovered      the FR universe minus the FRs cited from clause citation groups; fails
                    when non-empty (this lane has no baseline — see research.md A-7)
  clause-unparsable  files that yield no clause id under the owner's forms are NAMED, never
                    silently dropped, and counted into a non-zero companion; fails only for
                    a positive-form file yielding zero clauses, which is parse doubt
  coverage-baseline-delta  `comm -13 <baseline> <live uncovered>`, computed internally and
                    reported as names; fails when the delta is non-empty OR the baseline
                    file is absent — an absent baseline is never read as "no exemptions"

The anti-vacuity companion (FR-025): a green run always prints a claimed-clause count and
the scanned-file total beside the empty set, so "empty because right" is distinguishable
from "empty because blind". A corpus with no contract files at all is an input error, not a
green run.

Read-only: every verdict travels on stdout and the exit code. `--freeze` does not write
either — it PRINTS the baseline document (header plus sorted names) for the caller to
redirect, which keeps the write-point count at zero and keeps the frozen name form and the
live name form produced by one code path.

Verdict vocabulary (`status`): `ok` (both lanes empty beyond baseline, companions non-zero),
`uncovered` (at least one blocking item), `baseline-missing` (the frozen name list was not
found), `input-error` (spec dir / requirements.md / contract corpus not usable).

Exit codes:
  0  covered — no uncovered item beyond the frozen baseline, and no uncovered FR
  1  at least one blocking item in either lane
  2  input error, including a missing baseline file (C-21)

Usage:
  python3 .specify/scripts/python/account-clause-coverage.py <spec-dir-or-a-file-inside-it>
  python3 .specify/scripts/python/account-clause-coverage.py --spec-dir DIR [--corpus-root DIR]
                                                    [--baseline PATH] [--json] [--list-named]
  python3 .specify/scripts/python/account-clause-coverage.py DIR --freeze > DIR/coverage-baseline.txt

Freeze the baseline at the FIRST full-tree accounting run, not the first green one: green
would require the baseline while the baseline requires a run, which is circular (C-21).
The frozen面 excludes the spec being accounted, so that spec's own items can be claimed but
never exempted by its own baseline. Comparison is by NAME set, never by count — the same
`comm -13` idiom the frozen test baseline uses, and for the same reason: a count difference
cannot tell new debt from retired debt.

The external idiom MUST run under `LC_ALL=C`. The names are codepoint-sorted (Python's
`sorted`), while glibc collation ignores `#`, `/` and `.` at the first level, so under a
UTF-8 locale `comm` reports the baseline as unsorted and then echoes all of it as the delta
— measured on the real corpus as 665 where the true delta was 182. The internal delta is a
set difference and is locale-independent, so it stays authoritative; `LC_ALL=C` is what
makes the external cross-check agree with it.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

OWNER_DOC = ".specify/shared/definitions/contract-clause-definitions.md"
CENSUS_OWNER = "notes/clause-form-census.md"

STR009 = "UNCOVERED:"
UNCOVERED_FR = "UNCOVERED-FR:"

POSITIVE_FORMS = (
    "md-bold-closed",
    "md-bold-paren",
    "md-heading",
    "yaml-openapi",
    "yaml-assertions",
)
NAMED_FORM = "md-none"
OWNER_FORMS = POSITIVE_FORMS + (NAMED_FORM,)
YAML_SUFFIXES = (".yaml", ".yml")

BASELINE_NAME = "coverage-baseline.txt"

EXIT_OK = 0
EXIT_UNCOVERED = 1
EXIT_INPUT = 2


def _sibling(name: str):
    """Load a sibling script by path.

    By path rather than `import`, because this script runs both as
    `python3 .specify/scripts/python/account-clause-coverage.py` (its own directory is
    `sys.path[0]`) and under `importlib` from a contract test (where it is not). Resolving
    beside `__file__` also keeps a `.specify/` mirror copy on the mirror's own siblings.
    """
    path = Path(__file__).resolve().with_name(name)
    if not path.is_file():
        raise SystemExit(f"input-error: sibling script missing: {path}")
    spec = importlib.util.spec_from_file_location("_acc_sibling_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _corpus_files(corpus_root: Path):
    """Every contract file under `<corpus-root>/*/contracts/`, sorted, as (spec_key, spec_dir, path)."""
    out = []
    if not corpus_root.is_dir():
        return out
    for spec_dir in sorted(p for p in corpus_root.iterdir() if p.is_dir()):
        contracts = spec_dir / "contracts"
        if not contracts.is_dir():
            continue
        for path in sorted(p for p in contracts.rglob("*") if p.is_file()):
            if path.name in ("__pycache__", ".DS_Store") or path.suffix == ".pyc":
                continue
            out.append((spec_dir.name, spec_dir, path))
    return out


def _spec_dir_from(target: Path):
    """Resolve a positional argument to its spec dir: a dir is itself, a file walks up."""
    if not target.exists():
        return target  # let the caller report it as an input error, never guess a parent
    if target.is_dir():
        return target
    for parent in target.resolve().parents:
        if (parent / "requirements.md").is_file() or (parent / "contracts").is_dir():
            return parent
    return target.parent


def _qualified(spec_key: str, spec_dir: Path, path: Path) -> str:
    """The name form both lanes and the baseline share: `<spec-key>/<contract>#<clause>`."""
    return f"{spec_key}/{path.relative_to(spec_dir).as_posix()}"


def _scan(files, extractor):
    """Classify and extract in one pass.

    Returns (per_form, parsed, named, named_names, zero_clause_positive, universe, id_total)
    where `universe` is the set of qualified `<spec>/<contract>#<clause>` names and `named`
    counts every file that yields no clause id — a file that contributes nothing is reported,
    never silently counted as covered (C-8/C-15).

    `id_total` is the count of extracted ids BEFORE set collapse, and the difference between
    it and `len(universe)` is reported, never absorbed. The owner's `yaml-openapi` form names
    a clause by its HTTP method key, and one file may declare the same method under several
    paths, so those ids are not distinct within a file: 8 corpus files repeat a method key and
    24 operations share a name with another. Printing only the set size would under-report the
    denominator by that many and read as a smaller corpus — the exact "empty because blind"
    failure FR-025 exists to prevent, one level down at clause identity. Whether the owner
    syntax should qualify those ids by their path is an open design question (research.md A-8),
    not something an accounting run gets to decide silently.
    """
    per_form = {form: {"files": 0, "clauses": 0} for form in OWNER_FORMS}
    parsed, named, named_names, zero_positive = 0, 0, [], 0
    universe = set()
    id_total = 0
    for spec_key, spec_dir, path in files:
        form = extractor.form_of(path)
        ids = extractor.extract_clauses(path)
        per_form.setdefault(form, {"files": 0, "clauses": 0})
        per_form[form]["files"] += 1
        per_form[form]["clauses"] += len(ids)
        id_total += len(ids)
        qualified = _qualified(spec_key, spec_dir, path)
        if ids:
            parsed += 1
            for cid in ids:
                universe.add(f"{qualified}#{cid}")
        else:
            named += 1
            named_names.append(qualified)
            if form != NAMED_FORM:
                # a positive form that yielded nothing is parse doubt (stream-style yaml,
                # anchors, unexpected indentation): named, never guessed as zero-and-covered
                zero_positive += 1
    return per_form, parsed, named, sorted(named_names), zero_positive, universe, id_total


def _claims_for(spec_dir: Path, validate_tasks, universe, index):
    """(claimed names, unresolved claims) for one spec's own tasks.md.

    The declarations are parsed by validate-tasks.py rather than by a second regex here, so
    the fence and inline-code-span rules — a mentioned tag is not a declared one — have one
    implementation and cannot drift between the guard and the accountant.
    """
    tasks_md = spec_dir / "tasks.md"
    raw = []
    if tasks_md.is_file():
        validate_tasks.validate(tasks_md, claims_out=raw)
    claimed, unresolved = set(), []
    for claim in raw:
        target = None
        for base in (spec_dir, Path.cwd()):
            candidate = base / claim["contract_file"]
            if candidate.is_file():
                target = candidate.resolve()
                break
        name = None
        if target is not None:
            for other_key, other_dir, path in index:
                if path.resolve() == target:
                    name = _qualified(other_key, other_dir, path)
                    break
        if name is None:
            unresolved.append(f"{claim['contract_file']}#{claim['clause_id']}")
            continue
        full = f"{name}#{claim['clause_id']}"
        if full in universe:
            claimed.add(full)
        else:
            unresolved.append(full)
    return claimed, unresolved


def _fr_universe(requirements_md: Path, extractor, validate_requirements):
    """FR ids declared by definition rows, read outside fences and inline code spans."""
    if not requirements_md.is_file():
        return None
    raw = requirements_md.read_text(encoding="utf-8", errors="replace").splitlines()
    blanked = extractor.strip_fences(raw)
    view = [extractor.strip_code_spans(line) for line in blanked]
    out = set()
    for prefix, _digits, number, suffix, _lineno in validate_requirements._definitions(view):
        if prefix == "FR":
            out.add("FR-%03d%s" % (number, suffix))
    return out


def _fr_claimed(spec_dir: Path, extractor):
    """FR ids cited from the citation groups of this spec's own contract clauses."""
    claimed = set()
    contracts = spec_dir / "contracts"
    if not contracts.is_dir():
        return claimed
    for path in sorted(p for p in contracts.rglob("*") if p.is_file()):
        try:
            for _cid, frs in extractor.clause_citations(path).items():
                claimed |= frs
        except (OSError, UnicodeDecodeError):
            continue
    return claimed


def _baseline_names(path: Path):
    if not path.is_file():
        return None
    return sorted(
        l.strip() for l in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if l.strip() and not l.startswith("#")
    )


def _head_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip()[:12] or "unknown"
    except OSError:
        return "unknown"


def account(spec_dir: Path, corpus_root: Path, baseline_path: Path,
            freeze: bool = False):
    """The whole accounting, as data. `freeze` narrows the corpus to everything BUT spec_dir."""
    extractor = _sibling("clause_extract.py")
    validate_tasks = _sibling("validate-tasks.py")
    validate_requirements = _sibling("validate-requirements.py")

    problems = []
    if not spec_dir.is_dir():
        return {"status": "input-error", "problems": [f"spec dir does not exist: {spec_dir}"]}
    if not corpus_root.is_dir():
        return {"status": "input-error", "problems": [f"corpus root does not exist: {corpus_root}"]}

    all_files = _corpus_files(corpus_root)
    if not all_files:
        return {"status": "input-error", "problems": [
            f"no contract files found under {corpus_root}/*/contracts/ — a zero denominator "
            "would make every set trivially empty, so this is an input error, not a green run"
        ]}

    spec_key = spec_dir.resolve().name
    if freeze:
        files = [row for row in all_files if row[0] != spec_key]
    else:
        files = all_files

    per_form, parsed, named, named_names, zero_positive, universe, id_total = _scan(
        files, extractor
    )
    collapsed = id_total - len(universe)

    claimed, unresolved = set(), []
    own_claimed = set()
    for key in sorted({row[0] for row in files}):
        names, bad = _claims_for(corpus_root / key, validate_tasks, universe, files)
        claimed |= names
        if key == spec_key:
            own_claimed, unresolved = names, bad

    uncovered = sorted(universe - claimed)

    baseline_names = _baseline_names(baseline_path)
    baseline_set = set(baseline_names or [])
    if freeze:
        delta = uncovered
        baseline_internal = 0
    else:
        delta = sorted(n for n in uncovered if n not in baseline_set)
        baseline_internal = len([n for n in uncovered if n in baseline_set])

    requirements_md = spec_dir / "requirements.md"
    fr_universe = _fr_universe(requirements_md, extractor, validate_requirements)
    if fr_universe is None:
        problems.append(f"requirements.md not found in the spec dir: {requirements_md}")
        fr_uncovered = []
        fr_claimed_count = 0
        fr_universe_count = 0
    else:
        fr_claimed = _fr_claimed(spec_dir, extractor)
        fr_uncovered = sorted(fr_universe - fr_claimed)
        fr_claimed_count = len(fr_universe & fr_claimed)
        fr_universe_count = len(fr_universe)

    yaml_total = sum(1 for row in files if row[2].suffix.lower() in YAML_SUFFIXES)
    yaml_named = sum(1 for n in named_names if n.lower().endswith(YAML_SUFFIXES))

    blocking = bool(delta) or bool(fr_uncovered)
    if problems and not blocking:
        status = "input-error"
    elif baseline_names is None and not freeze:
        status = "baseline-missing"
        problems.append(
            f"frozen baseline not found: {baseline_path} — an absent baseline is NOT an "
            "empty exemption list, so this run cannot judge the delta; freeze it with "
            f"`account-clause-coverage.py {spec_dir} --freeze > {baseline_path}`"
        )
    elif blocking:
        status = "uncovered"
    else:
        status = "ok"

    checks = [
        {"label": "clause-uncovered",
         "status": "fail" if delta else "pass",
         "count": len(uncovered),
         "detail": f"{len(uncovered)} uncovered, {len(delta)} beyond the frozen baseline"},
        {"label": "fr-uncovered",
         "status": "fail" if fr_uncovered else "pass",
         "count": len(fr_uncovered),
         "detail": f"{fr_claimed_count} of {fr_universe_count} FRs cited from citation groups"},
        {"label": "clause-unparsable",
         "status": "fail" if zero_positive else ("warn" if named else "pass"),
         "count": named,
         "detail": f"{named} files yield no clause id under the owner's forms; "
                   f"{zero_positive} of them declare a positive form, which is parse doubt "
                   f"and is never read as zero-and-covered"},
        {"label": "coverage-baseline-delta",
         "status": "fail" if (delta or (baseline_names is None and not freeze)) else "pass",
         "count": len(delta),
         "detail": f"baseline holds {len(baseline_set)} names; {baseline_internal} uncovered "
                   "items are baseline-internal and do not block"},
    ]

    errors = len(delta) + len(fr_uncovered) + (1 if baseline_names is None and not freeze else 0)
    warnings = zero_positive + len(unresolved)

    return {
        "status": status,
        "problems": problems,
        "file": str(spec_dir),
        "spec_dir": str(spec_dir),
        "spec_key": spec_key,
        "corpus_root": str(corpus_root),
        "baseline": str(baseline_path),
        "baseline_present": baseline_names is not None,
        "freeze": freeze,
        "owner_forms": list(OWNER_FORMS),
        "owner_doc": OWNER_DOC,
        "census_owner": CENSUS_OWNER,
        "scanned": {
            "total": len(files),
            "parsed": parsed,
            "named_unparseable": named,
            "named_files": named_names,
            "zero_clause_parseable": zero_positive,
            "sentinel_holds": parsed + named == len(files),
            "yaml_total": yaml_total,
            "yaml_parsed": yaml_total - yaml_named,
            "yaml_named": yaml_named,
            "per_form": per_form,
        },
        "clause": {
            "universe": len(universe),
            "universe_ids": id_total,
            "collapsed_duplicate_ids": collapsed,
            "claimed": len(own_claimed),
            "claimed_all_specs": len(claimed),
            "uncovered": uncovered,
            "uncovered_beyond_baseline": delta,
            "baseline_internal_count": baseline_internal,
            "baseline_name_count": len(baseline_set),
            "claims_outside_corpus": sorted(unresolved),
        },
        "fr": {
            "universe": fr_universe_count,
            "claimed": fr_claimed_count,
            "uncovered": fr_uncovered,
        },
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def _freeze_document(report, corpus_root: Path, spec_key: str) -> str:
    """The baseline document: a sorted name list with a header recording what makes it comparable.

    Two header lines only, and in ascending order, so the file stays directly consumable by
    `comm -13` (a header line that sorted after a name would make comm report the inputs as
    unsorted and could drop a real delta).
    """
    scanned = report["scanned"]
    forms = ",".join(OWNER_FORMS)
    names = report["clause"]["uncovered"]
    lines = [
        "# coverage-baseline: frozen UNCOVERED clause names, codepoint-sorted, one per line; "
        "compare with `LC_ALL=C comm -13 <this file> <live uncovered>` — the LC_ALL=C is "
        "load-bearing: glibc collation ignores # / and . at the first level, so under a "
        "UTF-8 locale these header lines sort AFTER the names, comm reports 'file 1 is not "
        "in sorted order' and then echoes all of file 2 as the delta",
        f"# frozen-from: {corpus_root.as_posix()}/*/contracts/* excluding {spec_key} | "
        f"owner-forms: {forms} ({NAMED_FORM} named, never silently covered) | "
        f"clause-rules: {OWNER_DOC} | per-form counts: {CENSUS_OWNER} | "
        f"base-sha: {_head_sha()} | files: {scanned['total']} "
        f"(parsed {scanned['parsed']} + named {scanned['named_unparseable']})",
    ]
    lines.extend(names)
    return "\n".join(lines) + "\n"


def _print_human(report, list_named: bool) -> None:
    scanned = report["scanned"]
    clause = report["clause"]
    fr = report["fr"]
    sentinel = "OK" if scanned["sentinel_holds"] else "BROKEN"
    forms = ", ".join(POSITIVE_FORMS)

    print(f"spec-dir: {report['spec_dir']}")
    print(f"corpus:   {report['corpus_root']}/*/contracts/*")
    print(f"owner forms ({OWNER_DOC}): {forms}; {NAMED_FORM} named")
    print(f"scanned {scanned['total']} files: parsed {scanned['parsed']} + "
          f"named-unparseable {scanned['named_unparseable']} == {scanned['total']}  "
          f"[relational sentinel {sentinel}]")
    per_form = "; ".join(
        f"{form} {data['files']} files/{data['clauses']} clauses"
        for form, data in scanned["per_form"].items() if data["files"]
    )
    print(f"  per form (counts owned by {CENSUS_OWNER}, re-derive, never restate): {per_form}")
    print(f"  zero-clause-but-parseable (parse doubt): {scanned['zero_clause_parseable']}")
    print(f"  .yaml: parsed {scanned['yaml_parsed']} / total {scanned['yaml_total']} / "
          f"named {scanned['yaml_named']}")
    if list_named:
        for name in scanned["named_files"]:
            print(f"  NAMED: {name}")
    print(f"named-unparseable: {scanned['named_unparseable']} "
          f"(use --list-named to expand)")
    print(f"clause universe: {clause['universe']} distinct names over {scanned['parsed']} "
          f"parsed files ({clause['universe_ids']} ids extracted)")
    if clause["collapsed_duplicate_ids"]:
        print(f"  collapsed: {clause['collapsed_duplicate_ids']} extracted ids share a name "
              f"with another in the same file, so the distinct-name denominator is smaller "
              f"than the id count — the owner's yaml-openapi form names a clause by its HTTP "
              f"method key, which one file may declare under several paths. Reported, never "
              f"absorbed; qualifying those ids is research.md A-8, not this run's call.")
    print()

    print("== clause coverage (universe: contract files per the owner's forms; "
          "claimed: tasks.md [green:] declarations) ==")
    print(f"claimed clauses (this feature): {clause['claimed']}")
    print(f"baseline: {report['baseline']} ({clause['baseline_name_count']} names"
          f"{'' if report['baseline_present'] else ', MISSING'})")
    print(f"baseline-internal existing uncovered: {clause['baseline_internal_count']}")
    for name in clause["uncovered"]:
        print(f"{STR009} {name}")
    print(f"uncovered beyond baseline: {len(clause['uncovered_beyond_baseline'])}")
    for name in clause["uncovered_beyond_baseline"]:
        # deliberately NOT the STR-009 prefix: the `UNCOVERED:` block above is the raw set
        # difference and is what `comm -13 <baseline> <live>` consumes, so a second block
        # wearing the same prefix would make that pipeline count each blocking item twice
        print(f"BEYOND-BASELINE: {name}")
    if clause["claims_outside_corpus"]:
        for name in clause["claims_outside_corpus"]:
            print(f"WARN claims not resolving into the scanned universe: {name}")
    print()

    print("== FR coverage (universe: requirements.md definition rows outside code spans; "
          "claimed: clause citation groups, never task rows) ==")
    print(f"FR universe: {fr['universe']}")
    print(f"FR claimed: {fr['claimed']}")
    for name in fr["uncovered"]:
        print(f"{UNCOVERED_FR} {name}")
    print(f"FR uncovered: {len(fr['uncovered'])}")
    print()

    for problem in report["problems"]:
        print(f"ERROR {problem}")
    print(f"companion (must be non-empty on a green run): claimed clauses "
          f"{clause['claimed']}, scanned files {scanned['total']}, clause universe "
          f"{clause['universe']}, FR universe {fr['universe']}")
    for check in report["checks"]:
        print(f"  [{check['label']}] {check['status']} ({check['count']}) — {check['detail']}")
    print(f"{report['errors']} error(s), {report['warnings']} warning(s)")
    print(f"status: {report['status']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="account-clause-coverage.py",
        description="Account clause and FR coverage for a feature spec as set differences "
                    "over sorted NAME lists — never as counts, so two runs are comparable "
                    "with `comm -13`.",
        epilog="Exit codes: 0 = covered beyond the frozen baseline, 1 = uncovered items or "
               "uncovered FRs, 2 = input error including a missing baseline file.",
    )
    parser.add_argument("target", nargs="?",
                        help="the spec directory, or any file inside it (its spec dir is "
                             "derived by walking up to the nearest requirements.md/contracts)")
    parser.add_argument("--spec-dir", default=None,
                        help="the spec directory to account (overrides the positional target)")
    parser.add_argument("--corpus-root", default=".specify/specs",
                        help="directory holding the spec dirs (default: .specify/specs)")
    parser.add_argument("--baseline", default=None,
                        help="frozen name list (default: <spec-dir>/coverage-baseline.txt)")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable report instead of text")
    parser.add_argument("--list-named", action="store_true",
                        help="expand the named-unparseable list instead of printing only its count")
    parser.add_argument("--freeze", action="store_true",
                        help="PRINT the baseline document (header + sorted names) over the "
                             "corpus excluding --spec-dir; redirect it into the baseline file. "
                             "This script never writes.")
    args = parser.parse_args(argv)

    if args.spec_dir:
        spec_dir = Path(args.spec_dir)
    elif args.target:
        spec_dir = _spec_dir_from(Path(args.target))
    else:
        print("input-error: give a spec dir positionally or via --spec-dir", file=sys.stderr)
        return EXIT_INPUT
    if not spec_dir.is_dir():
        print(f"input-error: spec dir does not exist: {spec_dir}", file=sys.stderr)
        return EXIT_INPUT

    corpus_root = Path(args.corpus_root)
    baseline_path = Path(args.baseline) if args.baseline else spec_dir / BASELINE_NAME

    report = account(spec_dir, corpus_root, baseline_path, freeze=args.freeze)
    if report["status"] == "input-error" and "scanned" not in report:
        for problem in report["problems"]:
            print(f"input-error: {problem}", file=sys.stderr)
        if args.json:
            print(json.dumps({"file": str(spec_dir), "status": report["status"],
                              "problems": report["problems"], "checks": [],
                              "errors": len(report["problems"]), "warnings": 0},
                             ensure_ascii=False, indent=2))
        return EXIT_INPUT

    if args.freeze:
        sys.stdout.write(_freeze_document(report, corpus_root, report["spec_key"]))
        return EXIT_OK

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report, args.list_named)

    if report["status"] == "baseline-missing":
        return EXIT_INPUT
    return EXIT_UNCOVERED if report["status"] == "uncovered" else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
