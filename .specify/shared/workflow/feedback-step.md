# Canonical Feedback Step

This file is the single source of truth for the feedback step that every qualifying
unit's compiled `## Wrap-up` section wires to (056: the section is rendered by
`probe-utils.py --action compile-embeds`, not hand-embedded). The compiled section is
the final workflow section of a skill; complex command templates carry it at their
wrap-up / Git-commit-prompt stage. Simple commands carry no wrap-up face at all — a
command is complex iff it invokes .specify/scripts/CLI tools, produces an artifact another flow
consumes, or consumes another flow's artifact.

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

### Mechanism boundary — SDD-flow mechanisms vs framework feedback

`/speckit.analyze` and `/speckit.review` **belong to the SDD flow** and take the current
feature as their input: analyze is the read-only pre-implementation artifact-consistency
gate, and review is the post-implementation critique of the SDD process that produced
that feature. Review's report is **feature-scoped** — its "global" reach is the whole SDD
process of that one feature, never a whole-framework assessment.

**Feedback is not an SDD stage.** It targets the Spec Kit framework itself (red line 1),
attaches to the wrap-up of any qualifying unit — SDD command or not — and accumulates
across runs and units. Each entry stays `scope: local` (one unit + one run); a
framework-wide view exists only as the **aggregation** the introspection step builds from
recorded entries, never as an independent, zero-input audit. In short: analyze/review ask
"how is this feature's SDD run going?"; feedback asks "what does this unit's real use say
about the framework?".

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
   failed before wrap-up, follow the *Abort / partial-run rule* below. Where a 运行判定
   record exists for this run, its `qualification` field **is** this gate's answer — read
   it instead of re-judging (§ *Run Determination* below).
2. **Reflect (no user input).** Review the just-completed run against this unit's declared
   purpose/description. Produce a short prose review plus **≥1 concrete, unit-specific
   optimization point**. Where a 运行判定 record exists, write both from its measured axes
   rather than from impression (§ *Run Determination* below). If the run was clean, record
   exactly one line:
   `No significant optimization points identified this run.`
   **Token 效率自评**(纪律定义见 `.specify/shared/guidelines/token-efficiency.md`)——同步自查三问:本次运行是否发生 (1) **原文转储**(机器管理数据文件整体注入上下文)、(2) LLM **代做确定性工作**(固定规则判断未交程序)、(3) **重复读取**同一内容?有发现 → 对应优化点条目行 MUST 内嵌字面量 `token-efficiency`(稳定标记,供 `--action list --contains token-efficiency` 检索聚合);干净运行 MUST NOT 追加空洞的 Token 观察条目。量化口径:定性描述或行/字节代理指标,精确 Token 计数不可得时 MUST **不编造**具体数值。
3. **Scope guard.** Keep strictly to *this* unit's operation. Every entry is
   `scope: local` (one unit + one run); a framework-wide view exists only as the
   aggregation the introspection step builds from recorded entries — never as an
   entry-level assessment, and never by restating another unit's findings. The
   mechanism boundary is owned by § *Mechanism boundary* above. A review recommendation
   that targets the framework is not left without an intake: its legal entry is the
   existing `/speckit.feedback` manage-feedback Path A digest § A3 自省(Introspection)
   step. No new intake store, tracking engine, or scoring system is introduced.
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
   protocol* below. Where a 运行判定 record exists for this run, its routing bit composes
   with `should_prompt` and both MUST be true before this notification is surfaced; absent
   a record for this `(unit_id, run_id)`, `should_prompt` alone governs exactly as before
   (§ *Run Determination* below).

**Abort / partial-run rule.** If the run failed or was interrupted before wrap-up, either
skip recording OR record with `--partial` and a `## Review` that begins with
`**Partial run** — `. Never present a partial run as a complete review.

**Nesting rule.** When a command invokes a skill (or a skill invokes a skill), each
qualifying unit records feedback for **its own** scope only, keyed by its own
`(unit_id, run_id)`. The same unit+run MUST NOT be recorded twice.

---

## Run Determination (canonical measured input for steps 1, 2 and 6)

