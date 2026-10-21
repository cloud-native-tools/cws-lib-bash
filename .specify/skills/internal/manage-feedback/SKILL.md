---
name: manage-feedback
description: Single execution core for feedback-store operations — read the accumulated inventory, judge which hat the repo wears (framework project vs client project) and where each entry points, then route itself to exactly one of two paths: Path A digests entries in place (bundle consumption with re-delivery/orphan recognition, introspection, cross-bundle reconciliation, channel routing, atomic cleanup, local dispose) and Path B packages internal entries for manual upstream delivery (status, filtered summary, disposition, package, hat-aware cleanup, mark-submitted); probe injection for client-project custom units runs only on explicit request. Use this when the user mentions ["feedback", "反馈", "消化反馈", "就地消化", "打包上送", "package feedback", "反馈包", "feedback bundle", "自省", "introspection", "探针注入", "probe injection", "mark-submitted", "反馈积压", "feedback backlog", "consume-log", "feedback cleanup"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-feedback/SKILL.md>"
---

# manage-feedback

## Goal

Own the full execution logic of feedback operations: one invocation reads the local
feedback store, judges where each item points, and routes itself to exactly one of
**two execution paths** — **Path A 就地消化** (digest in this project) or
**Path B 打包上送** (package for the framework upstream) — plus the
explicitly-requested § Probe Injection capability. The owning command is
`/speckit.feedback`; it keeps the entry surface (arguments, User Input Protocol, and
its own wrap-up Feedback / Documentation / Handoffs steps) and delegates everything
below to this skill.

Canonical extraction source: `.specify/templates/commands/feedback.md` § Routing flow
(steps 1–10), § Path A (A1–A6 + behavior rules), § Path B (steps 1–6),
§ Probe Injection, and § Behavior Rules. The routing judgment lives in this SKILL.md;
the two execution paths and the probe capability live in `references/`. The engine
(`.specify/scripts/python/feedback-utils.py`) owns the mechanics — this skill owns
when, why, and how to call it.

## Input Contract

- **Intent**: any feedback operation on the local store. Empty arguments run the
  Routing flow below — no keywords needed. A non-empty argument MAY short-circuit to
  Path B (`package` / `打包`), MAY carry an inventory filter
  (`--slice` / `--kind` / `--disposition` / `--since`), or MAY name a custom unit for
  probe injection. If the intent is ambiguous or unsupported, report the two paths and
  request the missing intent — do NOT guess silently.
- **Precondition**: the probe registry installed by project initialization
  (`/speckit.instructions`); without it the engine has no probe truth source to read.
- **Glossary**: consult the project glossary (`.specify/memory/glossary.md`) and apply
  the protocol in `.specify/shared/workflow/glossary.md` before acting: correct
  recorded homophone/confusable variants; propose new terms at wrap-up with user
  confirmation.

## Workflow

`/speckit.feedback` is the **single entry point** for every operation on the local
feedback store. It does not ask the caller to select a mode by keyword: it reads the
store, judges where each item points, and routes itself.

**The hat decides first, `kind` decides second.** "Points at this project" is not a
property of an entry — it is a relation between the entry and the repo you are
standing in. In the framework repo, this project *is* the upstream, so every entry
points at it and there is nowhere to send a zip; in a client project, entries about
framework units point outward and entries about the project's own custom units point
inward.

| 本仓戴哪顶帽子 | 条目 | 路径 |
|---|---|---|
| **框架项目**(本仓即 Spec Kit 源) | 全部本地条目,不论 `kind` —— 上游就是本项目 | **Path A — 就地消化** |
| **框架项目** | `feedback/` 入站目录里客户项目送来的反馈包 | **Path A — 就地消化** |
| **客户项目** | `kind: external`(本项目自定义单元,`slice: host-custom`) | **Path A — 就地消化** |
| **客户项目** | `kind: internal`(框架单元) | **Path B — 打包上送** |
| 任意 | 为某个自定义单元**注入新探针** | *(超出自动分流)* — a target unit id cannot be inferred from repo state; see § Probe Injection |

**In the framework repo, Path B is reachable only by an explicit `package` request.**
Packaging there produces a zip addressed to this same repository, which nobody can
deliver to anybody — so the router never selects it on its own, and the threshold
prompt MUST NOT recommend it.

### Routing flow

1. **Recognize intent** from `$ARGUMENTS` **and repo state**: an explicit `package` /
   `打包` request short-circuits to Path B and skips steps 2–5 (in the framework repo
   this is the only way to reach Path B); an explicit custom-unit injection request
   goes to § Probe Injection; otherwise continue and let the hat and the inventory
   decide.
2. **Determine which hat this repo wears — this is the primary discriminator, not a
   gate on one sub-step.** Framework project iff the repository root owns the
   canonical framework **source** directories: `templates`, `skills`, `shared`,
   `scripts` and `src/specify_cli` (enumeration owned by
   `.specify/shared/definitions/dogfooding-definitions.md` § 2.1). Test the
   directories at the **root** — a client project has these only under `.specify/`,
   which is the runtime mirror, not the source. **Do NOT gate on `feedback/`
   directory existence**: a client project could have one for unrelated purposes.
   Write those directory names **without a trailing slash** when stating this
   criterion: `regen-command-copies.py` calls `rewrite_paths`, which prefixes any
   path-initial `templates`, `shared`, `scripts` or `memory` segment with the
   runtime-mirror directory — correct for a doc path a reader opens, but it would
   silently turn this test into one that every client project passes.
3. **Inventory** (this is where the probe overview lives — a step the judgment needs,
   not a destination of its own):

   ```bash
   python3 .specify/scripts/python/feedback-utils.py --action probes
   python3 .specify/scripts/python/feedback-utils.py --action probes --validate     # schema check
   python3 .specify/scripts/python/feedback-utils.py --action probes --reconcile   # embed audit
   python3 .specify/scripts/python/feedback-utils.py --action map                  # OPTIONAL (writes): rebuild probe-map.md
   python3 .specify/scripts/python/feedback-utils.py --action status
   python3 .specify/scripts/python/feedback-utils.py --action list --disposition open --format json
   ls feedback/feedback-*.zip 2>/dev/null                                          # framework hat only
   ```

   Render the merged probe truth source (framework Classes/Objects + project external
   probes) as a tree: kind → class (with target slice, collection, processing) →
   objects (unit @ lifecycle point). Mark internal vs external. The overview MUST be
   rendered from the truth source — never a hand-maintained list. Empty external
   section: show the `external-custom` class with its zero-object marker, no error.
   With `--format json` the list action emits `{"count": N, "matches": [...]}` where
   each match carries `id`, `file`, `unit_id`, `unit_type`, `run_id`, `probe`,
   `kind`, `slice`, `disposition`, `introspection_ref`, `partial`, `created`,
   `summary`, `path` — parse that shape, never a bare array.

   **Read the routing backlog** (`.specify/memory/feedback/backlog.md`) — the single
   carrier for findings prior consume runs routed but did not execute. Report how many
   rows are `open`, `open-unverified` and `carried-by-spec-*`. An `open-unverified` row
   is **not** a to-do: its underlying defect MUST be re-measured against current
   framework source before anyone acts on it, because most such rows were fixed by
   later work and acting on a stale point wastes a whole improvement cycle. A row
   still `open` across two or more consume runs is itself a finding — name it in the
   digest report.
4. **Classify by where each item points, hat first.** In the **framework project**,
   every entry in the local store points at this project regardless of its `kind`, and
   every inbound bundle in `feedback/` does too — all of it is Path A material, and
   Path B is not selected. In a **client project**, the stored `kind` field is the
   discriminator; the engine resolves it from the probe registry at record time and
   already enforces it at three layers, so the router reads a fact rather than forming
   an opinion: `kind: external` (`slice: host-custom`, recorded against a
   `custom:<owner>/<name>` unit) points at this project → Path A; `kind: internal`
   points at the framework upstream → Path B.
5. **Refine by content, in one direction only** (client projects only — in the
   framework project there is no outward side to refine toward). Run § Introspection
   (A3 in [`./references/path-a-digest.md`](./references/path-a-digest.md)) over the
   open `internal` entries: a finding whose root cause turns out to be *this*
   project's own configuration or usage routes `local-sink` even though its `kind` is
   `internal`. The refinement is **one-directional**, because the engine's report
   validation rejects any `upstream-bound` finding that contains a `kind: external`
   member (exit 2) — so content analysis may move an internal entry toward this
   project, but can never move an external entry upstream. Report the classification,
   including any entry whose route the analysis moved. In the framework project,
   § Introspection still runs, but its output feeds **A4's channel routing** (which
   improvement channel owns each finding), not a side selection that has already been
   settled by the hat.
