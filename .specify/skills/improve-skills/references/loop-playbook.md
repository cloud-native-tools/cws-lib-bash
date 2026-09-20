# Improvement-Loop Playbook

Method detail for the `improve-skills` workflow. `SKILL.md` carries the contract — step
skeleton, hard rules, decision branches; this file carries the *how*, loaded on demand.

Anchors are referenced from `SKILL.md` by step number.

---

## Step 2 — Implementation research detail

调研发生在任何优化动作之前。目标不是"看一遍文件",而是建立足够的实现理解,让后续的
keep/change/drop 决策有据可依。

**读什么(全量,非抽样)**:

- `SKILL.md` 全文——frontmatter(description 触发面)、Goal、Input Contract、Workflow 每步、
  Hard Constraints、Resources 表;
- `references/` 每个文件——哪些被 SKILL.md 指针引用、哪些是孤儿;
- `scripts/` 每个脚本——`--help` 或注释头,确认声明的输入输出与 SKILL.md 的描述一致;
- `assets/`(如存在)——模板/样例是否仍被引用;
- 客观形状:`python3 ${SKILL_HOME}/scripts/skill-shape.py <SKILL.md>` 的判定与发现。

**从实现自身视角评估优缺点**(超越规范符合性):

- 承重机制——哪些步骤/规则真正防止了观察到的失败(保留并强化);
- 死重——哪些章节每次运行都被跳过、哪些规则从未触发过任何决策(精简候选);
- 决策泄漏——工作流在哪里把本该确定的判断推给了执行者自由发挥(结构化/脚本化候选);
- 伪装的确定性——哪些散文段落其实是确定性逻辑(提取为脚本的候选);
- 优化空间——结构(章节顺序/分层)、效率(可省略的读/写)、证据纪律(可机械化的检查)。

**调研笔记**(三步即可,写进运行工作区或报告):优点清单 / 缺点清单 / 优化空间清单。
每条缺点注明它伤害的是哪次真实执行或哪条用户要求——没有受害者的"缺点"是审美偏好,不是优化项。

**反模式**:只对照规范清单打勾、把"看起来不规整"当成缺陷、在未读 references/scripts 的情况下
断言优化空间——这三种都是 conformance theater,产出的编辑没有决策基础。

---

## Step 3 — Evidence collection detail

### Degenerate-evidence fallback

When collected findings are effectively identical project-level output for every target
(byte-identical digests across skills — no per-skill signal), do **not** fabricate per-skill
defects from them. Restrict the candidate list to:

- the standing sanctioned checks (Feedback-section conformance, legacy path idioms), plus
- **filesystem ground truth** — dead links, missing referenced scripts/files.

State the evidence limitation explicitly in the final report.

### Supplementary evidence from the execution window

Gather: user feedback, steps that were confusing, tool failures, wrong assumptions, repeated
manual fixes, validation gaps, and files changed during the execution. Include terminal/test
output and error messages when they explain what went wrong. Review changed files as
evidence, but classify generated validation artifacts (e.g. `tools/*.json`) separately from
hand-edited Skill instructions.

### What to measure against the optimization goal

Whether the Skill could be invoked; whether its expected input format was accepted; whether
the workflow produced the expected output; how many avoidable manual/tool steps occurred;
whether validation caught the issue. Then name the execution-flow steps that missed:
broken command-line parameters, mismatched formats, missing prerequisites, ambiguous target
resolution, inefficient tool choices, repeated searches, unnecessary user handoffs.

Separate facts from interpretation. Do not optimize from generic best-practice principles
when no execution evidence supports the change.

### Runtime failures outrank any prior "it works" claim

A reference/example snippet that throws or silently no-ops at runtime (missing module, a loop
that toggles its own state, an extractor that skips iframes) is a **confirmed defect** even if
the file exists and a previous run asserted the Skill was fine. Anchor the fix to the observed
stack trace / wrong output, not to the earlier assertion; a stale "already works" is itself a
finding to correct.

### Silent under-extraction is a defect, not just a throw

When an executor reports a helper "ran fine" but returned *empty or thin* results (a select
with no options, a dashboard with "0 panels", `variables: []` on a page that visibly has
them), that is evidence the helper read the wrong or too-early DOM — not evidence the page is
empty. Capture the concrete observation (which selector matched 0 nodes, which content was
missing) as the reusable fact; it is often more actionable than an error message precisely
because nothing crashed. Record it even when headline metrics (coverage, screenshots) look
green.

---

## Step 4 — Analysis detail

### Fact-check gates before writing capability/data claims

Recurring defects came from authoring claims without ground truth. Run the matching gate:

