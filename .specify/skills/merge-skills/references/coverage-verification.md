# Coverage Verification — the no-loss gate (Phase 5)

This is what separates a real merge from a lossy one. A folder merge trivially "keeps
everything" because it copies files; a **restructure** rewrites content by hand, so it can
silently drop a parameter, an enum value, or a whole sub-capability. Phase 5 proves it didn't.

Principle: **prove, don't assert, no-loss.** "I think I got everything" is not a completed
merge. The proof is mechanical and repeatable (program-first): extract fact tokens from the
scratch material, check each appears in the rewritten target docs, drive the *unresolved*
misses to zero.

## Method

```bash
python3 ${SKILL_HOME}/scripts/coverage_probe.py [--allow FILE] <source-material> <target-doc>...
```

- **Input A** — the Phase-2 scratch material dir (neutral Markdown), the ground truth of what
  the source carried. A single file also works, which is what makes the reverse direction free.
- **Input B** — the rewritten target docs (the new/edited reference docs + the target
  `SKILL.md`).
- **Output** — the fact tokens found in A that do **not** appear verbatim in B, split into
  `MISSING` (unresolved) and `ALLOWED` (reviewed false positives).

### Exit codes — the gate is the code, not your impression

| Exit | Meaning | Action |
|------|---------|--------|
| `0` | every token present in the target, or allowed | gate passed |
| `2` | usage error (too few arguments, unreadable allow file) | fix the invocation |
| `3` | unresolved misses remain | judge each (below), then re-run |
| `4` | **the gate did not run** — source path missing, or it yielded 0 tokens | never a pass: fix the path or re-extract, then re-run |

Exit `4` is the trap worth naming: a typo'd scratch path — or a Phase-8 cleanup that already
deleted it — reads nothing, and a probe that read nothing has proved nothing.

### Prove both directions

Phase 3 usually edits *existing* target docs to absorb source fragments, so the target can lose
its own facts while gaining the source's. The same probe covers that direction: feed it the
pre-merge version of the edited doc as material.

```bash
git show HEAD:<target-doc> > /tmp/pre-merge.md      # a temp file — not <(...)
python3 ${SKILL_HOME}/scripts/coverage_probe.py /tmp/pre-merge.md <target-doc>
```

Process substitution (`<(git show …)`) does **not** work: the probe is handed a pipe, reads zero
chars, and exits `4`. Both directions must reach exit `0` before Phase 7.

## Fact-token classes

The probe extracts high-signal, verbatim-stable tokens — the things a hand-rewrite is most
likely to drop — not prose (prose is legitimately reworded):

| Class | Examples |
|-------|----------|
| Endpoints / paths | `/api/skills/{name}`, `/oauth/token` |
| Flags & long options | `--dry-run`, `--unit-type` |
| `snake_case` / `camelCase` identifiers | `code_challenge`, `onExistingPackageJson` |
| `UPPER_SNAKE` constants — switch keys, event types | `SKILL_VERSION_READY` |
| `UPPER-CASE` enum words (≥3 chars, stoplist-filtered) | `READ`, `WRITE`, `CREATED` |
| 3-digit status codes | `201`, `404`, `422` |
| Inline code spans | anything backtick-delimited |
| Bare URLs | `https://…` |

**Know the hole you are standing in.** Lowercase enum words in prose (`pass`, `fail`, `block`)
are ordinary English: tokenizing them drowns the residual list in noise, so they are caught
**only** when the source marks them as inline code. Reworded prose is never tokenized, by design.
When the facts you care about most fall in a class the probe does not extract, the capability
walk-through below is their only gate — say that plainly in the report instead of citing a green
probe as proof of full coverage.

The `UPPER-CASE` class is deliberately permissive. A domain acronym suppressed by the stoplist
becomes an invisible hole in the gate, so noise is preferred and absorbed by the allow file:
expect prose caps (`AFTER`, `FIRST`, `PATH`) in the residual list on doc-heavy sources. State
words (`SUCCESS`, `FAILED`, `ERROR`, `NULL`) are **not** stoplisted — they are exactly the enum
values a hand-rewrite drops.

## Judging the misses

Each residual miss is one of two things — read to decide, do not blindly "fix":

1. **False positive — the fact survived under different wording, or was merged into a table
   cell.** The probe matches substrings, so a token split across a reworded sentence can miss.
   Confirm by reading the destination doc; if the *fact* is present, record it in an allow file:

   ```text
   # allowed false positives — one token per line; '#' carries the reason
   /oauth/token   # renamed /oauth2/token in the target; endpoint documented in §Auth
   ```

   Re-run with `--allow <file>`. Allowed tokens print as `ALLOWED` and no longer fail the gate;
   entries that match no current token are reported as stale so you can prune them. **Never** edit
   the target doc into containing a stale token just to reach exit `0` — that corrupts the target
   to satisfy the instrument. The allow file is the audit trail, and it travels with the report.

2. **True omission — the fact genuinely didn't make it.** Add it to the right destination doc
   (per the Phase-3 mapping table) and re-run.

Proceed to Phase 7 only at exit `0` in **both** directions: unresolved misses `0`, every residual
accounted for in the allow file. Never delete the source form while real content is still
unaccounted for.

## Complement with a capability walk-through

The token probe catches dropped *facts*; also do a quick **capability walk-through** for
dropped *behaviors*: for each capability family in the Phase-1 source inventory, confirm the
merged target can still serve that scenario end-to-end. A capability can be "token-covered"
(all its nouns present) yet "behavior-lost" (no doc actually tells the agent how to invoke
it). Both checks must pass.

## Why verbatim, not semantic

The check is deliberately mechanical and literal so it's cheap, deterministic, and
un-foolable — it never asks the LLM "did I cover everything?" (which self-confirms). The LLM's
judgment is spent only on the small residual list, where reading a few destinations resolves
false positives fast.
