---
description: 反馈统一入口：按指向自动分流为就地消化或打包上送
---
<!-- AUTO-GENERATED from templates/commands/feedback.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions. If empty, run the **Routing flow** below — the command inspects what has accumulated, judges where each item points, and picks the path itself, so no arguments and no keywords are needed. A non-empty argument MAY name a path explicitly (`package` / `打包` short-circuits to Path B), MAY carry an inventory filter (`--slice` / `--kind` / `--disposition` / `--since`), or MAY name a custom unit for probe injection. If the intent is ambiguous or unsupported, report the two paths and request the missing intent (do NOT guess silently).

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

`/speckit.feedback` is the **single entry point** for every operation on the local feedback store. It does not ask the caller to select a mode by keyword: it reads the store, judges where each item points, and routes itself to exactly one of **two execution paths**.

**The hat decides first, `kind` decides second.** "Points at this project" is not a property of an entry — it is a relation between the entry and the repo you are standing in. In the framework repo, this project *is* the upstream, so every entry points at it and there is nowhere to send a zip; in a client project, entries about framework units point outward and entries about the project's own custom units point inward.

| 本仓戴哪顶帽子 | 条目 | 路径 |
|---|---|---|
| **框架项目**(本仓即 Spec Kit 源) | 全部本地条目,不论 `kind` —— 上游就是本项目 | **Path A — 就地消化** |
| **框架项目** | `feedback/` 入站目录里客户项目送来的反馈包 | **Path A — 就地消化** |
| **客户项目** | `kind: external`(本项目自定义单元,`slice: host-custom`) | **Path A — 就地消化** |
| **客户项目** | `kind: internal`(框架单元) | **Path B — 打包上送** |
| 任意 | 为某个自定义单元**注入新探针** | *(超出自动分流)* — a target unit id cannot be inferred from repo state; see § Probe Injection |

**In the framework repo, Path B is reachable only by an explicit `package` request.** Packaging there produces a zip addressed to this same repository, which nobody can deliver to anybody — so the router never selects it on its own, and the threshold prompt MUST NOT recommend it.

**Routing flow**:

1. **Recognize intent** from `$ARGUMENTS` **and repo state**: an explicit `package` / `打包` request short-circuits to Path B and skips steps 2–5 (in the framework repo this is the only way to reach Path B); an explicit custom-unit injection request goes to § Probe Injection; otherwise continue and let the hat and the inventory decide.
2. **Determine which hat this repo wears — this is the primary discriminator, not a gate on one sub-step.** Framework project iff the repository root owns the canonical framework **source** directories: `templates`, `skills`, `shared`, `scripts` and `src/specify_cli` (enumeration owned by [`.specify/shared/definitions/dogfooding-definitions.md`](../../.specify/shared/definitions/dogfooding-definitions.md) § 2.1). Test the directories at the **root** — a client project has these only under `.specify/`, which is the runtime mirror, not the source. **Do NOT gate on `feedback/` directory existence**: a client project could have one for unrelated purposes. Write those directory names **without a trailing slash** when stating this criterion: `regen-command-copies.py` calls `rewrite_paths`, which prefixes any path-initial `templates`, `shared`, `scripts` or `memory` segment with the runtime-mirror directory — correct for a doc path a reader opens, but it would silently turn this test into one that every client project passes.
3. **Inventory** (this is where the probe overview lives — a step the judgment needs, not a destination of its own):

   ```bash
   python3 .specify/scripts/python/feedback-utils.py --action probes
   python3 .specify/scripts/python/feedback-utils.py --action probes --validate     # schema check
   python3 .specify/scripts/python/feedback-utils.py --action probes --reconcile   # embed audit
   python3 .specify/scripts/python/feedback-utils.py --action map                  # OPTIONAL (writes): rebuild probe-map.md
   python3 .specify/scripts/python/feedback-utils.py --action status
   python3 .specify/scripts/python/feedback-utils.py --action list --disposition open --format json
   ls feedback/feedback-*.zip 2>/dev/null                                          # framework hat only
   ```

   Render the merged probe truth source (framework Classes/Objects + project external probes) as a tree: kind → class (with target slice, collection, processing) → objects (unit @ lifecycle point). Mark internal vs external. The overview MUST be rendered from the truth source — never a hand-maintained list. Empty external section: show the `external-custom` class with its zero-object marker, no error. With `--format json` the list action emits `{"count": N, "matches": [...]}` where each match carries `id`, `file`, `unit_id`, `unit_type`, `run_id`, `probe`, `kind`, `slice`, `disposition`, `introspection_ref`, `partial`, `created`, `summary`, `path` — parse that shape, never a bare array.
