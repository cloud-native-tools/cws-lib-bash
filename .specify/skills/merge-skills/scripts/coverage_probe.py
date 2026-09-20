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
    coverage_probe.py [--allow FILE] <source-material-dir-or-file> <target-doc> [...]

Options:
    --allow FILE   Tokens already reviewed and accepted as false positives (the fact
                   survived under different wording). One token per line; '#' starts a
                   comment, so each entry carries its reason. Allowed tokens are
                   reported but do NOT fail the gate — a verified false positive must
                   never force you to distort the target doc to satisfy the probe.

Exit code:
    0  every extracted fact token is present in the target corpus or allowed — gate passed
    2  usage error (too few arguments, unreadable --allow file)
    3  unresolved fact tokens missing from the target corpus — gate failed
    4  the gate could not run: source path unreadable, or it yielded zero fact tokens.
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
"""
import os
import re
import sys

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


def read_allow_list(path):
    """Read accepted false positives: one token per line, '#' comments, blanks ignored."""
    allowed = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        tok = line.split("#", 1)[0].strip()
        if tok:
            allowed.add(tok)
    return allowed


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
    # Fragments-of-a-constant only — an independent enum word is never dropped.
    compound = [t for t in found if "_" in t]
    if compound:
        found = {t for t in found
                 if "_" in t or not any(t != c and t in c for c in compound)}
    return found


def parse_args(argv):
    """Split `--allow FILE` out of argv (any position); return (allow_path, positional)."""
    allow_path, rest, i = None, [], 0
    while i < len(argv):
        if argv[i] == "--allow":
            if i + 1 >= len(argv):
                print("[error] --allow requires a file path", file=sys.stderr)
                sys.exit(2)
            allow_path = argv[i + 1]
            i += 2
            continue
        rest.append(argv[i])
        i += 1
    return allow_path, rest


def main():
    allow_path, argv = parse_args(sys.argv[1:])
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    src, targets = argv[0], argv[1:]

    allowed = set()
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
    corpus = read_corpus(targets)
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
    missing, accepted = [], []
    for t in sorted(tokens):
        inner = t[1:-1] if t.startswith("`") and t.endswith("`") else t
        if t in corpus or inner in corpus:
            continue
        (accepted if t in allowed else missing).append(t)

    print(f"fact tokens extracted: {len(tokens)}; "
          f"unresolved missing: {len(missing)}; allowed false positives: {len(accepted)}\n")
    for t in missing:
        print(f"  MISSING  {t}")
    for t in accepted:
        print(f"  ALLOWED  {t}")

    stale = allowed - tokens
    if stale:
        print(f"\n[note] {len(stale)} --allow entr(y/ies) match no current token "
              f"(prune them): {', '.join(sorted(stale)[:8])}")

    if missing:
        print(f"\n{len(missing)} unresolved token(s) not found verbatim — read each "
              "destination doc to classify false-positive (fact survived reworded → add "
              "to the --allow file with a one-line reason) vs. true omission (add it to "
              "the doc and re-run). See references/coverage-verification.md.")
        sys.exit(3)
    print("coverage clean — every fact token is present in the target or allowed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
