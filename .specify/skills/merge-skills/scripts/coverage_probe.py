#!/usr/bin/env python3
"""Coverage probe for merge-skills Phase 5 — the no-loss gate.

Extracts high-signal, verbatim-stable "fact tokens" from the source scratch material
(neutral Markdown produced in Phase 2) and checks whether each appears in the rewritten
target docs. Prints the tokens that are MISSING from the target, with a count.

This is deliberately mechanical and literal: it never asks the LLM "did I cover
everything?" (self-confirming). The LLM's judgment is spent only on the residual
missing list — read each destination doc to decide false-positive vs. true omission
(see references/coverage-verification.md).

Usage:
    coverage_probe.py [--allow FILE] [--emit-baseline FILE]
                      <source-material-dir-or-file> <target-doc> [...]
    coverage_probe.py --baseline FILE <target-doc> [...]

Options:
    --allow FILE   Tokens already reviewed and accepted as false positives (the fact
                   survived under different wording). One token per line; '#' starts a
                   comment, so each entry carries its reason. Allowed tokens are
                   reported but do NOT fail the gate — a verified false positive must
                   never force you to distort the target doc to satisfy the probe.

    --emit-baseline FILE
                   Freeze the extracted token set (with the --allow reasons folded in)
                   into a committed baseline file. Written ONLY when the gate reaches
                   exit 0 — an unresolved miss means the merge is lossy, and freezing
                   that state would launder the loss into a "proven" baseline.

    --baseline FILE
                   Re-verification mode: load a previously frozen baseline verbatim and
                   check it against the current target docs. Takes NO source material —
                   the whole point is that the scratch material is long gone. Use it to
                   prove a merged skill still covers what its sources carried, at any
                   later date, after any amount of intervening edit.

Exit code:
    0  every extracted fact token is present in the target corpus or allowed — gate passed
    2  usage error (too few arguments, unreadable --allow file)
    3  unresolved fact tokens missing from the target corpus — gate failed
    4  the gate could not run: source path unreadable, or it yielded zero fact tokens;
       in --baseline mode, the baseline is unreadable or holds zero frozen tokens.
       A probe that read nothing MUST NOT be reported as "coverage clean" — that
       false-green is exactly what the gate exists to prevent (typo'd scratch path, or
       the Phase-8 cleanup already deleted it).

Token classes extracted (things a hand-rewrite most often drops):
    - endpoints / paths            /api/skills/{name}, /oauth/token
    - flags & long options         --dry-run, --unit-type
    - snake/camel identifiers      onExistingPackageJson, code_challenge
    - UPPER_SNAKE constants        SKILL_VERSION_READY
    - UPPER-CASE enum words        READ, WRITE, CREATED (>=3 chars, stoplist-filtered)
    - 3-digit status codes         201, 404, 422
    - inline code spans            `...`  (backtick-delimited)
    - bare URLs                    https://...

NOT extracted — honest limitation, never assume these are gated:
    - lowercase enum words in prose (`pass`, `fail`, `block`) are ordinary English;
      tokenizing them drowns the residual list in noise. They are caught only when the
      source marks them as inline code. Their coverage comes from the capability
      walk-through in references/coverage-verification.md, not from this probe.
    - prose is intentionally not tokenized — it is legitimately reworded during a merge.

Baseline files (--emit-baseline / --baseline):
    A baseline is the FROZEN token set of one merged source: one token per line, an
    optional ' # <reason>' suffix marking a reviewed false positive, '#' lines as
    comments. --baseline loads those tokens VERBATIM; it never re-extracts them.

    That is deliberate, and measured rather than stylistic: extraction is not
    idempotent. Feeding a bare token list back through extract_tokens() loses the
    tokens that only existed because the source backtick-quoted them (`pass`, `fail` —
    the class the limitation above already flags as probe-invisible) and truncates
    relative paths to their leading-slash fragment (`docs/git-workflow.md` ->
    `/git-workflow.md`). A baseline regenerated from a baseline is therefore a
    strictly weaker gate that still prints "coverage clean". Treat the frozen file as
    the authority; if the source material still exists and the baseline looks wrong,
    re-emit from the material.
"""
import os
import re
import sys
import time