4. **Classify by where each item points, hat first.** In the **framework project**, every entry in the local store points at this project regardless of its `kind`, and every inbound bundle in `feedback/` does too — all of it is Path A material, and Path B is not selected. In a **client project**, the stored `kind` field is the discriminator; the engine resolves it from the probe registry at record time and already enforces it at three layers, so the router reads a fact rather than forming an opinion: `kind: external` (`slice: host-custom`, recorded against a `custom:<owner>/<name>` unit) points at this project → Path A; `kind: internal` points at the framework upstream → Path B.
5. **Refine by content, in one direction only** (client projects only — in the framework project there is no outward side to refine toward). Run § Introspection over the open `internal` entries: a finding whose root cause turns out to be *this* project's own configuration or usage routes `local-sink` even though its `kind` is `internal`. The refinement is **one-directional**, because the engine's report validation rejects any `upstream-bound` finding that contains a `kind: external` member (exit 2) — so content analysis may move an internal entry toward this project, but can never move an external entry upstream. Report the classification, including any entry whose route the analysis moved. In the framework project, § Introspection still runs, but its output feeds **A4's channel routing** (which improvement channel owns each finding), not a side selection that has already been settled by the hat.
6. **Path A — 就地消化** for everything that points at this project: in the framework project that is the whole store plus any inbound bundles; in a client project it is the `kind: external` entries plus any `internal` entry step 5 moved.
7. **Path B — 打包上送** for everything that points at the framework upstream — a client project's `kind: internal` entries, or an explicit `package` request in either hat.
8. **Both sides non-empty** (possible only in a client project) → run Path A then Path B in the same session and report both. Never silently drop one side to keep the run short.
9. **Nothing in scope** (zero open entries and, in the framework hat, zero pending bundles) → report the empty inventory and stop normally. Do NOT write an empty report file.
10. **Undecidable** — the inventory is non-empty but an item's target genuinely cannot be determined → report the two paths and ask **one** elicitation question; do not guess silently, and once answered proceed directly without a further blocking prompt.

### Path A — 就地消化 (Digest In This Project)

Everything the feedback points at this project. In the **framework project** that is the entire store — every entry, whatever its `kind`, because this repo is the upstream — plus any inbound bundles in the `feedback/` intake directory. In a **client project** it is the `kind: external` entries plus any `internal` entry the step-5 refinement moved.

#### A1 — Enumerate pending bundles (framework hat only)

```bash
ls feedback/feedback-*.zip 2>/dev/null
```

- Zero bundles → say so and continue to A3 for the local entries; this is not an error and does not end the path.
- N bundles → list them (filename + size) and proceed. **Batch discipline**: process ALL bundles as ONE consolidated batch, never one zip at a time — reconciling claims across bundles surfaces factual conflicts between reporters and yields one mechanism fitting every environment.
- **Already-consumed cross-check (before any processing)**: read `.specify/memory/feedback/consume-log.md` and match every pending bundle against its `Bundles` column. A filename already logged was consumed once — it is a **re-delivered copy**, not new input: name it as such in the report, do NOT re-route its entries by default (that row already records their routing), and re-process it only on the user's own instruction in this run. Skipping this check silently re-consumes a batch that was deleted after a previous run and later landed in the intake again.
- A client project (no framework hat) skips A1 and A2 entirely and starts at A3.