This section is the landed owner of exactly four facts: where 运行判定 (Run Determination)
enters the Reflection procedure, how its routing bit composes with step 6, what the
passive path MUST NOT do, and where its record lands. It owns **no** value domain, no
reason set and no decision table — those are code's. Everything else below reaches its
owner by path.

**Engine and code-side owner.** `.specify/scripts/python/run-determination.py` (framework
source `.specify/scripts/python/run-determination.py`) owns the record schema, every value domain
the program branches on, the routing-bit derivation (`derive_trigger_feedback`) and the
CLI flag set. No invocation is written out here on purpose: the parser generates the
engine's own `--help`, so a flag list copied into prose could only drift. The record *is*
the 改点 — term owner `.specify/memory/glossary.md`. The four red lines and the
never-solicit rule at the top of this file govern everything below unchanged and are not
restated here.

**Consumption point — the step 1 → step 2 boundary.**

- **Step 1** runs the engine's `determine` action at wrap-up. Its `qualification` field is
  this gate's answer, so the gate becomes a lookup instead of a fresh judgment. Supplying
  the current turn's class on that same call is what settles the *previous* run's
  satisfaction axis: settlement rides the next wrap-up, so there is no second call site
  and no hook to install.
- **Step 2** writes its review and its optimization points from the record's measured axes
  instead of from impression, and its Token 三问 now cites a measured token axis rather
  than a guess. The three questions themselves are unchanged and stay owned by step 2.
- **Steps 3, 4 and 5** are unchanged. The record is not a feedback entry: it never enters
  the step-5 call, never reaches the counter and never influences `should_prompt`.

**Composition at step 6.** The routing bit `passive_trigger.trigger_feedback` and the
feedback engine's `should_prompt` compose; neither replaces the other. The property a
reader MUST NOT miss is its asymmetry: a **single** regressed comparison axis does not
fire the passive path — it is recorded, and the active improve flow picks it up later.
Only a run that broke something, that the user rejected, or that regressed on **both**
comparison axes at once reaches step 6's notification. Requiring the two booleans together
is what holds the noise floor where red line 2 needs it.

**Absent record — degrade, never fabricate.** When no record exists for this
`(unit_id, run_id)` (the engine did not run, or this unit is outside its scope), step 6
governs on `should_prompt` alone exactly as it did before, and the wrap-up says plainly
that the determination was not evaluated. An absent record is neither a clean run nor a
veto, and MUST NOT be reported as either. This is the house response to a missing sensor —
continue on available run evidence, never fabricate — per
`.specify/shared/workflow/self-improvement-workflow.md` § Failure and Degradation.

**Unresolved-red input — engine exit codes only.** The satisfaction axis's red-adjacency
exception has exactly one producer: a non-zero exit from an engine this run invoked,
reported through the exit-code table the `.specify/scripts/python/` engines share. The producer
formerly named beside it — an anomaly the agent surfaced and the user never answered
(`surfaced_anomaly_unanswered`) — is **dropped**, not deferred, and MUST NOT be declared.
The per-turn telemetry store `.specify/memory/trigger/telemetry.jsonl` MUST NOT be read
for this state: its row schema is a closed set owned by another feature and carries no key
able to express an unresolved red. Seam owner: `OI9_RED_STATE_INPUT` / `read_red_state()`.

**Where the record lands.** Through the existing memory engine
(`.specify/scripts/python/memory-utils.py`) into the `session` scope, tagged
`run-determination`; the determination engine's own `history` action is the read side and
returns a projection, never record bodies. No new store, no new directory, no second
database beside SI-7's ledger. That memory engine's enforced `--source` contract accepts
the command and skill forms of `unit_id` and nothing else, so a `custom:<owner>/<name>`
unit has **no** accepted source form. The engine therefore fails closed — record emitted,
`persisted: false`, reason stated — and MUST NOT invent a source string to make the write
succeed; widening that contract is its owner's act, not this flow's. Seam owner:
`OI2_PERSISTENCE_ADAPTER` / `PERSISTENCE_ADAPTERS`.