# --- token patterns (each returns candidate substrings) --------------------
PATTERNS = [
    r"/[A-Za-z0-9_][A-Za-z0-9_\-./{}]*",          # endpoints / paths
    r"(?<!\w)--[a-zA-Z][a-zA-Z0-9-]+",            # long CLI flags
    r"[A-Za-z][a-zA-Z0-9]*_[a-zA-Z0-9_]+",        # snake_case identifiers
    r"[a-z]+[A-Z][a-zA-Z0-9]+",                   # camelCase identifiers
    r"[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+",          # UPPER_SNAKE constants
    r"\b[A-Z][A-Z0-9]{2,}\b",                     # UPPER-CASE enum words
    r"(?<![\d.])[1-5]\d{2}(?!\d)",                # 3-digit HTTP-style status codes
    r"`[^`\n]+`",                                 # inline code spans
    r"https?://[^\s)\]<>`\"']+",                  # bare URLs
]

# tokens that are pure noise / too generic to be meaningful facts
STOPWORDS = {
    "https://", "http://", "/", "//", "/.", "./", "../",
}

# UPPER-CASE words that are normative prose, discourse, or document-format acronyms
# rather than domain enum values. Deliberately narrow: a domain term wrongly listed here
# becomes an invisible hole in the gate, so prefer letting noise through and recording it
# in the --allow file. State words (SUCCESS, FAILED, ERROR, TRUE, NULL) are NOT listed —
# they are exactly the enum values a hand-rewrite drops.
CAPS_STOPWORDS = {
    # RFC-2119 / normative prose
    "MUST", "MUSTS", "SHOULD", "SHALL", "MAY", "CAN", "CANNOT", "NEVER", "ALWAYS",
    "ONLY", "NOT", "AND", "OR", "BUT", "THE",
    # prose / discourse
    "YES", "OK", "TODO", "FIXME", "NOTE", "NOTES", "TBD", "WARNING", "WARN",
    "IMPORTANT", "EXAMPLE", "EXAMPLES", "ETC", "VS", "VIA", "PER", "ALL", "ANY",
    "EACH", "EVERY", "NA", "II", "III", "IV",
    # document / markup format
    "SKILL", "SKILLS", "MD", "TXT", "PY", "SH", "JSON", "YAML", "XML", "HTML",
    "CSS", "URL", "URLS", "URI", "PDF", "API", "APIS", "CLI", "HTTP", "HTTPS",
    "SQL", "DB", "README", "CHANGELOG", "UTF", "ASCII", "CJK", "ISO",
    "UTC", "GMT",
}


def read_material(path):
    """Concatenate all .md/.txt material under a dir, or a single file."""
    if os.path.isfile(path):
        return open(path, encoding="utf-8", errors="replace").read()
    chunks = []
    for root, _, files in os.walk(path):
        for f in sorted(files):
            if f.endswith((".md", ".txt")):
                chunks.append(open(os.path.join(root, f), encoding="utf-8",
                                   errors="replace").read())
    return "\n".join(chunks)


def read_corpus(paths):
    parts = []
    for p in paths:
        if os.path.isfile(p):
            parts.append(open(p, encoding="utf-8", errors="replace").read())
        elif os.path.isdir(p):
            parts.append(read_material(p))
    return "\n".join(parts)


# Provenance artifacts must never be part of the corpus they are checked against.
PROVENANCE_DIRNAME = "merge-provenance"
PROVENANCE_RECORD = "merge-provenance.md"