#### A2 — Extract and read entries

For small batches (≤3 bundles, ≤20 entries total), read inline:

```bash
unzip -p <zip> MANIFEST.md       # manifest first
unzip -p <zip> <entry-filename>.md  # then each entry
```

For larger batches, extract to a temp directory first (faster, avoids repeated unzip overhead):

```bash
tmpdir=$(mktemp -d)
for z in feedback/feedback-*.zip; do unzip -o -d "$tmpdir/$(basename $z .zip)" "$z"; done
# then read files with standard file-reading tools
```

**Large-batch read discipline** (Token 效率纪律 applies — never inject all entry bodies into one context): group the entries by affinity (same unit / same slice / same feature chain), dispatch balanced **parallel read-only verifiers** (one Agent per group) that each read their entries in full, verify every optimization point against current framework source, and return a compact verdict table (point → STILL-VALID / ALREADY-FIXED / PARTIAL / NOT-OURS + evidence `path:line` + suggested routing). The reconciling agent reads the tables, never the raw bodies wholesale.

Collect from every entry: `unit_id`, `probe`, `slice`, `run_id`, `## Review`, `## Optimization Points`. Build a **cross-bundle findings table**: unit × finding × source-bundle. Clean up the temp dir after reading. 包内可能附 `introspection/<report-id>.md` 自省报告(条目经源头场景化核验):此类发现可直接采信其核验结论与证据锚点,把精力集中在跨包对账与冲突裁决上,无需重复事实核验。

**Bundle identity from the MANIFEST** — take `- **Install source**: <url> @ <sha>` and `- **Generated**: <ts>` for every bundle, plus its entry-file set from the archive listing (`unzip -l <zip>`). This is what catches a re-delivery the A1 filename check cannot (same batch, different filename):

- Equal install sha + generated ts, or an equal entry-file set, across two bundles → they are **copies of one batch**: count those entries once, process one copy, and state which copy was processed.
- Install sha / generated ts matching a batch already in `consume-log.md` under a different filename → a **second copy of a consumed batch**: handle under the A1 re-delivered rule, never as new input.
- No second copy anywhere — the zip is untracked and `git log --all --oneline -- feedback/<zip>` returns nothing → an **orphan**: its contents are unrecoverable once A5 removes it. Carry the orphan mark into the report.

#### A3 — Introspection(自省)

在记录与上行之间做**场景化深加工**:回到真实场景核验条目事实、聚类同根因问题、产出自省报告并分流(本地下沉 / 随包上行)。动机:消费方拿到的裸事实脱离了条目诞生的真实场景,容易产出错位方案;自省把深度思考移回项目现场。任意项目可运行本步,不受 A1 的框架项目门限制。

