---
description: 将当前会话导出到用户命名的目录
---
<!-- AUTO-GENERATED from templates/commands/session.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Positioning

Host AI agent CLIs (Claude Code / Codex CLI / Qoder CLI / GitHub Copilot / opencode / Hermes Agent) give sessions only auto-generated IDs — there is no official naming/renaming mechanism. `/speckit.session` lands the degraded route: **rename on the export side** — export the session's raw records into a directory whose name the user chooses, plus a session description document (deterministic meta + structured summary). The export's heavy lifting is delegated to the `archive-session` skill; this command owns only the interaction and the gate.

Deterministic rules (session location, tool detection, meta extraction, budget verdicts) live in `skills/archive-session/scripts/export.py`. Call the engine; do not re-derive its judgments in prose.

**Scope & unit of work** — what makes this command distinct from `/speckit.history`:

- **Scope = ONE session**: the current (or explicitly specified) session, treated as a **data object** — located, verified, copied out under a user-chosen name. Success is a faithful, complete raw export, not an interpretation of it.
- **Unit of work = session data management**: export / naming / archiving. The bundled description document (`SESSION.md`) is a light, snapshot-level inventory (任务脉络 / 关键决策 / 产物清单) kept faithful to the records — it is **not** concept extraction.
- **Counterpart**: mining *value* out of the project's **entire** conversation history — cross-session concept/theme aggregation (decisions, lessons, TODOs, flows, conflicts) — is `/speckit.history`'s job. Never grow this command toward content analysis; route concept-level needs there.

## Glossary

Consult `.specify/memory/glossary.md` and apply `.specify/shared/workflow/glossary.md`: map recorded homophone/confusable variants to canonical terms before acting, surfacing each correction. At wrap-up propose new project-specific terms (`origin=auto`, `status=proposed`) with user confirmation.

## Modes

Mode is inferred from `$ARGUMENTS`. The first version exposes exactly one subcommand:

| Subcommand | Purpose | Writes |
|------------|---------|--------|
| `export` | export the current (or specified) session into a user-named directory under `.session-export/` | `.session-export/<name>/` |

Unknown intent → report the capability list (only `export` today); do not guess.

## Outline

1. **Resolve context**: the export root is `<repo-root>/.session-export/`; the engine is `skills/archive-session/scripts/export.py`.

2. **Collect the export parameters**:
   - `--name <bundle-name>` is **必填** — the bundle directory name; never auto-generate one (naming is the purpose of this command). Grammar: safe path segment (first character alphanumeric, remaining `[A-Za-z0-9_.-]`); violations are rejected.
   - Optional: `--session <id>` (explicit session id), `--tool <name>` (one of `claude-code / codex-cli / qoder-cli / copilot / opencode / hermes`), `--verify <text>` (a distinctive recent user utterance, used to confirm/relocate the chosen session — fill it yourself from the current conversation; the user never provides it).

3. **Preview → confirm → execute.** Before running the engine, disclose all four elements and proceed only on explicit confirmation:
   - **工具**: the detected or specified tool;
   - **会话**: the session id and how it was located (auto / `--session` / `--tool`);
   - **目标**: the absolute bundle path `.session-export/<name>/`;
   - **规模**: the estimated record size when obtainable.

   Same-name conflict: if `.session-export/<name>/` already exists, refuse by default. Override (覆盖) only through an **interactive confirmation** inside this gate (the override clears the directory before rewriting, no leftovers). There is no bypass flag of any kind; in non-interactive contexts a same-name re-export fails and the user picks another name.
   > Gate probe: gate-session-export-overwrite — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

4. **Execute via the engine** — never reimplement export logic here:

   ```bash
   python3 skills/archive-session/scripts/export.py \
     --name "<bundle-name>" --verify "<distinctive recent user text>"
   # explicit forms:
   python3 skills/archive-session/scripts/export.py --name "<n>" --session "<session-id>"
   python3 skills/archive-session/scripts/export.py --name "<n>" --tool claude-code
   ```

   Exit codes: `0` ok · `2` invalid arguments (missing/bad `--name`, empty `--session`, same-name conflict) · `3` no matching session · `4` no supported tool usable (includes copilot/hermes probe declarations "会话存储未探测到") · `5` IO/SQLite error. A non-zero exit is a **verdict**: report it, never argue around it.

5. **Complete the description document.** The engine writes `session-meta.json` plus `SESSION.md` whose 元信息 section is deterministic and whose 结构化总结 section is a placeholder. Read the exported raw records and fill that section in place — three fixed subsections: **任务脉络**, **关键决策**, **产物清单** — faithful to the records (never invent decisions or artifacts; no fact source beyond the records). When `session-meta.json` says `over_summary_budget: true`, write a skeleton summary instead and declare the degradation reason and the triggered threshold. Never modify the 元信息 section. A running session (`snapshot: true`) is summarized as-of the snapshot moment — say so.

6. **Report**: bundle path, description-document path, and the meta summary (tool / session id / model / time window).

## Boundaries

- The export is **read-only** toward host session storage — records are copied, never moved or mutated.
- Version-control policy for `.session-export/` follows the project's `.gitignore` (the framework's own repo ignores it by owner decision 2026-08-15); never edit `.gitignore` from this command.
- The six-tool support matrix is the engine's contract; tools outside it are not export targets.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.session" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point, apply the docs-sync evaluation per `.specify/shared/workflow/docs-step.md` and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up.

## Handoffs

**Before**: none — any active AI agent CLI session can be exported at any time.

**After**: for team-run traceability, export dispatched-member sessions named by their dispatch label (`<team-slug>--<run-stamp>--<member-role>`) so `/speckit.team` run reports' mapping tables can reference the bundles.