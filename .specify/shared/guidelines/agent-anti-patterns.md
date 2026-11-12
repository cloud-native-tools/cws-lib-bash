# Agent Anti-Patterns (agent 反模式)

> **Owner**: this file owns the shared registry of operations an agent MUST avoid when it acts on a repository.
> The instruction document of every project carries only a POINTER to this file (see the final `## Agent
> Anti-Patterns` section of `.specify/templates/instructions-template.md`); never restate an entry there.
>
> **How the list grows (feedback accumulation)**: a new anti-pattern enters through the feedback mechanism —
> an observed misexecution is recorded via the project's feedback store (`/speckit.feedback`, engine
> `feedback-utils.py`), routed through the improvement flow, and lands here as one dated entry with its
> symptom and its fixed practice. Entries are added, never edited into vagueness; a superseded entry keeps
> its date and gains a pointer to the replacement.

## AP-1 — Unescaped regex metacharacters in text search

- **Symptom**: a search intended as a literal match silently matches something else, and the wrong result is
  then treated as evidence. Measured incident (2026-11-10): `grep [CN]` was used to find a literal `[CN]`
  placeholder; the bracket expression matched any line containing `C` or `N`, nearly the whole tree, and a
  restore pass overwrote files with stale content before being caught.
- **The trap**: `grep`, `find -name`, `sed` and their variants compile their pattern as a regular expression
  by default; `[` `]` `.` `*` `+` `?` `^` `$` `\` are operators, and the SHELL may expand `$VAR`/`${...}`
  before the tool ever sees it.
- **Fixed practice**: for a literal string use a fixed-string mode (`grep -F`) or an explicitly escaped
  pattern; when the term contains shell-active characters, single-quote it or pass it through a program
  (Python exact match) instead of a shell pipeline. State which layer expands the text (shell / tool / both)
  before concluding "not found".

## AP-2 — Shell-expanded literals judged as missing

- **Symptom**: a `${...}`-bearing literal (a template placeholder, a skill path) is reported "missing"
  because the shell expanded it before `grep` ran; or a `ugrep` escape quirk makes a check fail spuriously.
- **Fixed practice**: use Python exact-string matching (or `grep -F` with single quotes) for literals that
  carry `$`, `{}`, backslashes or other shell metacharacters; never conclude absence from a shell-grep miss
  on such a term.

## AP-3 — `find` rooted at an over-broad scope

- **Symptom**: `find /` (or `find ~`) scans unrelated trees, wastes minutes, and can surface matches from
  other projects as if they belonged to the current one.
- **Fixed practice**: root every `find` at the repository (or the named subtree) and bound it
  (`-maxdepth`) when the search is a probe; state the root in the command line so the reading is reproducible.

## AP-4 — Text search used as an existence oracle

- **Symptom**: "the path exists" is concluded because its text appears in some file; or "the path is
  missing" because a grep over one tree found nothing.
- **Fixed practice**: existence is answered by the filesystem (`test -e`, `Path.exists()`, `git ls-files`),
  never by grepping for a path's characters; a text hit only proves that text is present.

## AP-5 — Searches that ignore the live/dated boundary

- **Symptom**: a stale-reference finding counts a dated record's historical citation as a live defect, or
  the reverse — a live normative pointer is excused because a dated copy exists.
- **Fixed practice**: classify every hit before acting — live surfaces (framework sources, the runtime, the
  instructions) versus dated records (`.specify/specs/**` history, archives, run records); a dated record is
  annotated as such, never rewritten to make a search green.