- **Delegation capability** — when adding a capability to a Skill that delegates to another
  skill/tool, verify the delegate's real capability surface first (its docs / `--help` /
  contract), and encode honest limitation branches where the capability is absent. Never
  design a delegation path that must fail.
- **Data tables** — when adding or maintaining a data table (endpoints, service info,
  inventories), extract values from an existing cached fact source (meta caches, registries,
  `--help` output). Never write values from memory.
- **Tier/coverage tables** — when grading or tabulating capability coverage, reconcile the
  requested list against the tool's actual coverage (run real `--help` / command probes) and
  explicitly mark entries that are graded but not implemented. A coverage table that
  overstates capability is worse than an incomplete one.

### Deferred items must name their unlocking evidence

When an item must be deferred for lack of execution evidence (the no-fabrication discipline
blocks writing it this loop), record **which concrete evidence would unlock it** — which
scenario run, command output, or artifact would make it writable — so a later run can collect
it deliberately instead of leaving a generic "to be filled" backlog entry.

Discard one-off environment noise unless the Skill should explicitly handle it next run. A
refresh command that exits successfully with a fallback after an optional-source warning is a
validation note, not a root cause.

### Cross-skill ownership boundary

When two sibling skills own overlapping artifact types with no documented boundary (e.g.
capacity templates vs responsibility templates), the root cause is the **undocumented
boundary itself**, not any single failing step. The fix usually includes writing the boundary
down in both skills.

### Misuse-vs-pitfall reflection gate

Many observations recorded as "pitfalls" are not tool pitfalls at all — the executor chose a
wrong method from the start, and the tool behaved exactly as designed. Recording expected
behavior as a pitfall pollutes the learning store (memory records, agent-guide Known-Pitfalls
sections, skill references) with noise that encodes misuse as tool blame.

**Run this gate before labeling an observation a pitfall, and before writing any
pitfall/lesson into memory, an agent guide, or a reference:**

1. Is the observed behavior described anywhere as the tool's intended/documented behavior
   (`--help`, official docs, the tool's own contract)?
2. Did a different supported method exist that would have produced the desired result
   directly — i.e. was the problem the *method choice*, not the tool?
3. Would the same "problem" recur for any competent user of the chosen method?

- **Yes to 1–2** → this is **expected behavior under misuse**, not a pitfall. Do NOT record
  it as a pitfall. Instead fix the *method-selection instructions*: add an explicit decision
  branch mapping each intent to the correct method (which tool/flag/entry point to use for
  which goal). Optionally record a one-line *misuse guard* ("X is not for Y; use Z") — never
  a pitfall entry describing the expected behavior as surprising.
- **No** → a genuine pitfall: undocumented, surprising, or version-drifting behavior. Record
  it with symptom, scope, and workaround as usual.

**Worked case** (doc-workspace tooling): an agent inserted structured content via
`block insert --text`, observed that newlines/lists/headings were flattened, and recorded it
as a new pitfall entry plus a memory record. Wrong framing — `--text` is designed to hold one
plain text block; flattening is its expected behavior. The correct method existed from the
start: headings via `--heading --level`, one block per list item, or a whole-document write
via `doc create/update --content-file` (the only path that parses Markdown into
heading/table/list blocks). The fix is a method-selection decision branch (intent → correct
entry point), not a pitfall entry.

### Legacy path idioms

Flag these as migration candidates and apply this Migration Mapping table:

| Legacy idiom | Rewrite as |
|--------------|-----------|
| Bare relative paths (`./scripts/init.sh`, `./references/checklist.md`) | `${SKILL_HOME}/...` |
| `${SKILL_ROOT}/X` | `${SKILL_HOME}/X` |
| Agent-specific install paths in prose (`${HOME}/.copilot/skills/<name>/...`, hard-coded `.specify/skills/<name>/...`) | `${SKILL_HOME}/...` |

### Feedback-section conformance

Verify the Skill carries a `## Feedback` section as its final workflow section, beginning with
the **runtime-mode gate** (`.specify/shared/workflow/runtime-mode.md`), and that the rest of
the section is the **skill reference form** owned by
`.specify/shared/workflow/feedback-step.md` § *Embedded reference forms* — a pointer plus
this Skill's unit id, never a copy of the rules.

- **Missing** → append the skill reference form from
  `.specify/shared/workflow/feedback-step.md` § *Embedded reference forms*, substituting
  only `skill:<name>`.
- **Malformed** → realign to that form. Malformed means any of: missing runtime-mode gate,
  missing pointer to `feedback-step.md`, wrong or missing `--unit-id "skill:<name>"` /
  `--unit-type skill`, or a section that **restates** the owner's rules (the reflection
  steps, submission-prompt semantics, abort/partial rule, nesting rule, token-efficiency
  self-assessment) instead of pointing at them. A restatement is drift in waiting: repair it
  by deleting the copy and leaving the pointer, never by re-wording the copy to agree.