def read_corpus_excluding_provenance(paths, baseline_path=None):
    """Read the target corpus, excluding the provenance record and every baseline file.

    Load-bearing, not cosmetic: a baseline lists each frozen token by construction, so a
    corpus that includes the baseline directory matches every token unconditionally and
    re-verification can never fail — a false green in the exact path whose job is to
    catch drift. The record is excluded for the same reason: its Verification cells quote
    the tokens being checked. The same hazard applies at merge time when the target
    already carries baselines from an earlier merge, so both modes filter.

    Explicitly named files are still honored (minus the baseline itself), so a caller can
    point the probe at one doc deliberately.
    """
    base_abs = os.path.abspath(baseline_path) if baseline_path else None
    keep = []
    for p in paths:
        if os.path.isfile(p):
            if os.path.abspath(p) != base_abs:
                keep.append(p)
            continue
        if not os.path.isdir(p):
            keep.append(p)  # let the caller surface the unreadable path
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs
                       if d not in {"__pycache__", ".git", PROVENANCE_DIRNAME}]
            for f in sorted(files):
                if not f.endswith((".md", ".txt")) or f == PROVENANCE_RECORD:
                    continue
                fp = os.path.join(root, f)
                if os.path.abspath(fp) != base_abs:
                    keep.append(fp)
    return read_corpus(keep)


