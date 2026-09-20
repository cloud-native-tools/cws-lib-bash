# Canonical `## Feedback` Step

This file is the single source of truth for the `## Feedback` step that every
qualifying unit embeds. Skills embed it as their final workflow section; every
**complex** command template embeds it at their wrap-up / Git-commit-prompt stage.
Simple commands MUST NOT embed it — a command is complex iff it invokes
scripts/CLI tools, produces an artifact another flow consumes, or consumes another
flow's artifact.

**Embedding units reference this file; they do not copy it.** Each embedded
`## Feedback` section is one of the two short pointer forms in § *Embedded reference
forms* below — copy the form that matches the surface, substitute only the unit id,
and add nothing else. Divergent wording between surfaces is a defect, not a local
adaptation: those two forms are the whole embedded surface, and every rule a reader
needs in order to act lives here.

User-facing wording and context rules are defined once in `.specify/shared/guidelines/user-facing-comprehension.md` (this file covers surface class ③); its condition sets MUST NOT be restated here.

## Positioning & Red Lines

These four facts govern every part of the mechanism and outrank any embedded wording:

1. **Target = the Spec Kit framework itself.** Feedback describes friction in Spec Kit's
   templates, commands, skills, scripts, and docs — never an assessment of the LLM, the
   agent CLI/harness, or the user's project code.
2. **Feedback is user data and fully optional.** The user may ignore the threshold
   prompt, leave entries unprocessed forever, or delete the store. No flow may block,
   nag repeatedly, or degrade because feedback was not handled.
3. **Zero automated transmission.** Neither the engine nor any embedding unit may
   upload, push, or otherwise send feedback anywhere. The only legitimate transmission
   paths are (a) the user manually sending a packaged zip, and (b) the user committing
   feedback files to their own git repository. `mark-submitted` is local bookkeeping
   ("user confirmed disposition"), not an upload.
4. **Local workaround value.** Until a Spec Kit version update lands, past entries are a
   reference for working around recurring issues — see *Workaround lookup* below.

**Goal anchor (Constitution Principle XIII — Better-Harness Orientation).** Feedback is one
of the framework's Better-Harness instruments: it strengthens the **Learning Capture**
dimension of the goal model defined once in `.specify/shared/guidelines/better-harness.md`.
Vocabulary note: the "harness" in red line 1 means the agent CLI/runtime (the host); the
goal model's "Harness" means the project-level execution environment that Spec Kit's
artifacts help build. The anchor adds orientation only — it never overrides these red lines.

**Relationship to Self-Improvement.** Feedback is an optional observation sensor, never a
mutation authority or a complete improvement loop. A matching framework Execution Subject may
consume its own feedback through `self-improvement-workflow.md`, but only after evidence
qualification; non-framework subjects MUST use their own run evidence instead of repurposing
this framework-only store. Concept boundary:
`.specify/shared/definitions/self-improvement-definitions.md`.

---

## Reflection procedure (the embedded step points here)

**Runtime-mode precondition (skills only).** If `${SKILL_WORKDIR}/.specify/` does not
exist, the skill is running in standalone mode (a non–Spec Kit deployment, e.g. a
global agent skills directory) — skip this entire step: no engine call, no feedback
entry. Detection semantics: `.specify/shared/workflow/runtime-mode.md`. Commands
(`/speckit.*`) only ever run inside a Spec Kit project, so the precondition is a no-op
for them.

At wrap-up (the same lifecycle point where the unit would prompt for a Git commit),
run this self-reflection step. It is agent self-reflection — **never** solicit feedback
content from the user.

1. **Gate on qualification & completion.** Only proceed if this run reached wrap-up and
   did substantial work. Skip entirely for trivial/no-op runs. If the run was aborted or
   failed before wrap-up, follow the *Abort / partial-run rule* below.