1. **范围快照**:`python3 .specify/scripts/python/feedback-utils.py --action list --disposition open --format json`(可按 `--slice/--kind/--since` 收窄)取条目摘要投影;零条目 → 报告"无可自省条目"并正常结束,不落空报告文件。
2. **场景化分析**(agent 推理;适用 Token 效率纪律:程序优先、摘要优先、升级阶梯,禁止整库原文注入):逐条目调出被评单元的当前定义/源码与条目引用的上下文,给出带证据的核验结论(成立/部分成立/已过时/不成立);把同根因的条目聚类为**问题**;每个问题含齐五要素——问题陈述、根因、证据锚点(指向具体单元/文件/位置)、分流决定(`local-sink(<channel>)` 或 `upstream-bound(package-attachment)`)、具体优化方案。
3. **报告产出**:按报告 schema 落盘 draft 报告到 `.specify/memory/feedback/introspection/<report-id>.md`(`report-id` 形如 `introspection-<YYYYmmddTHHMMSSZ>`;frontmatter 七字段 + `## Findings` + `## Excluded`),然后运行 `--action introspect-register --report-file <path>` 完成结构校验与条目关联;校验失败(exit 2)会逐条列出违规,修正后重跑。**按条目分区,不按点分区**:一个条目只归属一个问题,范围条目须被「问题成员 ∪ Excluded」恰好覆盖一次;条目含多个点时择其主根因归属,次要根因写进该问题的「具体优化方案」并标注。该约束的判据是引擎 `--action introspect-register` 的 V-1 语义校验输出(exit 2 逐条列出违规),以引擎为准——本文不复制引擎内部规则,写报告前不必先读引擎源码。
4. **用户确认**:呈现报告摘要(问题清单 + 每个问题的分流决定与建议处置);用户可逐问题覆盖分流方向——覆盖写回报告该问题的 `**用户覆盖**`(原决定 → 覆盖后决定)并同步 `**分流决定**`/`**建议处置**` 行后再确认。确认后运行 `--action introspect-register --report-file <path> --confirm`:报告置 `confirmed`,`**建议处置**` 行逐条生效(等价于逐条 `--action dispose --id <entry-id> --to <state> --reason "introspection:<report-id>#F-nn" --ref <report-id>#F-nn`);报告无 `建议处置` 行时仅翻转报告状态,不动条目。
5. **路由建议**:列出分流结果的建议去向——本地下沉项给出建议通道(直接修复 / improve-skills / improve-docs / 新需求),随包上行项提示下次打包可附报告(见 Path B 第 4 步);**仅建议,不自动执行任何动作**。

红线与边界:

- 本步 MUST NOT 自动修改代码/配置、MUST NOT 触发任何网络行为或自动传输;所有落地动作(直接修复、improve-* 运行、打包与人工送达)均经既有通道由用户确认后执行。
- 外部 probe 条目(`kind: external`)参与自省时分流恒为 `local-sink`,永不进入上行候选——该约束由引擎的报告校验强制执行,不是本文的劝告。
- 自省执行期间新写入的条目不进入本次范围(以发起时刻快照为准);条目引用物已失时标注"已过时/无法复现"而非中断;对同一批条目重复自省时,新报告声明 `supersedes` 承继旧报告,不平行重复造问题。

#### A4 — Reconcile and route findings