- Apply the fix to **both** `skills/<name>/SKILL.md` and `.specify/skills/<name>/SKILL.md`.
- **Standalone-mode exception** — for a Skill in a standalone (non–Spec Kit) skills directory
  (no `.specify/` at the working-directory root) the engine-backed section is NOT required: a
  self-contained gated reflection section is conformant, the dual-copy rule does not apply,
  and no registry/agent propagation repair should be attempted.

---

## Step 5 — Codify deterministic logic; reserve natural language for judgment

Governing pattern: *deterministic logic → code, judgment logic → LLM.*

**Identify deterministic fragments.** Path derivation, sequence/number incrementing, state
detection, format/input validation, condition-branch decision trees, input/output transforms,
topological ordering, framework/version detection, prerequisite checks, structured parsing —
all have one correct result for a given input.

**Preset catalog + deterministic matcher.** When a skill repeatedly re-derives a whole
artifact shape (team roster, config skeleton, document layout) from vague free-form input, the
fix is a catalog of vetted presets plus a deterministic matcher mapping input signals to a
preset — not a longer prose decision tree. Presets must be distilled from real, evidenced
instances, and the matcher must be executed against sample inputs before wiring.

**Extract into a self-describing script.** Move the fragment into a shell or python script
under `${SKILL_HOME}/scripts/`. It must accept structured input (CLI arguments or a stdin JSON
payload), return structured output (JSON on stdout or an explicit exit code), and be
self-documenting (a `--help` flag, or a comment header stating purpose, inputs, outputs).

**Reference the script from `SKILL.md`.** Replace the prose describing the logic with a
script-invocation instruction — "run `${SKILL_HOME}/scripts/detect-framework.sh` and branch on
its JSON output" — instead of restating the steps in words.

**Keep judgment logic in natural language.** Option trade-offs, quality review, intent
understanding, and ambiguity resolution stay as LLM-directed prose.

**Apply only when it pays off.** Extract when the logic meets *any* complexity signal:
conditional branching, multi-step sequential operations with intermediate state, parsing or
transformation of structured data, or error-prone when restated in natural language (regex,
path arithmetic, version comparisons). Line count alone does not indicate complexity — a
one-line regex validation may warrant extraction while ten lines of straightforward
enumeration may not. The logic should also recur across executions or across Skills; truly
one-off trivial checks can stay inline.

---

## Step 6 — User-requirement pass detail

用户传入的优化描述在规范优化**之后**获得独立的应用通过。这一步骤的存在理由是决策顺序:
规范默认(精简偏好、结构习惯、风格约定)是从大量运行中蒸馏的*先验*,而用户要求是对
*本次*意图的直接陈述——冲突时先验让位。

**两级冲突分类**:

- **默认级冲突**(用户要求 vs 内置优化默认)——用户要求胜出,直接实施。
  例:用户要求"保留这段详细示例",而精简原则倾向移出 → 保留;用户要求"增加一个步骤",
  而结构习惯倾向合并 → 增加。
- **规范级冲突**(用户要求 vs 规范性义务)——不得静默服从,也不得静默拒绝。规范性义务包括:
  本技能的 Hard Constraints、目标技能的契约测试强制节(如 C-002 的 Agent-Specific
  Configuration 标题)、证据/红线纪律(Unobserved 不得生成缺陷等)、shape 门禁。
  处置:向用户显式指出冲突点,给出**最接近的合规实现**(如"步骤可以增,但细节须落
  references/ 以守住门禁"),由用户裁决。

**执行纪律**:

- 逐条核对用户要求:已满足(指出现状证据)/ 本次实施(指出编辑)/ 冲突(指出规范点与建议)。
  不允许"整体看起来做了"而遗漏单条要求。
- 用户要求的优先级是**决策顺序**,不是验证豁免:用户通过的编辑同样过步骤 8 的
  shape 门禁、契约测试与压测。
- 用户要求与证据冲突时(如用户基于过时印象要求修复已不存在的问题):陈述当前事实,
  按用户意图的*目标*而非字面措辞实施,并在报告中说明偏差。

---

## Step 7 — Rename/removal downstream-wiring checklist

When an improvement renames, consolidates, or removes a skill, the edit is not done until
every downstream pointer moves with it. In this repo:

1. Add the old name to `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`, extending the
   rename-chain comment.
2. Rename/realign the skill's contract-test file and its assertions, including guards that the
   old name is gone (directory absent, obsolete-manifest entry, no second directory carrying
   the same frontmatter `name`).
3. Update the skills-count list in the instructions file's Key Directories section (no
   registry row exists — discovery is by directory).
