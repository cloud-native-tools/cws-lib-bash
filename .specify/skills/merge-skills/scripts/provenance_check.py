#!/usr/bin/env python3
"""Provenance re-verification gate for a merged skill (merge-skills Phase 8, and any
later session that needs to know whether the merge still holds).

A merge proves no-loss once, at merge time. The target then keeps evolving — an
improve-skills loop, a doc restructure, a reference rename — and nothing notices when a
later edit drops a capability the merge absorbed. This script is the durable half of the
proof: it reads the committed capability-inheritance record the merge left behind and
re-checks it against the target as it exists NOW.

It answers one question mechanically: does this skill still cover what its sources
carried? Two independent checks, because a capability can be lost either way:

  1. facts   — every frozen coverage baseline under references/merge-provenance/ is
               re-run against the target's current corpus (delegates to
               coverage_probe.py; tokens loaded verbatim, never re-extracted). When the
               record declares a per-source `**Corpus**:` the check is scoped to it, so a
               fact lost from one absorbed source cannot be masked by a sibling's docs
               carrying the same token.
  2. routing — every capability row in the record names a destination path that still
               resolves, carries a verification method, and is marked verified or
               dropped(<reason>). A row whose destination was renamed or deleted is
               behavior-lost even when its nouns survive elsewhere.

Usage:
    provenance_check.py <target-skill-dir>

    <target-skill-dir>  the merged skill's own directory (the one holding SKILL.md and
                        references/merge-provenance.md), e.g. .specify/skills/git-utils

Exit code:
    0  record complete: every baseline clean, every destination resolves, every row
       verified or dropped-with-reason
    2  usage error (target dir missing / not a skill dir)
    3  drift or an open gap — the record names something the target no longer has, or a
       row is still `pending`. Read the findings; each names its own repair.
    4  the gate could not run: no provenance record, or the record parsed to zero
       sources. Never a pass — an unparsable record proves nothing, exactly as an
       empty coverage probe does.

What is NOT checked — honest limitation, do not read a green verdict as full coverage:
    - whether a capability is still *behaviorally* served end-to-end. The record's
      Verification column names how a human or agent checks that; running those is a
      walk-through, not this script's job.
    - `§ section` / `#anchor` parts of a destination. Only the file path is resolved, so
      a fact that slid to the wrong section of a still-existing doc passes.
    - prose-level facts, lowercase enum words, and anything the coverage probe does not
      tokenize (see coverage_probe.py's own limitation list).
    - cross-source masking, WHEN no `**Corpus**:` is declared. The default corpus is the
      whole target skill, so with several sources absorbed into one target a token that
      survives only in a sibling's docs reads as covered. Declare a scope per source in
      that case; see references/provenance-record.md.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_probe as cp  # noqa: E402

RECORD_RELPATH = os.path.join("references", "merge-provenance.md")
BASELINE_DIR = os.path.join("references", "merge-provenance")

# Corpus is everything the skill ships, not just its docs: a fact whose destination is a
# script (a CLI flag, an action key) is genuinely covered there, and a docs-only corpus
# would report it missing — a false red teaches the reader to ignore the gate.
CORPUS_EXTS = (".md", ".txt", ".py", ".sh", ".bash", ".js", ".json", ".yaml", ".yml")

SOURCE_HEADING = re.compile(r"^##\s+Source:\s*(?P<name>\S.*?)\s*$")
BASELINE_FIELD = re.compile(r"^\s*[-*]\s+\*\*Baseline\*\*:\s*`(?P<path>[^`]+)`")
CORPUS_FIELD = re.compile(r"^\s*[-*]\s+\*\*Corpus\*\*:\s*(?P<value>.+?)\s*$")
PATH_IN_CELL = re.compile(r"`([^`]+)`")
DROPPED = re.compile(r"^dropped\((?P<reason>.+)\)$")
TABLE_COLUMNS = ("capability", "target destination", "verification", "status")


def die(msg, code):
    print(msg, file=sys.stderr)
    sys.exit(code)


def _is_provenance_artifact(abs_path, skip_abs):
    return any(abs_path == s or abs_path.startswith(s + os.sep) for s in skip_abs)


def corpus_files(skill_dir, scope=None):
    """Everything the skill ships, MINUS the provenance record and its baselines.

    Excluding them is load-bearing, not cosmetic: a baseline lists every frozen token by
    construction, so a corpus that includes the baseline dir matches every token always
    and the gate can never go red. The record is excluded for the same reason — its
    Verification cells quote the very tokens being checked. What remains is the skill's
    functional content: SKILL.md, its other references, scripts, and assets.

    `scope` optionally narrows the walk to declared paths/globs relative to skill_dir —
    see `parse_corpus_scope`. Returns (files, unresolved_scope_entries).
    """
    skip_abs = {os.path.abspath(os.path.join(skill_dir, RECORD_RELPATH)),
                os.path.abspath(os.path.join(skill_dir, BASELINE_DIR))}
    if scope is None:
        roots, unresolved = [skill_dir], []
    else:
        entries, unresolved = scope
        roots = []
        for e in entries:
            matches = sorted(glob.glob(os.path.join(skill_dir, e), recursive=True))
            if matches:
                roots.extend(matches)
            else:
                unresolved.append(e)
    out = []
    for root in roots:
        if os.path.isfile(root):
            candidates = [(os.path.dirname(root), [os.path.basename(root)])]
        else:
            candidates = []
            for dirpath, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}]
                candidates.append((dirpath, sorted(files)))
        for dirpath, files in candidates:
            if _is_provenance_artifact(os.path.abspath(dirpath), skip_abs):
                continue
            for f in files:
                path = os.path.join(dirpath, f)
                if _is_provenance_artifact(os.path.abspath(path), skip_abs):
                    continue
                if f.endswith(CORPUS_EXTS):
                    out.append(path)
    return sorted(set(out)), unresolved


def parse_corpus_scope(value):
    """Parse a `**Corpus**:` value into (entries, ...): backticked spans, else commas.

    Entries may be paths or globs relative to the skill dir. Globs matter here: a
    multi-source merge needs "this engine's subtree plus the target's own top-level docs",
    which is `references/types/<engine>` + `references/*.md` + `SKILL.md` — the second
    pattern deliberately does not match `references/types/**`.
    """
    spans = [s.strip() for s in PATH_IN_CELL.findall(value) if s.strip()]
    if spans:
        return spans, []
    return [p.strip().strip("`") for p in value.split(",") if p.strip()], []


def split_cells(row):
    """Split a markdown table row on UNESCAPED pipes; a cell may contain `\\|`."""
    body = row.strip()
    body = re.sub(r"^\|", "", body)
    body = re.sub(r"\|$", "", body)
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


def parse_record(text):
    """Split the record into per-source sections: {name: {lines, baseline, rows}}."""
    sources, current = [], None
    for line in text.splitlines():
        m = SOURCE_HEADING.match(line)
        if m:
            current = {"name": m.group("name"), "lines": [], "baseline": None,
                       "corpus": None, "rows": []}
            sources.append(current)
            continue
        if current is None:
            continue
        current["lines"].append(line)
        b = BASELINE_FIELD.match(line)
        if b:
            current["baseline"] = b.group("path")
        c = CORPUS_FIELD.match(line)
        if c:
            current["corpus"] = parse_corpus_scope(c.group("value"))
    for src in sources:
        src["rows"] = parse_capability_table(src["lines"])
    return sources


def match_columns(cells):
    """Map each required column name to its cell index; header cells may be qualified
    (`Capability (what the source could do)`), so match on prefix, not equality."""
    idx = {}
    for col in TABLE_COLUMNS:
        for i, cell in enumerate(cells):
            if cell.startswith(col):
                idx[col] = i
                break
    return idx if len(idx) == len(TABLE_COLUMNS) else None


def parse_capability_table(lines):
    """Read the capability-inheritance table by header name, not column position."""
    header_idx, colmap, width = None, None, 0
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip().lower() for c in split_cells(line)]
        colmap = match_columns(cells)
        if colmap:
            header_idx, width = i, len(cells)
            break
    if header_idx is None:
        return None
    rows = []
    for line in lines[header_idx + 1:]:
        if not line.lstrip().startswith("|"):
            break
        cells = split_cells(line)
        if all(set(c) <= set("-: ") for c in cells if c):
            continue  # separator row
        if len(cells) != width:
            rows.append({"malformed": line})
            continue
        rows.append({col: cells[i] for col, i in colmap.items()})
    return rows


def resolve_destination(cell, skill_dir):
    """Return (paths_found, unresolved). Only backticked file paths are resolvable."""
    problems = []
    found = []
    for raw in PATH_IN_CELL.findall(cell):
        path = re.split(r"[#§]", raw)[0].strip().strip("/")
        if not path:
            continue
        # a leading ./ or a bare filename inside references/ both mean skill-relative
        candidates = [os.path.join(skill_dir, path)]
        if not os.path.exists(candidates[0]) and "/" not in path:
            candidates.append(os.path.join(skill_dir, "references", path))
        if any(os.path.exists(c) for c in candidates):
            found.append(path)
        else:
            problems.append(path)
    if not found and not problems:
        problems.append("(no backticked path in the cell)")
    return found, problems


def check_status(cell):
    status = cell.strip().strip("`").lower()
    if status == "verified":
        return "ok", ""
    if status == "pending":
        return "gap", "still `pending` — inheritance not yet verified"
    m = DROPPED.match(status)
    if m:
        return "dropped", m.group("reason").strip()
    return "gap", f"status `{cell.strip()}` is not one of verified / pending / dropped(<reason>)"


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    skill_dir = os.path.abspath(sys.argv[1])
    if not os.path.isdir(skill_dir) or not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        die(f"[error] not a skill directory (no SKILL.md): {skill_dir}", 2)

    record_path = os.path.join(skill_dir, RECORD_RELPATH)
    if not os.path.isfile(record_path):
        die(f"[error] no provenance record at {RECORD_RELPATH}.\n"
            "        Either this skill never absorbed another skill (nothing to check —\n"
            "        this gate is not a pass or a fail for it), or the merge finished\n"
            "        without committing its record. A name-level \"formerly X, merged\n"
            "        with content preserved\" note is an assertion, not a record:\n"
            "        nothing in it can be re-checked. See references/merge-provenance.md.", 4)

    sources = parse_record(open(record_path, encoding="utf-8", errors="replace").read())
    if not sources:
        die(f"[error] {RECORD_RELPATH} parsed to zero `## Source:` sections.\n"
            "        The gate did not run — an unparsable record proves nothing.", 4)

    default_files, _ = corpus_files(skill_dir)
    print(f"provenance re-verification — {os.path.basename(skill_dir)}")
    print(f"  record: {RECORD_RELPATH} ({len(sources)} source(s)); "
          f"whole-target corpus: {len(default_files)} file(s)\n")

    findings, dropped_rows, verified_rows = [], [], 0
    for src in sources:
        name = src["name"]
        scope = src.get("corpus")
        if scope:
            files, unresolved = corpus_files(skill_dir, scope)
            for u in unresolved:
                findings.append(f"{name}: `**Corpus**` entry `{u}` resolves to nothing — "
                                "a scope that silently widened to the whole target would "
                                "mask loss, so fix the path or drop the field")
        else:
            files, unresolved = default_files, []
        corpus = cp.read_corpus(files)
        print(f"  source: {name}")
        print("    corpus: " + f"{len(files)} file(s)"
              + (f" [scoped: {', '.join(scope[0])}]" if scope else " [whole target]"))

        # --- check 1: frozen facts -------------------------------------------
        if not src["baseline"]:
            findings.append(f"{name}: no `**Baseline**:` line — the frozen fact set is "
                            "missing, so fact coverage cannot be re-checked")
            print("    facts: NO BASELINE DECLARED")
        else:
            bpath = src["baseline"]
            if not os.path.isabs(bpath):
                bpath = os.path.join(skill_dir, BASELINE_DIR, os.path.basename(bpath)) \
                    if not os.path.exists(os.path.join(skill_dir, bpath)) \
                    else os.path.join(skill_dir, bpath)
            if not os.path.isfile(bpath):
                findings.append(f"{name}: baseline `{src['baseline']}` does not resolve "
                                f"(looked at {os.path.relpath(bpath, skill_dir)})")
                print(f"    facts: BASELINE FILE MISSING ({src['baseline']})")
            else:
                frozen = cp.load_baseline(bpath)
                if not frozen:
                    findings.append(f"{name}: baseline `{src['baseline']}` holds 0 frozen "
                                    "tokens — an empty baseline proves nothing")
                    print("    facts: EMPTY BASELINE")
                else:
                    allowed = {t: r for t, r in frozen.items() if r}
                    missing, accepted = cp.check_coverage(set(frozen), allowed, corpus)
                    if missing:
                        findings.append(f"{name}: {len(missing)} frozen fact token(s) no "
                                        "longer appear in the target: "
                                        + ", ".join(missing[:10])
                                        + (" …" if len(missing) > 10 else ""))
                    print(f"    facts: {len(frozen)} frozen, {len(missing)} missing, "
                          f"{len(accepted)} allowed-false-positive")

        # --- check 2: capability routing -------------------------------------
        rows = src["rows"]
        if rows is None:
            findings.append(f"{name}: no capability-inheritance table with columns "
                            f"{' / '.join(TABLE_COLUMNS)} — routing cannot be re-checked")
            print("    capabilities: NO PARSEABLE TABLE")
            continue
        bad_rows = [r for r in rows if "malformed" in r]
        if bad_rows:
            findings.append(f"{name}: {len(bad_rows)} malformed table row(s) — cell count "
                            "does not match the header")
        for row in rows:
            if "malformed" in row:
                continue
            cap = row.get("capability", "?")[:52]
            _, unresolved = resolve_destination(row.get("target destination", ""), skill_dir)
            if unresolved:
                findings.append(f"{name}: capability “{cap}” points at a destination that "
                                f"does not resolve: {', '.join(unresolved)}")
            if not row.get("verification", "").strip():
                findings.append(f"{name}: capability “{cap}” has an empty Verification "
                                "cell — an uncheckable row is not a verifiable checklist")
            verdict, detail = check_status(row.get("status", ""))
            if verdict == "gap":
                findings.append(f"{name}: capability “{cap}” — {detail}")
            elif verdict == "dropped":
                dropped_rows.append(f"{name}: “{cap}” — dropped: {detail}")
            else:
                verified_rows += 1
        total = len(rows) - len(bad_rows)
        print(f"    capabilities: {total} row(s) declared")

    print()
    for d in dropped_rows:
        print(f"  DROPPED (deliberate, reasoned)  {d}")
    if findings:
        print(f"\n{len(findings)} finding(s):")
        for f in findings:
            print(f"  FINDING  {f}")
        print(f"\nrecord: {verified_rows} verified row(s), {len(dropped_rows)} dropped-with-reason.")
        print("The target drifted away from what the merge proved. Repair the target, or —")
        print("when the change was deliberate — update the record and the baseline to say")
        print("so with a reason. Editing this gate's inputs to go green without a reason")
        print("is the same failure as deleting a failing test.")
        sys.exit(3)
    print()
    print(f"record holds: {verified_rows} verified row(s), {len(dropped_rows)} "
          "dropped-with-reason, every baseline clean, every destination resolves.")
    print("Fact + routing coverage re-proven. Behavior-level coverage still needs the")
    print("Verification column's own methods run — this gate does not run them.")
    sys.exit(0)


if __name__ == "__main__":
    main()