def read_allow_list(path):
    """Read accepted false positives: one token per line, '#' comments, blanks ignored.

    Returns {token: reason}. A reason may be trailing (`tok # why`) or carried by the
    comment line above a run of tokens — the grouping style real allow files use, where
    one explanation covers several renames. Last comment before a token wins; a trailing
    reason overrides it. Reasons matter beyond bookkeeping: --emit-baseline folds them
    into the frozen baseline, and a frozen token with no reason re-reads as *required*,
    turning an accepted false positive into a permanent false red.
    """
    allowed, pending = {}, ""
    for line in open(path, encoding="utf-8", errors="replace"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            pending = stripped.lstrip("#").strip()
            continue
        tok, sep, reason = stripped.partition("#")
        tok = tok.strip()
        if tok:
            allowed[tok] = reason.strip() if sep else pending
    return allowed


# A baseline line is `<token>` with an optional ` # <reason>`. The reason separator
# requires whitespace on both sides so a token that legitimately contains '#' (a URL
# fragment) is not truncated by its own annotation.
BASELINE_LINE = re.compile(r"^(?P<tok>.*?)(?:\s+#\s+(?P<reason>.*))?$")

# A token may itself be a backtick-quoted Markdown heading or shell comment (`## Git
# Workflow`, `# ── 前置 ──`). Written bare, such a line is indistinguishable from a
# comment and silently disappears on re-read — a baseline that quietly holds fewer facts
# than the merge proved. Tokens can never contain a backtick (extract_tokens strips them
# and the code-span pattern excludes internal ones), so backtick quoting is lossless.
QUOTED_LINE = re.compile(r"^`(?P<tok>[^`]*)`(?:\s+#\s+(?P<reason>.*))?$")


def _needs_quoting(tok):
    return tok.lstrip().startswith("#") or " # " in tok


def _emit_token(tok):
    return f"`{tok}`" if _needs_quoting(tok) else tok


def load_baseline(path):
    """Load a frozen token set verbatim: {token: reason-or-empty}. No re-extraction."""
    frozen = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("`"):
            m = QUOTED_LINE.match(stripped)
            if not m:
                continue
            tok, reason = m.group("tok"), m.group("reason") or ""
        else:
            m = BASELINE_LINE.match(stripped)
            tok, reason = m.group("tok"), m.group("reason") or ""
        tok = tok.strip()
        if tok:
            frozen[tok] = reason.strip()
    return frozen


def write_baseline(path, tokens, allowed, src):
    """Freeze the proven token set so the gate stays re-runnable after scratch cleanup."""
    stamped = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    lines = [
        "# merge baseline — frozen fact tokens of one merged source skill",
        f"# source-material: {src}",
        f"# frozen: {stamped} by coverage_probe.py --emit-baseline (gate at exit 0)",
        "#",
        "# Re-verify at any later date, with no scratch material present:",
        f"#   coverage_probe.py --baseline {os.path.basename(path)} <target-doc>...",
        "#",
        "# A trailing ' # <reason>' marks a token reviewed as a verified false positive",
        "# (the fact survived under different wording); it never fails the gate.",
        "# A backtick-quoted line is a token whose own text starts with '#' or contains",
        "# ' # ' — quoting keeps it from being read back as a comment.",
        "# Tokens are FROZEN — --baseline loads them verbatim and never re-extracts.",
        "# Do not regenerate this file from itself: extraction is not idempotent, and a",
        "# re-extracted baseline is a weaker gate that still prints 'coverage clean'.",
    ]
    for tok in sorted(tokens):
        reason = allowed.get(tok, "")
        emitted = _emit_token(tok)
        lines.append(f"{emitted} # {reason}" if reason else emitted)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(tokens), sum(1 for t in tokens if allowed.get(t))


def check_coverage(tokens, allowed, corpus):
    """Split tokens into (unresolved-missing, accepted-false-positives) against corpus."""
    missing, accepted = [], []
    for t in sorted(tokens):
        inner = t[1:-1] if t.startswith("`") and t.endswith("`") else t
        if t in corpus or inner in corpus:
            continue
        (accepted if t in allowed else missing).append(t)
    return missing, accepted


def extract_tokens(text):
    found = set()
    for pat in PATTERNS:
        for m in re.findall(pat, text):
            tok = m.strip("`.,;:)（）]").strip()
            if len(tok) < 3:
                continue
            if tok in STOPWORDS or tok in CAPS_STOPWORDS:
                continue
            found.add(tok)
    # Drop UPPER-CASE fragments of a longer UNDER_SCORE constant: the constant pattern
    # already covers `SKILL_VERSION_READY`, so a bare `READY` is residue, not a fact.
    # Component-delimited only — a plain substring test also swallows independent enum
    # words that merely occur inside a longer constant (`READ` inside `..._READY`),
    # which is a silent false-negative in a gate whose whole job is not losing facts.
    components = {part for t in found if "_" in t for part in t.split("_") if part}
    if components:
        found = {t for t in found if "_" in t or t not in components}
    return found


FILE_OPTS = ("--allow", "--emit-baseline", "--baseline")


def parse_args(argv):
    """Split the file options out of argv (any position); return (opts, positional)."""
    opts, rest, i = {}, [], 0
    while i < len(argv):
        if argv[i] in FILE_OPTS:
            if i + 1 >= len(argv):
                print(f"[error] {argv[i]} requires a file path", file=sys.stderr)
                sys.exit(2)
            opts[argv[i].lstrip("-").replace("-", "_")] = argv[i + 1]
            i += 2
            continue
        rest.append(argv[i])
        i += 1
    return opts, rest


def report(missing, accepted, token_count, label):
    print(f"{label}: {token_count}; unresolved missing: {len(missing)}; "
          f"allowed false positives: {len(accepted)}\n")
    for t in missing:
        print(f"  MISSING  {t}")
    for t in accepted:
        print(f"  ALLOWED  {t}")


def run_baseline_mode(baseline_path, targets):
    """Re-verify a merged target against a frozen baseline. No source material needed."""
    if not os.path.isfile(baseline_path):
        print(f"[error] baseline not found: {baseline_path}\n"
              "        Re-verification cannot run on a baseline it did not read. This is\n"
              "        not a pass — locate the committed baseline under the target's\n"
              "        references/merge-provenance/, or re-emit it from source material.",
              file=sys.stderr)
        sys.exit(4)
    frozen = load_baseline(baseline_path)
    if not frozen:
        print(f"[error] baseline at {baseline_path} holds 0 frozen tokens.\n"
              "        An empty baseline proves nothing — refusing to report coverage.",
              file=sys.stderr)
        sys.exit(4)
    corpus = read_corpus_excluding_provenance(targets, baseline_path)
    # Only tokens carrying a reason are accepted false positives. Passing the whole
    # frozen dict here would make every token "allowed" and the gate could never fail —
    # a false-green, which is the one outcome this probe exists to prevent.
    allowed = {t: reason for t, reason in frozen.items() if reason}
    missing, accepted = check_coverage(set(frozen), allowed, corpus)
    report(missing, accepted, len(frozen),
           f"frozen baseline tokens ({os.path.basename(baseline_path)})")
    if missing:
        print(f"\n{len(missing)} frozen token(s) no longer appear in the target. The\n"
              "target drifted after the merge: an absorbed fact was dropped by a later\n"
              "edit. Restore it, or — if the capability was deliberately retired — update\n"
              "the capability-inheritance row in references/merge-provenance.md and prune\n"
              "the token from the baseline with a reason. Never delete the baseline to go\n"
              "green.")
        sys.exit(3)
    print("baseline clean — the merged target still carries every frozen fact token.")
    sys.exit(0)


def main():
    opts, argv = parse_args(sys.argv[1:])
    allow_path = opts.get("allow")
    emit_path = opts.get("emit_baseline")
    baseline_path = opts.get("baseline")

    if baseline_path:
        if not argv:
            print(__doc__)
            sys.exit(2)
        run_baseline_mode(baseline_path, argv)

    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    src, targets = argv[0], argv[1:]

    allowed = {}
    if allow_path:
        if not os.path.isfile(allow_path):
            print(f"[error] --allow file not readable: {allow_path}", file=sys.stderr)
            sys.exit(2)
        allowed = read_allow_list(allow_path)

    if not os.path.exists(src):
        print(f"[error] source material not found: {src}\n"
              "        The no-loss gate cannot run on material it did not read. Fix the\n"
              "        path, or re-extract if Phase-8 cleanup already removed the scratch.",
              file=sys.stderr)
        sys.exit(4)

    material = read_material(src)
    corpus = read_corpus_excluding_provenance(targets, emit_path)
    tokens = extract_tokens(material)

    if not material.strip() or not tokens:
        print(f"[error] source material at {src} yielded 0 fact tokens "
              f"({len(material.strip())} chars read).\n"
              "        Refusing to report coverage — an empty probe is not a passed gate.\n"
              "        Check the scratch dir holds the Phase-2 neutral material (.md/.txt).",
              file=sys.stderr)
        sys.exit(4)

    # a token is covered if it appears verbatim anywhere in the target corpus;
    # for inline-code spans, also test the un-backticked inner text.
    missing, accepted = check_coverage(tokens, allowed, corpus)
    report(missing, accepted, len(tokens), "fact tokens extracted")

    stale = set(allowed) - tokens
    if stale:
        print(f"\n[note] {len(stale)} --allow entr(y/ies) match no current token "
              f"(prune them): {', '.join(sorted(stale)[:8])}")

    if missing:
        if emit_path:
            print(f"\n[error] --emit-baseline refused: {len(missing)} unresolved miss(es).\n"
                  "        Freezing a lossy state would launder the loss into a 'proven'\n"
                  "        baseline. Drive the misses to zero first.", file=sys.stderr)
        print(f"\n{len(missing)} unresolved token(s) not found verbatim — read each "
              "destination doc to classify false-positive (fact survived reworded → add "
              "to the --allow file with a one-line reason) vs. true omission (add it to "
              "the doc and re-run). See references/coverage-verification.md.")
        sys.exit(3)

    if emit_path:
        unreasoned = [t for t in accepted if not allowed.get(t)]
        if unreasoned:
            print(f"[error] --emit-baseline refused: {len(unreasoned)} accepted false "
                  f"positive(s) carry no reason: "
                  f"{', '.join(sorted(unreasoned)[:6])}\n"
                  "        A frozen token with no reason re-reads as REQUIRED, so this\n"
                  "        allowance would flip into a permanent false red on every later\n"
                  "        re-verification. Give it a one-line reason in the --allow file\n"
                  "        (trailing ' # why', or a comment line above the token).",
                  file=sys.stderr)
            sys.exit(3)
        frozen, annotated = write_baseline(emit_path, tokens, allowed, src)
        print(f"\nbaseline frozen: {emit_path} ({frozen} tokens, {annotated} annotated as "
              "verified false positives).\nCommit it with the target — it is what makes "
              "this gate re-runnable after the scratch is cleaned.")
    print("coverage clean — every fact token is present in the target or allowed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