4. Add a feature-history entry recording the rename and rationale.
5. Fix stale pointers in artifacts the old skill dogfooded (e.g. report headers naming the
   predecessor skill).

Sync the `skills/<name>/` ↔ `.specify/skills/<name>/` mirror with `\cp -rf` (plain `cp` may be
aliased to `cp -i` and silently skip overwrites) and verify byte-equivalence with `diff -rq`.

**Move-then-edit order**: when a rename uses `git mv`, re-read the file at its NEW path before
editing — file-editing tools reject writes to paths not yet read in-session, so edits aimed at
the old path land nowhere.

---

## Step 8 — Zero-regression proof on a red suite

When the test suite has pre-existing failures, "the same tests still fail" eyeballed from
counts is not sufficient. Prove zero regression with a **failure-set diff**:

1. Capture the sorted `FAILED|ERROR` lines of the full run.
2. Produce a clean baseline of `HEAD` and rerun the same suite there.
3. Diff the two failure sets — an identical set means your change introduced no regression.

Prefer `git worktree add <tmp> HEAD` for the clean baseline: it is read-only with respect to
the working tree and immune to concurrent writers (a running continuous team writing into
`.specify/teams/` mid-run can block `git stash pop` and strand a stash entry). Use
`git stash -u` + rerun + `git stash pop` only when worktrees are unavailable.

If a combined validation command returns only partial output or omits later checks, rerun the
missing checks individually before concluding validation passed.

**Metadata validation detail**: when `skill_id` is added or corrected, ensure the directory
name and frontmatter `name` agree and no other skill directory carries the same `name`
(there is no registration table — see `.specify/skills.md`).

### Recorded exception (shape gate)

Hard Constraint 3 owns the rule; this is the mechanics. `skill-shape.py` exits `10` when a
body is over the L1 budget or trips a blocking shape rule. Finishing a loop on a red gate is
legitimate under exactly two cases:

- **Contract-mandated inline section** — a feature spec or contract test requires a section to
  stay inline in `SKILL.md` (grep `.specify/specs/**` and `tests/contract/**` before claiming
  this case), and keeping it inline pushes the controllable body past budget. The report names
  the mandating file.
- **Pre-existing over-budget baseline** — the step-2 gate run already exited `10` before this
  loop's first edit, and delete-and-absorb within this loop's scope cannot clear the debt. A
  loop that touches one line of an over-budget file need not repay the whole debt — but it
  must not add to it.

Both cases require the numbers: `est_tokens_controllable` from the step-2 baseline run and the
step-8 final run, plus the delta (`--json` exposes the exact field; the estimate is built to be
stable enough for this comparison — see the script's docstring). A positive delta on an
already-over-budget file fails the exception unless the added tokens are themselves the
mandated content or the same loop delete-and-absorbs an offsetting amount: quantifying the
growth is the price of finishing red. The exception lives in the step-9 loop report — a reason
stated only in conversation or a commit message was never recorded.

---

## Input Contract — batch mode detail

### Running a batch (explicit multi-skill request)

When the user explicitly names a *set* of Skills (or a whole skills directory), do not force
single-target resolution and do not loop the full workflow N times blindly. Run one batch pass:

1. Collect evidence **once** for the batch, then derive per-skill candidates.
2. **Freeze the per-skill candidate list** before editing — no mid-batch additions.
3. Prefer **mechanical, sanctioned conformance edits applied directly** (Feedback-section
   conformance, legacy path idioms, dead links, missing script refs) over speculative per-skill
   rewrites.
4. Verify mirror/write-through **once at the end** for the whole batch (e.g. `diff -rq`).

A batch that repeatedly fails on speculative rewrites should be restarted in this minimal-edit
shape rather than retried harder.

### Batch triage ownership

A unit naming a Skill absent from *this* repo is not automatically out of scope. First resolve
where the Skill actually lives — host skills dirs (`~/.qoder/skills/`), sibling project roots'
`.specify/skills/`, hardlink/write-through copies — and process it *there* when the user owns
that location (e.g. the framework developer handling cross-project feedback). Only mark a unit
out of scope after its install location is unknown or owned elsewhere.

### Intent routing guard

When the intent is to **monitor or evaluate an ongoing execution process** ("continuously
watch/score another agent's work") rather than to modify a specific Skill, this skill is the
wrong entry point: editing a SKILL.md conflicts with monitoring red lines (zero writes to the
monitored target). Route to a `continuous` monitoring team (`create-team` / `improve-team`) and
tell the user why, instead of forcing target-Skill resolution.