2. **Reflect (no user input).** Review the just-completed run against this unit's declared
   purpose/description. Produce a short prose review plus **≥1 concrete, unit-specific
   optimization point**. If the run was clean, record exactly one line:
   `No significant optimization points identified this run.`
   **Token 效率自评**(纪律定义见 `.specify/shared/guidelines/token-efficiency.md`)——同步自查三问:本次运行是否发生 (1) **原文转储**(机器管理数据文件整体注入上下文)、(2) LLM **代做确定性工作**(固定规则判断未交程序)、(3) **重复读取**同一内容?有发现 → 对应优化点条目行 MUST 内嵌字面量 `token-efficiency`(稳定标记,供 `--action list --contains token-efficiency` 检索聚合);干净运行 MUST NOT 追加空洞的 Token 观察条目。量化口径:定性描述或行/字节代理指标,精确 Token 计数不可得时 MUST **不编造**具体数值。
3. **Scope guard.** Keep strictly to *this* unit's operation. Do NOT produce a
   global/whole-project assessment — that is `/speckit.review`'s job. Every entry is
   `scope: local`.
4. **Dedup guard.** Choose a stable `run_id` for this run (e.g. the feature key + a run
   timestamp). If a parent flow already recorded feedback for this same `(unit_id, run_id)`,
   the engine will no-op — do not force a duplicate.
5. **Persist** via the engine:

   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "<skill:NAME | /speckit.COMMAND>" --unit-type "<skill|command>" \
     --run-id "<stable-run-id>" --feature "<requirement-key-if-any>" \
     [--feature-id "<Feature-registry-ID-if-any>"] \
     --review "<review prose>" --points-file "<points file>"
   ```

   Probe attribution: the engine resolves the unit to its probe object automatically — the entry inherits kind/slice from the probe registry. External custom units record via `--unit-id custom:<owner>/<name> --unit-type custom-unit`; their entries stay host-project-local and never enter upstream packages.
   Identifier discipline: `--feature` carries the **requirement key** (e.g.
   `038-goal-target`); `--feature-id` carries the **Feature registry ID** (e.g.
   `041`). Different number spaces — never overload one field with both.
6. **Consolidated submission prompt.** Read `should_prompt` from the `record` output
   (or run `--action status`). When it is `true`, surface a **single** consolidated
   non-blocking notification (非阻塞) inviting the user to run the `/speckit.feedback` command — the user-facing path; never paste the raw
   `feedback-utils.py` engine call into the user-facing line. `/speckit.feedback` is
   the single entry point that reads the store, judges where the accumulated feedback
   points, and routes itself — so the notification MUST NOT pre-announce a disposition
   that judgment has not made. In particular, in the **framework project** (this repo
   *is* the upstream, so every entry points at this project and is digested in place)
   the notification MUST NOT recommend packaging: a zip produced there would be
   addressed to the repo that produced it. The wrap-up MUST NOT pause for the choice
   and MUST NOT trigger any automated transmission (自动传输); silence = skip. Below
   threshold, do NOT prompt. The three choices and their semantics: § *Threshold prompt
   protocol* below.

**Abort / partial-run rule.** If the run failed or was interrupted before wrap-up, either
skip recording OR record with `--partial` and a `## Review` that begins with
`**Partial run** — `. Never present a partial run as a complete review.

**Nesting rule.** When a command invokes a skill (or a skill invokes a skill), each
qualifying unit records feedback for **its own** scope only, keyed by its own
`(unit_id, run_id)`. The same unit+run MUST NOT be recorded twice.

---

## Embedded reference forms

Two forms, one per surface class. Copy the matching block verbatim into the embedding
unit and substitute only the unit id (`/speckit.<command>` for a command template,
`skill:<name>` for a skill). Nothing else is per-surface: no rule, threshold, engine
flag or red line is restated in an embedded section, because a copy is what drifts.

**Command templates** — complex commands only (the four simple commands carry no
`## Feedback` section at all). Place it next to `## Optional: Git Commit`, never
mid-flow:

```markdown
## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.COMMAND" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
```

**Skills** (`skills/*/SKILL.md` and `templates/skills-template.md`) — the runtime-mode
gate is part of this form, because skills are also deployed standalone outside any
Spec Kit project. The section is the last workflow section of `SKILL.md`:

```markdown
## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:NAME" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
```

---

## Threshold prompt protocol (canonical semantics for step 6)

When `should_prompt` is `true`, append **one non-blocking notification** to the wrap-up
report offering exactly three choices — the wrap-up MUST NOT pause waiting for the
user's choice; the choice is honored whenever the user responds (same turn or later),
and silence counts as **Skip this time** (the notification reappears only after more
entries accumulate). It MUST NOT trigger any automated transmission.
Present the choices in user-facing terms: the notification references the
`/speckit.feedback` command, never the raw `feedback-utils.py` engine path.
(Embedded copies that still say only "invite the user to submit" defer to the comprehension
discipline named in the header pointer, which owns this wording rule; this section keeps only
its class-③ instance):

1. **Let the command judge** — the user-facing path is `/speckit.feedback` with no
   argument: the command reads the store, determines which hat this repo wears, and
   routes the accumulated feedback itself. In a **client project** the entries that
   point outward reach its package path, which is where a zip for manual delivery comes
   from; in the **framework project** every entry points at this repo and is digested in
   place, so a package is produced only when the user asks for one explicitly
   (`/speckit.feedback package`). When a package is what this run is to produce, the
   engine call is:

   ```bash
   python3 .specify/scripts/python/feedback-utils.py --action package
   ```

   The engine zips all pending entries into `.specify/memory/feedback/packages/`
   (**source files untouched**, no network access), and prints the zip path, the
   detected upstream repo (user-configured `upstream_repo` > PEP 610 install metadata
   `direct_url.json` — the custom spec-kit's GitHub/GitLab origin), and manual send
   guidance (GitHub: issue attachment; GitLab: issue attachment or MR to the feedback
   intake directory). **The agent never sends the zip itself.** After the user confirms
   the batch is dealt with (sent — or deliberately discarded), run
   `--action mark-submitted [--notes "<disposition summary>"]`: the engine
   archives the pending batch into `packages/` (with the optional disposition
   record as `SUBMISSION-NOTES.md` inside the zip) and then resets the local
   counter — every reset therefore leaves an auditable package artifact behind.
2. **Skip this time** — do nothing; the prompt will naturally reappear only after more
   entries accumulate.
3. **Stop prompting** — the agent raises the threshold (`--threshold <N>` or
   `SPECKIT_FEEDBACK_THRESHOLD`); feedback keeps recording but stops prompting.

If the upstream repo cannot be detected, offer one-time setup instead of guessing: on
the user's confirmation, run
`python3 .specify/scripts/python/feedback-utils.py --action upstream --set <repo-url>`
(engine detail — do not paste the bare flag into the user-facing line).

## Workaround lookup (local value of the store)

When a command or skill misbehaves and a Spec Kit update is not yet available, check
whether earlier runs already hit — and worked around — the same issue:

```bash
python3 .specify/scripts/python/feedback-utils.py --action list --unit-id "<skill:NAME | /speckit.COMMAND>"
```

Entries' `## Review` / `## Optimization Points` often name the concrete obstacle and the
workaround applied. This is a read-only aid — it never gates execution.

---

## Notes for embedders

- **Which form**: command templates take the command form, `skills/*/SKILL.md` and
  `templates/skills-template.md` take the skill form (its runtime-mode gate is
  mandatory — detection semantics live in `.specify/shared/workflow/runtime-mode.md`).
- **Skills**: `--unit-id "skill:<name>"`, `--unit-type skill`.
- **Complex commands**: `--unit-id "/speckit.<command>"`, `--unit-type command`.
- **External custom units** (host-project skills/agents/commands with an injected `ext-*` probe): `--unit-id custom:<owner>/<name>`, `--unit-type custom-unit`. Entries stay host-project-local (never packaged upstream) — see `/speckit.feedback` § Probe Injection.
- **Simple commands** (`agents`, `constitution`, `feature`, `team`): omit this step entirely.
- The engine store lives at `.specify/memory/feedback/`; threshold defaults to `10`
  (`--threshold` / `SPECKIT_FEEDBACK_THRESHOLD`).
