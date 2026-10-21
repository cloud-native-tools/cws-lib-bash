# Path A — 就地消化 (Digest In This Project)

Owns § Path A (A1–A6 + behavior rules) of the feedback skill. Extracted from
`.specify/templates/commands/feedback.md`; content preserved, form re-expressed. The routing
judgment that selects this path lives in the skill's SKILL.md (Routing flow).

Everything the feedback points at this project. In the **framework project** that is
the entire store — every entry, whatever its `kind`, because this repo is the
upstream — plus any inbound bundles in the `feedback/` intake directory. In a
**client project** it is the `kind: external` entries plus any `internal` entry the
step-5 refinement moved.

## A1 — Enumerate pending bundles (framework hat only)

```bash
ls feedback/feedback-*.zip 2>/dev/null
```

- Zero bundles → say so and continue to A3 for the local entries; this is not an error
  and does not end the path.
- N bundles → list them (filename + size) and proceed. **Batch discipline**: process
  ALL bundles as ONE consolidated batch, never one zip at a time — reconciling claims
  across bundles surfaces factual conflicts between reporters and yields one mechanism
  fitting every environment.
- **Already-consumed cross-check (before any processing)**: read
  `.specify/memory/feedback/consume-log.md` and match every pending bundle against its
  `Bundles` column. A filename already logged was consumed once — it is a
  **re-delivered copy**, not new input: name it as such in the report, do NOT re-route
  its entries by default (that row already records their routing), and re-process it
  only on the user's own instruction in this run. Skipping this check silently
  re-consumes a batch that was deleted after a previous run and later landed in the
  intake again.
- **Interrupted-run recognition (the mirror case of the cross-check above)**: a bundle
  in the intake with **no** matching `Bundles` row is not automatically new input
  either — it is equally what an interrupted Path A run leaves behind, because the
  consume-log row is that run's only persistent marker and A5 writes it **last**. Put
  such a bundle to the user as **one** question — is this a **已确认待清理** resumption
  of an earlier run, or genuinely new input? — and do NOT re-route it as new input by
  default. Record the answer in that batch's consume-log row so the next run reads a
  fact instead of facing the same ambiguity. A resumption picks A5 back up (its
  bundles were already confirmed and are awaiting removal); new input continues from
  A2.
- A client project (no framework hat) skips A1 and A2 entirely and starts at A3.

## A2 — Extract and read entries

For small batches (≤3 bundles, ≤20 entries total), read inline:

```bash
unzip -p <zip> MANIFEST.md       # manifest first
unzip -p <zip> <entry-filename>.md  # then each entry
```

For larger batches, extract to a temp directory first (faster, avoids repeated unzip
overhead):

```bash
tmpdir=$(mktemp -d)
for z in feedback/feedback-*.zip; do unzip -o -d "$tmpdir/$(basename $z .zip)" "$z"; done
# then read files with standard file-reading tools
```

**Large-batch read discipline** (Token 效率纪律 applies — never inject all entry
bodies into one context): group the entries by affinity (same unit / same slice /
same feature chain), dispatch balanced **parallel read-only verifiers** (one Agent per
group) that each read their entries in full, verify every optimization point against
current framework source, and return a compact verdict table (point → STILL-VALID /
ALREADY-FIXED / PARTIAL / NOT-OURS + evidence `path:line` + suggested routing). The
reconciling agent reads the tables, never the raw bodies wholesale.

Collect from every entry: `unit_id`, `probe`, `slice`, `run_id`, `## Review`,
`## Optimization Points`. Build a **cross-bundle findings table**: unit × finding ×
source-bundle. Clean up the temp dir after reading. 包内可能附
`introspection/<report-id>.md` 自省报告(条目经源头场景化核验):此类发现可直接采信其核验
结论与证据锚点,把精力集中在跨包对账与冲突裁决上,无需重复事实核验。

**Bundle identity from the MANIFEST** — take `- **Install source**: <url> @ <sha>` and
`- **Generated**: <ts>` for every bundle, plus its entry-file set from the archive
listing (`unzip -l <zip>`). This is what catches a re-delivery the A1 filename check
cannot (same batch, different filename):

- Equal install sha + generated ts, or an equal entry-file set, across two bundles →
  they are **copies of one batch**: count those entries once, process one copy, and
  state which copy was processed.
- Install sha / generated ts matching a batch already in `consume-log.md` under a
  different filename → a **second copy of a consumed batch**: handle under the A1
  re-delivered rule, never as new input.
- No second copy anywhere — the zip is untracked and
  `git log --all --oneline -- feedback/<zip>` returns nothing → an **orphan**: its
  contents are unrecoverable once A5 removes it. Carry the orphan mark into the
  report.