**Passive non-exhaustiveness.** The passive path MUST NOT be exhaustive, because acting on
everything it can see would disturb the very run it is measuring. In scope for this turn:
a finding whose unit is this unit and whose axis was actually evaluated in this run —
those, and only those, feed the routing bit. Everything else is recorded in the same
record's `out_of_scope[]`, one bounded line each, with **no carrier assigned**
(`parked_via: none`); assigning one belongs to the **active** improve flow, which chooses
between two carriers that already exist — `/speckit.todo` Park Mode (the default: a
free-floating improvement idea; mode, store path and frontmatter owned by
`.specify/templates/commands/todo.md`) and a new spec through `/speckit.requirements` (when the
finding constrains what this project's source must implement, which is the Requirement
plane's call, not this flow's). The passive turn names carriers; it MUST NOT open either
flow, widen the current turn, or emit anything beyond the single non-blocking notification
step 6 already owns.

**改点 is a sensor, not a ledger.** The record carries no disposition, no threshold and no
mutation authority, and it is never written under `.specify/memory/feedback/`. It feeds
SI-7's `intervention.json`, which stays in the baseline evidence run directory keyed by its
own fields; the join is one-way, and the record never replaces or duplicates that ledger.
Boundary and flow position: `.specify/shared/workflow/self-improvement-workflow.md` SI-1,
SI-7, SI-8.

**Never solicited.** The passive path **infers**. It classifies a user turn that already
happened, from context the agent already holds, and only that closed classification ever
crosses into the engine — never raw user text. No question is put to the user, no prompt is
added and no new user-facing surface class appears. That is why this wiring stays on the
inference side of the never-solicit rule above.

---

## Embedded reference forms

The embedded wrap-up section is **compiled, not hand-embedded** (056): `probe-utils.py
--action compile-embeds` renders each unit's single AUTO-GENERATED `## Wrap-up` from the
registry (`.specify/shared/definitions/probe-definitions.md` ## Handler / ## HandlerBinding) and
migrates away any manual `## Feedback` / `## Documentation` section it finds. They do
not copy it — each call line points here; the agent executing the section follows its
lines in order, which lands on this file's own sections. Nothing is per-surface beyond
the interpolated unit id: no rule, threshold, engine flag or red line is restated in an
embedded section, because a copy is what drifts.

Command and skill faces share one shape — kind-derived call lines in ascending handler
order; skill faces additionally carry the runtime-mode gate (skills are also deployed
standalone outside any Spec Kit project), command faces never do. The shape with
placeholders:

```markdown
## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source:
     .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding)
     — fingerprint: <fp> — do not edit; edit the registry, then recompile -->

1. <Label> — `python3 .specify/scripts/python/<engine>.py --action <action>
   --unit-id "<unit-id>" --unit-type <command|skill>`
2. <Label> — `.specify/shared/workflow/feedback-step.md` § "<action>"

**Runtime-mode gate.** … (skill faces only) …
```

Hand-editing a compiled section is forbidden — edit the registry, then recompile; the
banner fingerprint makes drift detectable (`compile-embeds --check` exits 1 on any
unit whose section no longer matches the registry).

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
  `.specify/templates/skills-template.md` take the skill form (its runtime-mode gate is
  mandatory — detection semantics live in `.specify/shared/workflow/runtime-mode.md`).
- **Skills**: `--unit-id "skill:<name>"`, `--unit-type skill`.
- **Complex commands**: `--unit-id "/speckit.<command>"`, `--unit-type command`.
- **External custom units** (host-project skills/agents/commands with an injected `ext-*` probe): `--unit-id custom:<owner>/<name>`, `--unit-type custom-unit`. Entries stay host-project-local (never packaged upstream) — see `/speckit.feedback` § Probe Injection.
- **Simple commands** (`agents`, `constitution`, `feature`): omit this step entirely. This list is *derived* from the complexity criterion at the top of this file — when a command gains or loses script invocations, or starts or stops producing or consuming another flow's artifact, re-derive the list rather than editing it alone.
- The engine store lives at `.specify/memory/feedback/`; threshold defaults to `10`
  (`--threshold` / `SPECKIT_FEEDBACK_THRESHOLD`).