6. **Path A — 就地消化** for everything that points at this project: in the framework
   project that is the whole store plus any inbound bundles; in a client project it is
   the `kind: external` entries plus any `internal` entry step 5 moved.
7. **Path B — 打包上送** for everything that points at the framework upstream — a
   client project's `kind: internal` entries, or an explicit `package` request in
   either hat.
8. **Both sides non-empty** (possible only in a client project) → run Path A then
   Path B in the same session and report both. Never silently drop one side to keep
   the run short.
9. **Nothing in scope** (zero open entries and, in the framework hat, zero pending
   bundles) → report the empty inventory and stop normally. Do NOT write an empty
   report file.
10. **Undecidable** — the inventory is non-empty but an item's target genuinely cannot
    be determined → report the two paths and ask **one** elicitation question; do not
    guess silently, and once answered proceed directly without a further blocking
    prompt.

### Path execution

- **Path A — 就地消化 (Digest In This Project)**: execute per
  [`./references/path-a-digest.md`](./references/path-a-digest.md) — A1 pending-bundle
  intake (re-delivery / interrupted-run / orphan recognition), A2 extraction and
  large-batch read discipline, A3 Introspection(自省), A4 reconcile and route, A5
  atomic cleanup with the consume-log row, A6 dispose local entries, and the Path A
  behavior rules.