## A3 — Introspection(自省)

在记录与上行之间做**场景化深加工**:回到真实场景核验条目事实、聚类同根因问题、产出
自省报告并分流(本地下沉 / 随包上行)。动机:消费方拿到的裸事实脱离了条目诞生的真实
场景,容易产出错位方案;自省把深度思考移回项目现场。任意项目可运行本步,不受 A1 的框架
项目门限制。

1. **范围快照**:`python3 .specify/scripts/python/feedback-utils.py --action list --disposition open --format json`(可按 `--slice/--kind/--since` 收窄)取条目摘要投影;零条目 → 报告"无可自省条目"并正常结束,不落空报告文件。
2. **场景化分析**(agent 推理;适用 Token 效率纪律:程序优先、摘要优先、升级阶梯,禁止整库原文注入):逐条目调出被评单元的当前定义/源码与条目引用的上下文,给出带证据的核验结论(成立/部分成立/已过时/不成立);把同根因的条目聚类为**问题**;每个问题含齐五要素——问题陈述、根因、证据锚点(指向具体单元/文件/位置)、分流决定(`local-sink(<channel>)` 或 `upstream-bound(package-attachment)`)、具体优化方案。
3. **报告产出**:按报告 schema 落盘 draft 报告到 `.specify/memory/feedback/introspection/<report-id>.md`(`report-id` 形如 `introspection-<YYYYmmddTHHMMSSZ>`;frontmatter 七字段 + `## Findings` + `## Excluded`),然后运行 `--action introspect-register --report-file <path>` 完成结构校验与条目关联;校验失败(exit 2)会逐条列出违规,修正后重跑。**按条目分区,不按点分区**:一个条目只归属一个问题,范围条目须被「问题成员 ∪ Excluded」恰好覆盖一次;条目含多个点时择其主根因归属,次要根因写进该问题的「具体优化方案」并标注。该约束的判据是引擎 `--action introspect-register` 的 V-1 语义校验输出(exit 2 逐条列出违规),以引擎为准——本文不复制引擎内部规则,写报告前不必先读引擎源码。
4. **用户确认**:呈现报告摘要(问题清单 + 每个问题的分流决定与建议处置);用户可逐问题覆盖分流方向——覆盖写回报告该问题的 `**用户覆盖**`(原决定 → 覆盖后决定)并同步 `**分流决定**`/`**建议处置**` 行后再确认。确认后运行 `--action introspect-register --report-file <path> --confirm`:报告置 `confirmed`,`**建议处置**` 行逐条生效(等价于逐条 `--action dispose --id <entry-id> --to <state> --reason "introspection:<report-id>#F-nn" --ref <report-id>#F-nn`);报告无 `建议处置` 行时仅翻转报告状态,不动条目。
5. **路由建议**:列出分流结果的建议去向——本地下沉项给出建议通道(直接修复 / improve-skills / improve-docs / 新需求),随包上行项提示下次打包可附报告(见 `./path-b-and-probe.md` 第 4 步);**仅建议,不自动执行任何动作**。

红线与边界:

- 本步 MUST NOT 自动修改代码/配置、MUST NOT 触发任何网络行为或自动传输;所有落地动作(直接修复、improve-* 运行、打包与人工送达)均经既有通道由用户确认后执行。
- 外部 probe 条目(`kind: external`)参与自省时分流恒为 `local-sink`,永不进入上行候选——该约束由引擎的报告校验强制执行,不是本文的劝告。
- 自省执行期间新写入的条目不进入本次范围(以发起时刻快照为准);条目引用物已失时标注"已过时/无法复现"而非中断;对同一批条目重复自省时,新报告声明 `supersedes` 承继旧报告,不平行重复造问题。

## A4 — Reconcile and route findings

