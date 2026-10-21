#!/usr/bin/env python3
"""Deterministic structural validator for a feature's tasks.md.

Program-First discipline (.specify/shared/guidelines/token-efficiency.md): the fixed
mechanical rules that /speckit.tasks must enforce are checked here, once,
instead of being re-improvised as ad-hoc greps on every run.

Checks performed:
  row-format      every task row matches `- [state] T<NNN>[letter] ...` on ONE
                  line; checkbox lines with a missing/placeholder/malformed ID
                  are errors; indented continuation lines directly after a task
                  row (a wrapped row) are errors
  id-unique       task IDs are unique across the file
  blockedBy       every [blockedBy: Txxx,Tyyy] reference resolves to an
                  existing task ID (dangling/self references are errors;
                  references to LATER tasks are warnings)
  parallel-safe   two [P] tasks in the same phase must not WRITE the same file
                  path (warning: path extraction from prose is heuristic, and a
                  row's paths are split into write targets and pointer targets —
                  a path governed by an explicit read-only marker (a cite
                  governor such as `per` / `see` / `against` / `owner` / `指向`,
                  `read-only`, or a `grep` / `diff -` probe in the preceding
                  window) is a pointer target, so two rows that merely cite the
                  same owner do not conflict. Confirm each reported overlap
                  against the rows' actual write targets, then drop [P] from one
                  row or re-target it — never silence a warning by deleting the
                  cited path from the row text)
  story-labels    inside a `## Phase ... User Story ...` phase every row
                  carries exactly one [US<n>] label; NON-story phases
                  (Setup / Foundational / Polish / anything else) carry zero
                  `[US` markers (placeholders like [US-none] are violations)
  dod-format      no checkbox-syntax line (`- [ ]` / `- [x]` ...) inside the
                  `## Definition of Done` section (reserved for task rows)
  green-dangling  a `[green: <contract>#<clause>]` attribution whose contract
                  file does not exist, whose file declares no machine-decidable
                  clause form, or whose clause id that file does not contain
                  (error: a claim nobody can resolve is a claim nobody can
                  honour, which is worse than one that lands a phase late)
  green-cross-phase  on one contract, the clause ordinals of the claims run
                  backwards against the rows' monotonic order, so the earlier row
                  cannot leave that contract green at its own phase (warning;
                  compares the same `order` counter blockedBy uses — this script
                  has no numeric phase index and MUST NOT grow one)
  green-clause-collision  two rows claim the same contract clause, i.e. the
                  clause partition (条款分区 (Clause Partition),
                  `.specify/memory/glossary.md`) was cut over the same clause
                  twice (warning)
  green-path-divergence  one TEST path is claimed green by two rows at two
                  different green points, so the pair cannot each be the row that
                  turns that file green (warning; scoped to test paths because an
                  append-only sink such as an evidence log is written by every row
                  that pastes into it and is nobody's green point)

Usage:
  python3 .specify/scripts/python/validate-tasks.py <path/to/tasks.md> [--json]

Exit codes:
  0  no errors (warnings may still be reported)
  1  at least one error
  2  file missing / unreadable / no task rows found
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

TASK_ROW = re.compile(r"^- \[([ xX>~])\]\s+(\S+)(.*)$")
VALID_ID = re.compile(r"^T\d{3}[A-Za-z]?$")
BLOCKED_BY = re.compile(r"\[blockedBy:\s*([^\]]+)\]")
STORY_LABEL = re.compile(r"\[US(\d+)\]")
ANY_US_MARKER = re.compile(r"\[US[^\]]*\]")
PHASE_HEADING = re.compile(r"^##\s+Phase\b(.*)$", re.IGNORECASE)
USER_STORY_PHASE = re.compile(r"User Story", re.IGNORECASE)
DOD_HEADING = re.compile(r"^##\s+Definition of Done\b", re.IGNORECASE)
NEXT_H2 = re.compile(r"^##\s")
PARALLEL_MARKER = re.compile(r"(?<!\S)\[P\](?!\S)")
# path-like tokens: contains a slash, or a filename with a common extension
PATH_TOKEN = re.compile(
    r"(?:[\w.@+~-]+/)+[\w.@+~/-]+|[\w@+~-]+\.(?:py|sh|bash|md|ya?ml|json|toml|txt|js|mjs|ts|tsx|ini|cfg|tpl|sql|go|rs|java|c|h|cpp)\b"
)
# A path token governed by one of these is a POINTER target (read/cited), not a
# WRITE target. Deliberately a closed list of unambiguous read-only governors:
# ambiguous ones (`from`, `via`, `in`) also head write phrases, so a token they
# govern keeps the default classification and the overlap is still reported.
POINTER_GOVERNOR = re.compile(
    r"(?:\b(?:per|see|against|cite|cited|cites|owner|owned)\b|"
    r"read-only|readonly|只读|指向|参见|详见|MUST NOT edit|(?:do not|never) edit)"
    r"[\s`'\"(:,、。]*$",
    re.IGNORECASE,
)
# A read-only probe named in the window preceding the token also demotes it --
# covers `grep <pat> in <path>`, where the governor word (`in`) is ambiguous and
# so cannot be used on its own.
POINTER_CONTEXT = re.compile(
    r"\bgrep\b|\brg\b|\bdiff\s+-|\bgit diff\b|no matches",
    re.IGNORECASE,
)
# A write verb inside that same window cancels the demotion: `grep X in a.md then
# rewrite b.py` must keep b.py a write target, or the guard loses real conflicts.
WRITE_VERB = re.compile(
    r"\b(?:create|write|add|update|edit|rewrite|extend|insert|rename|remove|"
    r"delete|author|fill|implement|modify|append|replace|patch|port|copy|sync)\b|"
    r"新建|写入|新增|插入|扩写|改写|修改|重写|追加|替换|同步",
    re.IGNORECASE,
)
POINTER_WINDOW = 40

# An inline green-point attribution: `[green: <contract>#<clause>]` (STR-001; the surface
# is declared in .specify/templates/tasks-template.md § Format). The separator is the FIRST `#` and
# everything up to the closing bracket is the clause id, so the id forms the corpus
# actually uses (`C-1`, `C-01`, `C-001`, `C-3.4`) all survive intact.
GREEN_CLAIM = re.compile(r"\[green:\s*([^\]#]+)#([^\]]+)\]")
# Clause ids are not uniform in width and may carry a dotted sub-number, so the ordering
# key is the tuple of their number groups. An id with no digits at all (a
# `yaml-assertions` name) has no order and is skipped rather than guessed at.
CLAUSE_ORDINAL = re.compile(r"\d+")

# WHY green claims are extracted before classification, and NOT taught to POINTER_GOVERNOR:
# PATH_TOKEN's trailing character class has no `#`, so inside
# `[green: contracts/x.md#C-1]` it matches `contracts/x.md` — and the bracket skip in
# _classify_paths (`if "[" in tok or "]" in tok: continue`) cannot protect it, because
# the brackets are outside the match. Adding `[green:` to POINTER_GOVERNOR would silence
# the symptom and break that table's contract, which is a closed list of read-only
# governor WORDS (`per`, `see`, `owner`, …); `[green:` is a label prefix, not a word.
# Extracting first makes the orthogonality a construction property instead of a regex
# special case, and yields the parsed claim tuples as a by-product.
_CLAUSE_EXTRACT = None


def _clause_extract():
    """The sibling clause extractor, loaded by path rather than by `import`.

    This script runs both as `python3 .specify/scripts/python/validate-tasks.py` (where its own
    directory is `sys.path[0]`) and under `importlib` from a contract test (where it is
    not). Resolving the sibling next to `__file__` also keeps a `.specify/` mirror copy
    on the mirror's own extractor instead of reaching back into the source tree.
    """
    global _CLAUSE_EXTRACT
    if _CLAUSE_EXTRACT is None:
        sibling = Path(__file__).resolve().with_name("clause_extract.py")
        spec = importlib.util.spec_from_file_location("_clause_extract_sibling", sibling)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _CLAUSE_EXTRACT = module
    return _CLAUSE_EXTRACT


def _strip_claims(source: str, rest: str):
    """((contract, clause) pairs, residual row text) for one task row.

    `source` is the row as seen through the DECLARATION view: fenced lines blanked, and
    the content of each inline code span dropped. A form inside a ``` block is an example
    and a form inside backticks is a mention of the tag, so neither is a declaration.
    `rest` is the raw row text, and is what the path classifier sees next. When the row
    declares nothing, `rest` is returned byte-identical — a claim-free file is classified
    exactly as it was before this surface existed.
    """
    found = [(m.group(1).strip(), m.group(2).strip()) for m in GREEN_CLAIM.finditer(source)]
    if not found:
        return [], rest
    return found, GREEN_CLAIM.sub(" ", rest)


def _repo_root_of(tasks_path: Path):
    for base in tasks_path.resolve().parents:
        if (base / ".git").exists():
            return base
    return None


def _resolve_contract(claim_path: str, tasks_path: Path):
    """Locate a claimed contract file, or None.

    Two spellings are both legitimate, so both are tried: a spec's own tasks.md reaches
    its contracts as `contracts/<name>.md` beside itself, and a claim about another
    feature's contract is written from the repository root. The working directory is the
    last base so a scratch file outside any repository still resolves.
    """
    resolved = tasks_path.resolve().parent
    bases = [resolved]
    root = _repo_root_of(tasks_path)
    if root is not None and root not in bases:
        bases.append(root)
    cwd = Path.cwd()
    if cwd not in bases:
        bases.append(cwd)
    for base in bases:
        candidate = base / claim_path
        if candidate.is_file():
            return candidate
    return None


def _clause_ordinal(clause_id: str):
    numbers = tuple(int(n) for n in CLAUSE_ORDINAL.findall(clause_id))
    return numbers or None


def _is_test_path(token: str) -> bool:
    """Whether a write target is a TEST path, for green-path-divergence only.

    FR-018(b) and green-point-claim.md C-16 both scope that check to a test path appearing
    in two verification rows, and the prose obligation it mechanizes says "any test path"
    too. Recognizing one is a structural fact rather than a guess: `tests/` is the location
    the house's own template declares (.specify/templates/tasks-template.md § Path Conventions), and
    `test_*` is the collection prefix pytest uses.

    The distinction is load-bearing, and dogfooding is what proved it: an append-only
    evidence log such as `notes/red-first-evidence.md` is a write target of every row that
    pastes into it, so scoping the check to all write targets reported a divergence between
    rows that merely share a sink — three false findings on this feature's own tasks.md.
    A sink is not a green point, so no row is claiming to be the one that turns it green.
    `parallel-safe` is deliberately unaffected: two [P] rows writing one file really do
    conflict whatever the file is for.
    """
    parts = token.replace("\\", "/").split("/")
    return "tests" in parts or parts[-1].startswith("test_")


def _classify_paths(text: str):
    """Split a row's path tokens into (write targets, pointer targets).

    The default is WRITE: only an unambiguous read-only governor immediately
    before the token, or a read-only probe in the preceding window with no write
    verb in it, demotes a token. Two [P] rows that merely cite the same owner
    therefore stop being reported as a write conflict, while every overlap the
    guard reported before is still reported.
    """
    write, pointer = set(), set()
    for m in PATH_TOKEN.finditer(text):
        tok = m.group(0).strip(".,;:()")
        if "[" in tok or "]" in tok:  # template placeholder, not a real path
            continue
        before = text[max(0, m.start() - POINTER_WINDOW):m.start()]
        governed = bool(POINTER_GOVERNOR.search(before))
        probed = bool(POINTER_CONTEXT.search(before)) and not WRITE_VERB.search(before)
        (pointer if (governed or probed) else write).add(tok)
    return write, pointer


def validate(path: Path, claims_out: list | None = None):
    """(errors, warnings) for one tasks.md.

    `claims_out` is an optional list the caller passes to receive the parsed
    `[green:]` declarations (four E-4 fields each); `validate()` keeps returning a
    2-tuple so every existing caller and contract pin is unaffected.
    """
    errors, warnings = [], []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [f"0: cannot read {path}: {exc}"], []

    tasks = {}          # id -> {line, phase, parallel, write_paths, pointer_paths, order}
    claims = []         # parsed [green:] attributions, in row order
    claim_view = None   # fence-blanked + code-span-stripped lines, built on first need
    order = 0
    phase_name = None
    phase_is_story = False
    in_dod = False
    prev_was_task = False

    for lineno, line in enumerate(lines, start=1):
        # --- section tracking -------------------------------------------
        if DOD_HEADING.match(line):
            in_dod, phase_name = True, None
            prev_was_task = False
            continue
        if in_dod:
            if NEXT_H2.match(line):
                in_dod = False
            elif re.match(r"^\s*- \[[ xX~]\]", line):
                errors.append(
                    f"{lineno}: dod-format: checkbox syntax inside Definition of Done "
                    f"(use `- DoD-N:` prefix): {line.strip()[:80]}"
                )
        m_phase = PHASE_HEADING.match(line)
        if m_phase:
            phase_name = m_phase.group(0).strip()
            phase_is_story = bool(USER_STORY_PHASE.search(phase_name))
            prev_was_task = False
            continue
        if re.match(r"^##\s", line):  # any other H2 ends the current phase
            phase_name, phase_is_story = None, False

        # --- task rows ----------------------------------------------------
        m = TASK_ROW.match(line)
        if m:
            prev_was_task = True
            if in_dod:
                continue  # already reported by the dod-format check above
            state, tid, rest = m.group(1), m.group(2), m.group(3)
            if not VALID_ID.match(tid):
                errors.append(
                    f"{lineno}: row-format: checkbox row with missing/placeholder/malformed "
                    f"Task ID `{tid}` (expected T<NNN>): {line.strip()[:80]}"
                )
                continue
            if tid in tasks:
                errors.append(
                    f"{lineno}: id-unique: duplicate Task ID {tid} "
                    f"(first defined at line {tasks[tid]['line']})"
                )
                continue
            order += 1
            # extract the green-point claims BEFORE the residual text is classified
            # (see the note by POINTER_WINDOW); a form inside a ``` fence is an example
            # and a form inside an inline code span is a MENTION of the tag, not a
            # declaration of it — the same distinction FR-009 draws for references, and
            # without it a row that merely names the tag (or the template that defines
            # it) reports a dangling claim for a clause nobody ever asserted
            if "[green:" in line and claim_view is None:
                extractor = _clause_extract()
                claim_view = [
                    extractor.strip_code_spans(text)
                    for text in extractor.strip_fences(lines)
                ]
            source = line if claim_view is None else claim_view[lineno - 1]
            row_claims, rest = _strip_claims(source, rest)
            write_paths, pointer_paths = _classify_paths(rest)
            tasks[tid] = {
                "line": lineno,
                "state": state,
                "phase": phase_name,
                "phase_is_story": phase_is_story,
                "parallel": bool(PARALLEL_MARKER.search(rest)),
                "write_paths": write_paths,
                "pointer_paths": pointer_paths,
                "order": order,
                "blocked_by": [
                    t.strip() for t in re.split(r"[,\s]+", (BLOCKED_BY.search(rest).group(1) if BLOCKED_BY.search(rest) else "")) if t.strip()
                ],
            }
            for contract_file, clause_id in row_claims:
                claims.append({
                    "contract_file": contract_file,
                    "clause_id": clause_id,
                    "task_id": tid,
                    "phase": phase_name,
                    "line": lineno,
                    "order": order,
                })
            # story-label placement
            labels = STORY_LABEL.findall(rest)
            any_us = ANY_US_MARKER.search(rest)
            if phase_is_story and len(labels) != 1:
                errors.append(
                    f"{lineno}: story-labels: {tid} in User Story phase "
                    f"`{phase_name[:60]}` must carry exactly one [US<n>] label "
                    f"(found {len(labels)})"
                )
            elif not phase_is_story and any_us:
                errors.append(
                    f"{lineno}: story-labels: {tid} in NON-story phase "
                    f"`{(phase_name or '<no phase>')[:60]}` must not carry any "
                    f"[US...] marker: {any_us.group(0)}"
                )
            continue

        # --- wrapped continuation line -------------------------------------
        if prev_was_task and line.strip() and re.match(r"^\s+\S", line) \
                and not re.match(r"^\s*(?:[-*#>|`]|\d+\.)", line):
            errors.append(
                f"{lineno}: row-format: wrapped task row — continuation text must be "
                f"folded into the single-line task row above: {line.strip()[:80]}"
            )
        if not line.strip():
            prev_was_task = False
        elif not line.startswith((" ", "\t")):
            prev_was_task = False

    if not tasks:
        errors.append(f"0: no task rows found in {path} (expected `- [ ] T<NNN> ...` lines)")
        return errors, warnings

    # --- blockedBy resolvability -----------------------------------------
    for tid, t in tasks.items():
        for ref in t["blocked_by"]:
            if ref == tid:
                errors.append(f"{t['line']}: blockedBy: {tid} references itself")
            elif ref not in tasks:
                errors.append(
                    f"{t['line']}: blockedBy: {tid} references {ref}, which does not exist "
                    f"(dangling reference)"
                )
            elif tasks[ref]["order"] > t["order"]:
                warnings.append(
                    f"{t['line']}: blockedBy: {tid} references later task {ref} "
                    f"(forward dependency — verify this is intentional)"
                )

    # --- [P] parallel safety (same phase, same file) -----------------------
    by_phase = {}
    for tid, t in tasks.items():
        if t["parallel"]:
            by_phase.setdefault(t["phase"], []).append((tid, t))
    for phase, rows in by_phase.items():
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                tid_a, a = rows[i]
                tid_b, b = rows[j]
                phase_label = (phase or "<no phase>")[:60]
                both_write = a["write_paths"] & b["write_paths"]
                if both_write:
                    warnings.append(
                        f"{a['line']}: parallel-safe: [P] tasks {tid_a} (line {a['line']}) and "
                        f"{tid_b} (line {b['line']}) both WRITE {sorted(both_write)} in phase "
                        f"`{phase_label}` — [P] requires different write targets; drop [P] from "
                        f"one row or re-target it, never by deleting the cited path"
                    )
                    continue
                # One row writes what the other only cites: a real ordering
                # hazard, but weaker than two writers, so it is labelled
                # distinctly and the two-writer remedy is not offered for it.
                # Reported per direction — both directions can hold at once.
                a_writes = a["write_paths"] & b["pointer_paths"]
                b_writes = b["write_paths"] & a["pointer_paths"]
                for writer, wline, reader, rline, paths in (
                    (tid_a, a["line"], tid_b, b["line"], a_writes),
                    (tid_b, b["line"], tid_a, a["line"], b_writes),
                ):
                    if not paths:
                        continue
                    warnings.append(
                        f"{wline}: parallel-safe: [P] task {writer} (line {wline}) WRITES "
                        f"{sorted(paths)} while {reader} (line {rline}) only references it as a "
                        f"read-only target in phase `{phase_label}` — the reader may observe a "
                        f"half-written file; sequence the pair with [blockedBy:] or drop [P]"
                    )

    # --- green-point attribution claims ------------------------------------
    # Resolvability is judged by the clause-syntax owner's forms via the sibling
    # extractor, never by a private regex here: a second definition of "what counts
    # as a clause" is exactly the drift the owner document exists to prevent.
    resolved = []
    if claims:
        extractor = _clause_extract()
        for claim in claims:
            target = _resolve_contract(claim["contract_file"], path)
            if target is None:
                errors.append(
                    f"{claim['line']}: green-dangling: {claim['task_id']} declares "
                    f"[green: {claim['contract_file']}#{claim['clause_id']}] but no such "
                    f"contract file exists (looked beside {path.name}, then the repository "
                    f"root, then the working directory) — correct the path or drop the claim"
                )
                continue
            if extractor.form_of(target) == "md-none":
                errors.append(
                    f"{claim['line']}: green-dangling: {claim['task_id']} declares "
                    f"{claim['contract_file']}#{claim['clause_id']} but that file declares "
                    f"no machine-decidable clause form, so nothing can check the claim "
                    f"(forms: .specify/shared/definitions/contract-clause-definitions.md) — give the "
                    f"contract a machine-decidable clause form or drop the claim"
                )
                continue
            if not extractor.resolvable(target, claim["clause_id"]):
                errors.append(
                    f"{claim['line']}: green-dangling: {claim['task_id']} declares "
                    f"{claim['contract_file']}#{claim['clause_id']} but that file contains "
                    f"no clause {claim['clause_id']} — name a clause id the file declares"
                )
                continue
            resolved.append(dict(claim, resolved=str(target)))

    if resolved:
        # cross-phase: within one contract the clause ordinals must not run backwards
        # against the rows' monotonic order. `order` is the comparison quantity, the same
        # one the blockedBy forward-dependency warning above uses; this script has no
        # numeric phase index and MUST NOT grow one (the heading numbers are prose).
        per_contract = {}
        for claim in resolved:
            per_contract.setdefault(claim["resolved"], []).append(claim)
        for group in per_contract.values():
            group.sort(key=lambda c: c["order"])
            for earlier, later in zip(group, group[1:]):
                ord_a = _clause_ordinal(earlier["clause_id"])
                ord_b = _clause_ordinal(later["clause_id"])
                if ord_a is None or ord_b is None or ord_b >= ord_a:
                    continue
                warnings.append(
                    f"{earlier['line']}: green-cross-phase: {earlier['task_id']} "
                    f"(line {earlier['line']}, `{(earlier['phase'] or '<no phase>')[:60]}`, "
                    f"order {earlier['order']}) claims "
                    f"{earlier['contract_file']}#{earlier['clause_id']} while the later "
                    f"{later['task_id']} (line {later['line']}, "
                    f"`{(later['phase'] or '<no phase>')[:60]}`, order {later['order']}) "
                    f"claims #{later['clause_id']} — the clause order runs backwards against "
                    f"the row order, so {earlier['task_id']} cannot leave that contract green "
                    f"at its own phase; move the earlier clause's row up or re-cut the partition"
                )

        # one clause claimed by two rows: the clause partition was cut over it twice
        # (条款分区 (Clause Partition), `.specify/memory/glossary.md`)
        first_claim = {}
        for claim in sorted(resolved, key=lambda c: c["order"]):
            key = (claim["resolved"], claim["clause_id"])
            previous = first_claim.get(key)
            if previous is None:
                first_claim[key] = claim
                continue
            warnings.append(
                f"{previous['line']}: green-clause-collision: {previous['task_id']} "
                f"(line {previous['line']}) and {claim['task_id']} (line {claim['line']}) both "
                f"claim {claim['contract_file']}#{claim['clause_id']} — one clause belongs to "
                f"one row, so re-cut the partition (条款分区 (Clause Partition), "
                f".specify/memory/glossary.md) rather than dropping one of the two claims"
            )

        # one write target claimed green at two different points by two rows: the pair
        # cannot each be the row that turns that file green
        row_points = {}
        for claim in resolved:
            row_points.setdefault(claim["task_id"], set()).add(
                f"{claim['contract_file']}#{claim['clause_id']}"
            )
        writers = {}
        for tid, t in tasks.items():
            for write_target in t["write_paths"]:
                if not _is_test_path(write_target):
                    continue    # a shared sink is not a shared green point (see _is_test_path)
                writers.setdefault(write_target, []).append(tid)
        for write_target, tids in sorted(writers.items()):
            claiming = [tid for tid in tids if row_points.get(tid)]
            for i in range(len(claiming)):
                for j in range(i + 1, len(claiming)):
                    tid_a, tid_b = claiming[i], claiming[j]
                    if row_points[tid_a] == row_points[tid_b]:
                        continue  # a shared path with the SAME green point is not divergence
                    warnings.append(
                        f"{tasks[tid_a]['line']}: green-path-divergence: {tid_a} "
                        f"(line {tasks[tid_a]['line']}) and {tid_b} "
                        f"(line {tasks[tid_b]['line']}) both write {write_target} but claim "
                        f"different green points ({sorted(row_points[tid_a])} vs "
                        f"{sorted(row_points[tid_b])}) — two rows cannot each be the one that "
                        f"turns this file green; partition the clauses between them or "
                        f"sequence the pair with [blockedBy:]"
                    )

    if claims_out is not None:
        claims_out.extend({
            k: claim[k] for k in ("contract_file", "clause_id", "task_id", "phase")
        } for claim in claims)

    # stable file order: each entry starts with "<lineno>: "
    errors.sort(key=lambda e: int(e.split(":", 1)[0]))
    warnings.sort(key=lambda w: int(w.split(":", 1)[0]))
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate-tasks.py",
        description="Deterministic structural validator for a feature's tasks.md "
                    "(row format, ID uniqueness, blockedBy resolvability, [P] "
                    "parallel safety, story-label placement, DoD format, and the "
                    "four green-point attribution checks).",
        epilog="Exit codes: 0 = no errors (warnings possible), 1 = errors found, "
               "2 = file missing / no task rows.",
    )
    parser.add_argument("tasks_md", help="path to the tasks.md file to validate")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable JSON report instead of text")
    args = parser.parse_args(argv)

    path = Path(args.tasks_md)
    if not path.is_file():
        print(f"FAIL: {path} does not exist", file=sys.stderr)
        return 2

    claims: list = []
    errors, warnings = validate(path, claims_out=claims)
    unparseable = any(e.startswith("0:") for e in errors)

    if args.json:
        print(json.dumps({
            "file": str(path),
            "errors": errors,
            "warnings": warnings,
            "status": "FAIL" if (errors or unparseable) else "PASS",
            # the parsed `[green:]` declarations, four fields each; the verdicts on
            # them travel in errors/warnings under the four green-* labels
            "green_claims": claims,
        }, ensure_ascii=False, indent=2))
    else:
        for w in warnings:
            print(f"WARN  {w}")
        for e in errors:
            print(f"ERROR {e}")
        status = "FAIL" if errors else ("PASS (with warnings)" if warnings else "PASS")
        print(f"{status}: {path} — {len(errors)} error(s), {len(warnings)} warning(s)")

    return 2 if unparseable else (1 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())