- **Path B — 打包上送 (Package For The Framework Upstream)**: execute per
  [`./references/path-b-and-probe.md`](./references/path-b-and-probe.md) — status,
  filtered summary, disposition, packaging, hat-aware post-package cleanup,
  `mark-submitted` after delivery.
- **Probe Injection (explicit request only)**: per
  [`./references/path-b-and-probe.md`](./references/path-b-and-probe.md) § Probe
  Injection — outside the automatic router by design; runs only when the user names a
  target custom unit.

## Behavior Rules

- Zero network operations of any kind (red line); `mark-submitted` remains local
  bookkeeping.
- Path A operates on both stores — the local store `.specify/memory/feedback/` and the
  `feedback/` intake directory (read-only until A5's atomic cleanup). Path B operates
  only on the local store. Never edit store files by hand.
- Exit code 2 from the engine is a verdict — report it, do not argue around it.
- Probe truth source: `.specify/shared/definitions/probe-definitions.md` (+ project
  `probes/`); derived views (`probe-map.md`) are rebuilt, never hand-edited.
- **The routing judgment is reported, not assumed**: state which hat the repo wears
  and how that was determined, how many items landed on each side, whether Path B was
  selected by judgment or taken on an explicit request, and any entry whose route the
  content analysis moved away from its `kind`-based first cut.
- **Routed ≠ done**: `.specify/memory/feedback/backlog.md` is the single carrier for
  findings routed but not executed — read at inventory, written at A4, and a row
  closes only on evidence that its named owner file changed. The consume-log is a
  batch audit trail; it does not carry work forward.

## Boundaries

- **Recording new feedback entries** is not this skill — every unit's own wrap-up
  Feedback step persists entries via the engine's record action; this skill consumes,
  routes, disposes, and packages what is already recorded.
- **SDD-flow mechanisms are separate.** `/speckit.analyze` and `/speckit.review` take
  the current feature as input and stay inside the SDD flow; feedback targets the
  framework itself across units and runs. The normative boundary is
  `.specify/shared/workflow/feedback-step.md` § *Mechanism boundary* — do not merge the
  two, and do not describe review as a whole-framework report.
- **Command-lifecycle surfaces** (User Input Protocol, the command's own Feedback /
  Documentation / Handoffs wrap-up steps) stay with `/speckit.feedback`; this skill is
  the execution core it delegates to.
- **Engine mechanics** (flag validation, report schema checks, exit codes, excluded
  counts) belong to `feedback-utils.py`; when this skill and the engine disagree, the
  engine's verdict wins (exit 2 is a verdict).

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-feedback" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-feedback" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-feedback" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