Cross-bundle reconciliation (the reason for A1's batch discipline):

- **Conflicting claims**: two reporters assert different facts about the same unit → surface the conflict explicitly, pick the one verified against source code, note the rejection.
- **Recurring findings**: the same optimization point appears in ≥2 bundles → elevate priority (systemic friction, not one-off).

Route each finding to the channel that owns it:

| Finding type | Route to | Example |
|-------------|----------|---------|
| Small, obvious fix | Direct fix (in this run) | Typo, stale count, broken link |
| New feature / capability | `/speckit.requirements` | New command, new engine action |
| Skill/agent improvement | `improve-skills` / `improve-agent` / `improve-team` | Workflow refinement, template fix |
| Tool record correction | `improve-tools` | Wrong contract, missing alias |
| Documentation gap | `improve-docs` or direct edit | Stale doc, broken link |
| Acknowledge only | Record in the report | Already fixed, duplicate, WONTFIX |

Produce a **digest report** for the user: findings table, routing decisions, conflicts found, proposed cleanup list, and the A1/A2 identity marks per bundle (re-delivered copy / second copy / orphan).

#### A5 — Cleanup (mandatory closing step of the digest run)

The user confirms the **routing decisions** in the digest report — confirmation of the report, NOT completion of every downstream routed run (findings routed to later `improve-*` / `/speckit.requirements` runs carry their input from the report and the log row below). On that confirmation, cleanup runs before the command ends:

```bash
rm feedback/feedback-<ts>.zip   # each processed bundle in this batch
```

- Delete ONLY the bundles that were in this batch; cleanup is atomic and **part of the run** — a digest run does not end with its intake files still on disk. The durable record is the consume-log row (routings + conflicts), never the zips: lingering bundles would form a second, staler source of truth.
- **Named marks, never a silent uniform delete**: every bundle carrying an A1/A2 identity mark (*re-delivered copy*, *second copy*, *orphan*) is listed by name **with that mark** in the report's cleanup section, so the confirmation already given for this batch knowingly covers a deletion that has no second copy behind it. An orphan the report did not name is not deleted.
- **Orphan preserve-first precondition**: before deleting ANY orphan-marked bundle, copy it to the standard preserve path `${TMPDIR:-/tmp}/speckit-feedback-preserve/<zip-name>` (a grace copy for the current session — `${TMPDIR}` is ephemeral across reboots; anyone needing longer retention moves it and records the final location). An orphan whose preserve copy failed is not deleted. The consume-log Cleanup column MUST record the preserve path for every orphan.
- Record the event by appending one row to `.specify/memory/feedback/consume-log.md`:

  ```markdown
  | 2026-08-15 | feedback-<ts1>.zip, feedback-<ts2>.zip | 23 | 5 direct fix, 3 improve-skills, 1 requirement | 1 (conflicting tool count) | 2 zips removed |
  ```

  Columns: `| Date | Bundles | Entries | Findings Routed | Conflicts | Cleanup |`

- The `feedback/` directory itself remains (it is the permanent intake point).

#### A6 — Dispose local entries

For entries this project digested without an inbound bundle (`kind: external`, or an `internal` entry A3 routed `local-sink`):

```bash
python3 .specify/scripts/python/feedback-utils.py --action dispose --id <entry-id> --to processed|ignored
```

Local metadata only; optional `--reason` / `--ref` record provenance (e.g. `introspection:<report-id>#F-nn`).

#### Path A behavior rules

- **Read-only toward bundles until cleanup**: never modify zip contents; extraction is read-only (`unzip -p` to stdout).
- **One batch, one cleanup**: do not delete individual bundles mid-batch; cleanup is atomic, runs once at the end of the digest run (once the routing report is confirmed), and leaves the intake empty.
- **No network**: digestion is entirely local file I/O + agent reasoning.
- **Fix at the owning hat**: in the framework project, findings are acted on in the framework **source** — the root-level `templates`, `skills`, `scripts`, `shared` and `src` directories — never in the `.specify/` runtime mirror (two-hats rule: Constitution XI). Those directory names are written without a trailing slash on purpose; see Routing flow step 2. In a client project, findings about a custom unit are acted on in that unit's own files.

### Path B — 打包上送 (Package For The Framework Upstream)

Everything the feedback points at the framework upstream. This is the sending side, and it never sends anything itself — delivery stays manual.

**Reached automatically only from a client project.** In the framework project the router does not select this path, because there is no upstream to deliver to — a zip packaged here is addressed to this same repository. It stays reachable there by an explicit `package` request (for example to hand a bundle to another maintainer, or to reset the counter via `mark-submitted`), and the run says plainly that it was taken on request rather than by judgment.

1. **Status view**: `--action status` (count / threshold / should_prompt)。若因阈值提示进入本命令:Path A 的 § Introspection 可先跑一遍再打包——建议而非强制,跳过不影响任何后续步骤。
2. **Summary view**: `--action list --limit 0` with filters as requested — `--slice <commands|skills|host-custom|...>`, `--kind <internal|external>`, `--disposition <processed|ignored|open>`, plus the pre-existing `--unit-id/--since/--contains`. Parse the `{"count": N, "matches": [...]}` envelope documented in the Routing flow's inventory step, never a bare array.
3. **Disposition**: `--action dispose --id <entry-id> --to processed|ignored` (local metadata only; optional `--reason`/`--ref` record provenance, e.g. from an introspection report).
4. **Package** (on the user's go-ahead, internal entries only): `--action package` → print zip path + manual-send guidance. The agent NEVER sends the zip. 若待打包条目带有 `introspection_ref`(已被自省覆盖),默认提议改用 `--action package --include-introspection` 把覆盖它们的自省报告一并入包;用户可拒绝,拒绝不阻断打包。外部条目(`kind: external`)由引擎自动排除并只回报 `excluded_external` 计数——它们属 Path A,永不随包上行。
5. **Post-package cleanup (default closing step of the package run)**: once the zip exists, the packaged batch no longer needs to live in the active store — the zip is the record. Preview with `--action cleanup --package <zip|latest> --dry-run`, then run without `--dry-run` in the same session as packaging. Cleanup removes only entries actually inside that zip; `cleanup-log.md` records every removal. The zip itself STAYS under `.specify/memory/feedback/packages/` as the delivery artifact.
6. **After delivery (`mark-submitted`)**: once the batch is dealt with (sent, or deliberately ignored) and `mark-submitted` has reset the counter, the zip has served its purpose — remove it from the outbox: `rm .specify/memory/feedback/packages/feedback-<ts>.zip`. The store, the outbox, and the counter all return to zero; `cleanup-log.md` plus the (already-delivered) zip's MANIFEST remain the audit trail.

If upstream cannot be detected, the engine offers a one-time `--action upstream --set <repo-url>` (engine detail — do not paste the bare flag into the user-facing line).

### Probe Injection (explicit request only)

Outside the automatic router by design: injecting a probe needs a target unit id that cannot be inferred from repo state, so this capability runs only when the user names it. For **client-project** custom Skills/Agents/Commands (assets the framework's own probes never cover). Terminology — **客户项目 (Client Project)** / **框架项目 (Framework Project)** — is defined canonically in [`.specify/shared/definitions/dogfooding-definitions.md`](../../.specify/shared/definitions/dogfooding-definitions.md) §2 (one repo, two hats; the flow chain framework sources → publish → install → each client project's `.specify/`); this command says "client project" wherever older drafts said "host project":

1. Elicit the target unit (`custom:<owner>/<name>`), lifecycle point (default `wrap-up`), and a short collection-intent note (`--notes-file`).
2. Run `--action probe-inject --unit custom:<owner>/<name> --notes-file <file>` — writes `.specify/memory/feedback/probes/ext-<slug>.md`.
3. Verify the injection: the object appears in `--action probes` and after `--action map`.

External-probe feedback is **client-project-local** (the client project's own use→feedback→iterate loop): it feeds that project's own optimization, is separately filterable via `--kind external`, is routed by Path A, and is **never** included in upstream packages.

## Behavior Rules

- Zero network operations of any kind (red line); `mark-submitted` remains local bookkeeping.
- Path A operates on both stores — the local store `.specify/memory/feedback/` and the `feedback/` intake directory (read-only until A5's atomic cleanup). Path B operates only on the local store. Never edit store files by hand.
- Exit code 2 from the engine is a verdict — report it, do not argue around it.
- Probe truth source: `.specify/shared/definitions/probe-definitions.md` (+ project `probes/`); derived views (`probe-map.md`) are rebuilt, never hand-edited.
- **The routing judgment is reported, not assumed**: state which hat the repo wears and how that was determined, how many items landed on each side, whether Path B was selected by judgment or taken on an explicit request, and any entry whose route the content analysis moved away from its `kind`-based first cut.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.feedback" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Handoffs

**Before**: none (any Spec Kit project; requires the probe registry installed by `/speckit.instructions`).

**After**: Path A → this project's own improvement channels (`improve-skills` / `improve-agent` / `improve-tools` / `improve-docs`), routed `/speckit.requirements` calls for new-feature findings, and `consume-log.md` recording the batch disposition. Path B → `mark-submitted` if not yet run for the batch, then manual delivery of the zip by the user. § Probe Injection → the client project's own improvement loop, which consumes `list --kind external` findings.