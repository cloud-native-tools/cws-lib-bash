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

Host AI agent CLIs (Claude Code / Codex CLI / Qoder CLI / GitHub Copilot / opencode / Hermes Agent) give sessions only auto-generated IDs — there is no official naming/renaming mechanism. `/speckit.session` lands the degraded route: **rename on the export side**. **Scope = ONE session** treated as a data object: located, verified, copied out under a user-chosen name — success is a faithful, complete raw export, not an interpretation of it. Cross-session concept/theme aggregation (mining value out of the project's entire conversation history) is `/speckit.history`'s job — never grow this command toward content analysis.

## Glossary

Consult `.specify/memory/glossary.md` and apply `.specify/shared/workflow/glossary.md`: map recorded homophone/confusable variants to canonical terms before acting, surfacing each correction. At wrap-up propose new project-specific terms (`origin=auto`, `status=proposed`) with user confirmation.

## Delegation

The export's heavy lifting is delegated to one internal skill; this command owns only the interaction and the gate (below).

- **Skill**: `archive-session` — runtime path `.specify/skills/internal/archive-session/SKILL.md`; export engine `.specify/scripts/export.py` beside the SKILL.md (runtime: `.specify/skills/internal/archive-session/scripts/export.py`). Deterministic rules (session location, tool detection, meta extraction, budget verdicts) live in the engine — call it; do not re-derive its judgments in prose.
- **Inputs**: `--name <bundle-name>` (**必填**, collected at the gate below) plus optional `--session <id>` / `--tool <name>` / `--verify <text>`; the skill's 调用 section owns engine invocation (bash / PowerShell, interpreter probing) and its exit-code table: `0` ok · `2` invalid arguments (missing/bad `--name`, empty `--session`, same-name conflict) · `3` no matching session · `4` no supported tool usable (includes copilot/hermes probe declarations "会话存储未探测到") · `5` IO/SQLite error. A non-zero exit is a **verdict**: report it, never argue around it.
- **Outputs**: the `.session-export/<name>/` bundle under the export root `<repo-root>/.session-export/` — raw session records (read-only copy: records are copied, never moved or mutated), `session-meta.json` (deterministic meta), and `SESSION.md` (元信息 section deterministic + 结构化总结 placeholder).
- **SESSION.md structured summary**: the fill-in is owned by the skill's 描述文档流程 — three fixed subsections (任务脉络 / 关键决策 / 产物清单) faithful to the records, budget-overrun skeleton degradation, running-session as-of-snapshot note; never modify the 元信息 section. Do not restate the procedure here.
- **Boundaries**: read-only toward host session storage; `.session-export/` version-control policy follows the project's `.gitignore` (never edit it from this command); the six-tool support matrix is the engine's contract — tools outside it are not export targets.

## Modes

Mode is inferred from `$ARGUMENTS`. Exactly one subcommand:

| Subcommand | Purpose | Writes |
|------------|---------|--------|
| `export` | export the current (or specified) session into a user-named directory under `.session-export/` | `.session-export/<name>/` |

Unknown intent → report the capability list (only `export` today); do not guess.

## Outline

1. **Collect the export parameters**:
   - `--name <bundle-name>` is **必填** — the bundle directory name; never auto-generate one (naming is the purpose of this command). Grammar: safe path segment (first character alphanumeric, remaining `[A-Za-z0-9_.-]`); violations are rejected.
   - Optional: `--session <id>` (explicit session id), `--tool <name>` (one of `claude-code / codex-cli / qoder-cli / copilot / opencode / hermes`), `--verify <text>` (a distinctive recent user utterance, used to confirm/relocate the chosen session — fill it yourself from the current conversation; the user never provides it).

2. **Preview → confirm → execute.** Before running the engine, disclose all four elements and proceed only on explicit confirmation:
   - **工具**: the detected or specified tool;
   - **会话**: the session id and how it was located (auto / `--session` / `--tool`);
   - **目标**: the absolute bundle path `.session-export/<name>/`;
   - **规模**: the estimated record size when obtainable.

   Same-name conflict: if `.session-export/<name>/` already exists, refuse by default. Override (覆盖) only through an **interactive confirmation** inside this gate (the override clears the directory before rewriting, no leftovers). There is no bypass flag of any kind; in non-interactive contexts a same-name re-export fails and the user picks another name.
   > Gate probe: gate-session-export-overwrite — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

3. **Execute via the skill** — never reimplement export logic in this command; the engine invocation forms and exit codes live in the skill's 调用 / 退出码 sections.

4. **Complete the description document** per the skill's 描述文档流程 (ownership note in `## Delegation` above).

5. **Report**: bundle path, description-document path, and the meta summary (tool / session id / model / time window).

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.session" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.session" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.session" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"

## Handoffs

**Before**: none — any active AI agent CLI session can be exported at any time.

**After**: for team-run traceability, export dispatched-member sessions named by their dispatch label (`<team-slug>--<run-stamp>--<member-role>`) so `/speckit.team` run reports' mapping tables can reference the bundles.