Cross-bundle reconciliation (the reason for A1's batch discipline):

- **Conflicting claims**: two reporters assert different facts about the same unit →
  surface the conflict explicitly, pick the one verified against source code, note the
  rejection.
- **Recurring findings**: the same optimization point appears in ≥2 bundles → elevate
  priority (systemic friction, not one-off).

Route each finding to the channel that owns it:

| Finding type | Route to | Example |
|-------------|----------|---------|
| Small, obvious fix | Direct fix (in this run) | Typo, stale count, broken link |
| New feature / capability | `/speckit.requirements` | New command, new engine action |
| Skill/agent improvement | `improve-skills` / `improve-agent` / `improve-team` | Workflow refinement, template fix |
| Tool record correction | `improve-tools` | Wrong contract, missing alias |
| Documentation gap | `improve-docs` or direct edit | Stale doc, broken link |
| Acknowledge only | Record in the report | Already fixed, duplicate, WONTFIX |

Produce a **digest report** for the user: findings table, routing decisions, conflicts
found, proposed cleanup list, and the A1/A2 identity marks per bundle (re-delivered
copy / second copy / orphan).

**Write the backlog, not only the log**: every finding routed to a channel that is NOT
executed in this run MUST gain a row in `.specify/memory/feedback/backlog.md` (routed
date, source, finding, channel, owner file(s), status). The consume-log row records
where a finding was *sent*; the backlog records what is still *owed*. A routing that
lives only in the consume-log is a dead letter — that has already happened once here.
The recurrence test for closing a backlog row is that the **named owner file actually
changed** (a commit, or a measurement of the owner showing the defect gone), never
that the row exists.

## A5 — Cleanup (mandatory closing step of the digest run)

The user confirms the **routing decisions** in the digest report — confirmation of the
report, NOT completion of every downstream routed run (findings routed to later
`improve-*` / `/speckit.requirements` runs carry their input from the report and the
log row below). On that confirmation, cleanup runs before the command ends:

```bash
rm feedback/feedback-<ts>.zip   # each processed bundle in this batch
```

- **Uninterrupted sequence**: preserve (orphans) → remove the bundles → append the
  consume-log row MUST run as **one uninterrupted sequence**, with no other work
  inserted between its steps — not another finding, not a routed `improve-*` run, not
  a wrap-up step. The reason is structural, not stylistic: the log row is this batch's
  **only** persistent marker and it is the sequence's *last* step, so an interruption
  anywhere before it leaves removed bundles with no record that they were ever routed
  — which the next run cannot tell apart from a batch nobody processed. That
  indistinguishability is exactly what A1's interrupted-run recognition has to ask the
  user about, so an interruption here manufactures the ambiguity there.
- Delete ONLY the bundles that were in this batch; cleanup is atomic and **part of the
  run** — a digest run does not end with its intake files still on disk. The durable
  record is the consume-log row (routings + conflicts), never the zips: lingering
  bundles would form a second, staler source of truth.
- **Named marks, never a silent uniform delete**: every bundle carrying an A1/A2
  identity mark (*re-delivered copy*, *second copy*, *orphan*) is listed by name
  **with that mark** in the report's cleanup section, so the confirmation already
  given for this batch knowingly covers a deletion that has no second copy behind it.
  An orphan the report did not name is not deleted.
- **Orphan preserve-first precondition**: before deleting ANY orphan-marked bundle,
  copy it to the standard preserve path
  `${TMPDIR:-/tmp}/speckit-feedback-preserve/<zip-name>` (a grace copy for the current
  session — `${TMPDIR}` is ephemeral across reboots; anyone needing longer retention
  moves it and records the final location). An orphan whose preserve copy failed is
  not deleted. The consume-log Cleanup column MUST record the preserve path for every
  orphan.
- Record the event by appending one row to `.specify/memory/feedback/consume-log.md`:

  ```markdown
  | 2026-08-15 | feedback-<ts1>.zip, feedback-<ts2>.zip | 23 | 5 direct fix, 3 improve-skills, 1 requirement | 1 (conflicting tool count) | 2 zips removed |
  ```

  Columns: `| Date | Bundles | Entries | Findings Routed | Conflicts | Cleanup |`

- The `feedback/` directory itself remains (it is the permanent intake point).

## A6 — Dispose local entries

For entries this project digested without an inbound bundle (`kind: external`, or an
`internal` entry A3 routed `local-sink`):

```bash
python3 .specify/scripts/python/feedback-utils.py --action dispose --id <entry-id> --to processed|ignored
```

Local metadata only; optional `--reason` / `--ref` record provenance (e.g.
`introspection:<report-id>#F-nn`).

## Path A behavior rules

- **Read-only toward bundles until cleanup**: never modify zip contents; extraction is
  read-only (`unzip -p` to stdout).
- **One batch, one cleanup**: do not delete individual bundles mid-batch; cleanup is
  atomic, runs once at the end of the digest run (once the routing report is
  confirmed), and leaves the intake empty.
- **No network**: digestion is entirely local file I/O + agent reasoning.
- **Fix at the owning hat**: in the framework project, findings are acted on in the
  framework **source** — the root-level `templates`, `skills`, `scripts`, `shared`
  and `src` directories — never in the `.specify/` runtime mirror (two-hats rule:
  Constitution XI). Those directory names are written without a trailing slash on
  purpose; see the SKILL.md Routing flow step 2. In a client project, findings about a
  custom unit are acted on in that unit's own files.
