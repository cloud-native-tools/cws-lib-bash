<!-- AUTO-GENERATED from templates/commands/team.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). If empty, execute the **Default Behavior (No Arguments)** defined below. If non-empty but intent is ambiguous or unsupported, report capabilities and request the missing intent (do NOT guess silently).

## Outline

`/speckit.team` is the **single entry point** for every **team** operation — the multi-agent analogue of `/speckit.agents`. It recognizes intent, then routes to the owning team skill. It delegates to skills and does **NOT** render templates inline. It MUST NOT serve single-agent authoring (that is `/speckit.agents`), and single-agent commands MUST NOT serve team operations.

A **team** is a named, reusable multi-agent structure organized around a single **goal**. Every team has three parts: a **goal** (the team's overall final objective — the north star that all work serves), a **static structure** (Role × Stage × Type roster — *who* participates), and a **dynamic structure** (collaboration pattern — parallel / serial / iteration / continuous — with its parallelism/DAG/iteration/operating settings and execution flow — *how* they collaborate). The four patterns each encode a priority: **parallel** = 效率优先 (throughput), **serial** = 质量优先 (quality, verified handoffs), **iteration** = 目标收敛 (converge then stop), **continuous** = 长期运营 (operate on a cadence). The static and dynamic structures exist **only to achieve the goal**; whatever they are, they MUST be organized and run around it. Persistent teams own a directory at the canonical location `.specify/teams/<slug>/` (definition at `.specify/teams/<slug>/team.md`; run reports under `.specify/teams/<slug>/runs/`). The multi-agent Conceptual Model that underpins teams is defined once in `skills/create-team/references/conceptual-model.md`; the `continuous` operating discipline in `skills/create-team/references/operating-loops.md`.

### Goal — 团队的最终目标

Every team MUST have a **goal** set at creation and carried for its whole lifetime. The goal is the team's single overall final objective — the reason the team exists — and it governs both structures below.

- **North star, not a task list.** The goal states the desired end outcome, not the steps. The static structure (roster) and dynamic structure (pattern) are both *derived from* and *subordinate to* the goal: the goal decides which roles/stages are needed and which collaboration pattern fits. The Goal concept itself — project-level definition, criteria authority, singularity, and the `goal_slug` Goal–Team binding — is defined once in `.specify/shared/definitions/goal-definitions.md`.
- **Concrete and verifiable.** State the goal so progress toward it can be judged — ideally with explicit success criteria / quality dimensions and, where possible, a measurable target (e.g. a score threshold, a passing test suite, a coverage bar). The **evaluator** stage and the **iteration/continuous** `threshold` / quality dimensions measure progress *against the goal*; a goal that cannot be evaluated cannot drive a loop.
- **Distinct from `description`.** `description` is a one-line label; the **goal** is the operational objective the whole team is organized around. A team has exactly **one** goal (sub-objectives belong to member roles/stages).
- **Deliberately revisable, never drifting.** The goal stays fixed while a team runs and never changes as a *side effect* of restructuring — but it is not frozen. The **modify** mode can deliberately **redefine an existing team's goal**; when it does, the static and dynamic structures MUST be re-checked and realigned to serve the new goal.

When a goal's theme is **optimization**, `create-team` further classifies it (**one-time vs continuous**) and, for continuous optimization, selects a strategy (**elimination vs progressive**) — see `skills/create-team/references/optimization-goals.md`.

The goal is persisted as the `goal` frontmatter field and rendered as a `## Goal` section (see Persistence).

### Modes → Capability Routing

`/speckit.team` exposes **exactly three modes**:

| Mode | Recognized intent | Delegates to skill |
|------|-------------------|--------------------|
| **create** | "创建团队", "组织一个团队", "组建团队", "new team", "build a team" | `create-team` |
| **modify** | "修改团队", "调整团队", "优化 team", "improve/adjust team" | `improve-team` |
| **run** | "运行团队", "执行团队", "run/execute team", "跑一遍"(可选 `--target T-<nnn>` 指定目标切片) | `create-team` (execution path) |

**Routing flow**:

1. **Recognize intent** from `$ARGUMENTS` and conversation/repo context: classify as `create`, `modify`, or `run`.
2. **create** → `create-team`: **first establish the goal** — check the **Goal-Based Create branch** first (see below: exact-match the input token against archived goal slugs), otherwise elicit it from `$ARGUMENTS` / conversation / repo context as free text, or ask for it when missing — then **match the goal against the predefined team presets** (`skills/create-team/templates/teams/`, matched via `skills/create-team/scripts/match-team-preset.py`): on a strong match, recommend reusing that preset instead of deriving a team from scratch; otherwise propose a roster (static structure) + pattern config (dynamic structure) **derived from that goal**. **直接落盘** `.specify/teams/<slug>/team.md`(或按用户指示 run one-shot 不落盘)——可逆动作自动执行,落盘前 MUST NOT 设置阻塞式停等(判据:`.specify/shared/guidelines/confirmation-gates.md`);落盘后 MUST 呈现定义内容并给出修改途径(`/speckit.team` modify / `improve-team`),按执行报告约定收尾。
3. **modify** → `improve-team`: load the existing team and apply targeted, evidence-based edits to any of its three parts — the **goal**, the **static structure**, or the **dynamic structure**. Structure edits are structure-preserving and keep serving the current goal. **Redefining the goal is a first-class, supported edit**: when the goal changes, re-evaluate and realign the roster and pattern to serve the new goal. Re-persist and bump `updated`.
4. **run** → `create-team` execution path: follow the **preview → execute** sequence below.
5. **Empty arguments** → execute **Default Behavior (No Arguments)** below.
6. **Non-empty but ambiguous / unsupported** → report capabilities and request the missing intent (see "Ambiguous or Unsupported Intent" below).
7. **modify / run targeting a team that does not exist** under `.specify/teams/` → report **"team not found"** and offer to `create` it.

### Default Behavior (No Arguments)

When `$ARGUMENTS` is empty, the command MUST execute the following sequence instead of routing to a mode:

1. **List all existing teams** — scan `.specify/teams/*/team.md` and present a summary table with each team's `slug`, `name`, `goal`, and `pattern`. If no teams exist, state "No teams found" explicitly.
2. **Give contextual suggestions** — based on the current conversation, recent repo activity, and the listed teams, recommend the most relevant next action. Examples:
   - A team whose goal aligns with the current task → suggest `run <slug>`.
   - A team whose structure seems outdated relative to recent changes → suggest `modify <slug>`.
   - No teams exist or no team fits the current need → suggest `create` with a proposed goal derived from context.
   Suggestions MUST be grounded in observable context (conversation history, repo state, team definitions), NOT fabricated.
3. **Show capability summary** — briefly list the three modes (create / modify / run) so the user knows what operations are available.

This behavior is informational and non-destructive: it MUST NOT create, modify, or run any team without explicit user instruction.

### Ambiguous or Unsupported Intent

When intent cannot be resolved from non-empty arguments, the command MUST report the recognized capabilities and request the missing intent. It MUST NOT guess silently or fail without a message. Report this capability listing:

- **create** — establish the team's **goal**, then author a new team (static + dynamic structure) organized around it and persist it → `create-team`
- **modify** — adjust/optimize an existing team — reshape its structure, or **redefine its goal** and realign the structure to the new goal → `improve-team`
- **run** — restate the **goal**, render the team's structure, and execute it directly (preview is disclosure, not a gate) → `create-team`

### Goal-Based Create(基于已定义 Goal 的创建分支)

The create path first checks whether the user passed an **already-defined goal**: when a token in `$ARGUMENTS` matches an archived `<goal-slug>` under `.specify/goal/`, the flow enters the **goal-based branch** directly — recognition is deterministic and engine-driven (never guessed from memory), and the branch decision is disclosed in the run output rather than gated on confirmation.

1. **识别(确定性,零语义猜测)**:先运行 `python3 .specify/scripts/python/goal-utils.py list --json` 取得 archive slug 全集;入参 token 与某 slug **精确匹配**(或为指向其 `goal.md` 的路径)→ 报出"基于已定义 goal `<slug>` 创建"并**直接进入分支**(判定结果即时呈现,不设阻塞式停等)。匹配判定 MUST 由引擎枚举结果驱动,MUST NOT 由 agent 凭记忆或语义猜测断言;近似不匹配(大小写/连字符差异)**不构成命中**。无命中 → 走既有自由文本流程,行为与引入前一致(零回归)。
2. **加载与两类拒绝**:进入分支后经 `parse_goal`(`.specify/scripts/python/goal-utils.py`)读取 objective、criteria(含 `None provided.` 缺失态)、status、targets、history,并复述呈现给用户(非阻塞)。
   - **悬空引用**(用户指名但 `list` 无此 slug):输出以逐字前缀 `goal 未定义:` 开始的报错,指向 `/speckit.goal create`;零产物、零写入,MUST NOT 静默降级为内联 goal 创建。
   - **终态 goal**(`achieved`/`abandoned`):显式报出终态并拒绝创建团队。两类拒绝是停止而非写入,无需用户确认即可执行。
3. **四要素分析(建议非门禁)**:创建前呈现,每项附理由:
   1. **维度**——goal 对象所处平面(链接概念锚 `.specify/shared/definitions/goal-definitions.md` 的 Goal Dimensions,不复述);
   2. **判据覆盖**——criteria 逐条列出,或显式声明缺失(`None provided.`,MUST NOT 臆造);
   3. **既有 Target**——open/done/dropped 分类清单(复用基线,见下文"分解提议"小节的处置规则);
   4. **可达成性**——单团队短期可达成 vs 宽泛需分解,结论 + 依据。
   分析结论是建议而非门禁:单团队/分解路径由用户裁决;用户坚持单团队不被阻止,但裁决留痕于呈现与执行报告。
4. **分解提议与成组批准(分解路径)**——分析判定宽泛且用户裁决分解时:
   - **起草纪律**:每条候选为成果形语句(GD-2 切片尺度)、从属同一目标;自身独立成立的候选经 GD-3 litmus 引导**另立 goal**,退出提议集并在预览中说明;MUST NOT 复述该 goal 的成功判据或任何需求规格的 SC-xxx。提议集为**无序集**——呈现顺序不承载执行语义,落盘身份由引擎单调发放;MUST NOT 附依赖边、编号顺序或阶段化措辞。
   - **干跑校验**:每条候选在呈现前经 `python3 .specify/scripts/python/goal-utils.py targets <slug> --check "<候选语句>"` 干跑(零写入,校验器与 `--add` 同源);呈现给用户前每条 MUST 已通过(exit 0)——被拒条目改写重检或移出,MUST NOT 以 exit-2 状态进入批准呈现。
   - **呈现**:以 `分解提议` 小节一次性呈现全量——每条语句 + 单独理由 + `--check` verdict。
   - **批准与落盘**:一次**合并批准**(全量语句一次呈现 → 用户单次裁决,propose→ratify 决策语义不变)覆盖整组;随后**逐条**执行 `python3 .specify/scripts/python/goal-utils.py targets <slug> --add "<语句>"`。每条 verdict 即时尊重:exit 2 的拒绝被**原样上报** verdict 与原因,修订后重走 `--check` 再提交或被显式放弃;MUST NOT 绕过引擎、MUST NOT 手写或手改 `## Targets` 节。
   - **复用基线**:goal 已有 Target 时以既有集合为**复用基线**——open 条目直接复用(后续成组建队的对象),语义重复的语句 MUST NOT 被重复授权;done/dropped 条目保留展示、不复用身份、MUST NOT 被顺带重开(重开仅 `/speckit.goal targets --set open`,由人发起)。提议只补缺口或确认复用;提议集为空时直接进入成组建队。
   - **中途中止**:用户中止或某条落盘失败时,已落盘条目保留(它们是合法授权),其余丢弃;再次发起时既有 open Targets 自动成为复用基线,不重复授权。
5. **团队派生与落盘**:路径确定后派生团队——
   - 单团队路径:roster 与 pattern 以该 goal 叙事为输入走既有机制(`python3 skills/create-team/scripts/match-team-preset.py` preset 匹配 + `skills/create-team/references/patterns.md` 决策树),派生理由 MUST 进入执行前呈现;preset 强匹配时推荐复用该 preset。
   - **成组路径(N teams : 1 Goal)**:分解批准后(或复用基线成立时),**每个 open Target 对应创建一个团队**——全部声明**同一 `goal_slug`**;每个团队的 roster/pattern 以其 **Target 语句**为输入复用既有派生机制(`python3 skills/create-team/scripts/match-team-preset.py --goal "<Target 语句>"` + pattern 决策树),派生理由入执行前呈现;`focus_target: T-<nnn>` 指向该团队对应的切片(**插在 `goal_slug` 之后**;创建落盘前 MUST 校验其存在于绑定 goal 的 `## Targets` 且为 `open`,否则拒绝创建);团队 slug 缺省派生 `<goal-slug>-t<nnn>`(小写、三位零填充,如 `log-split-t003`),对 `.specify/teams/` 现存目录**查重**,冲突即自动改写并回显(用户事后可经 modify 改名,不阻塞落盘)。
   - **territory 纪律**:多团队方案 MUST 基于切片呈现两两不相交的 territory 提议,落盘前经 `python3 skills/create-team/scripts/verify-territory-disjoint.py --input <proposals.json> [--repo-root <root>] --json` 校验(提议团队 ∪ 同 `goal_slug` 既有团队;判定文法 import 自 `build-summary-input.py`,零第二文法):`exit 0` → 提议划分随各 team.md 落盘;`exit 4`(任何 overlap/undecidable)→ 披露争用区/未声明方,人工改划后重跑或移交 `/speckit.goal coordinate`,MUST NOT 静默落盘已知重叠的 territory;同 goal 下已有其他团队时,单团队路径同样必跑 verify。
   - **落盘前一次性披露(非阻塞)**:分支判定(命中的 goal-slug 与定义摘要)、分析结论、路径决策、提议集或复用声明、territory 划分提议(含 verify verdict)——披露即呈现,不设阻塞式停等;随后 team.md **直接落盘**,落盘后按执行报告约定呈现定义内容与修改途径(`/speckit.team` modify / `improve-team`)。同一 `goal_slug` 下已存在团队(扫描 `.specify/teams/*/team.md` frontmatter)时:MUST 检测并提议复用既有团队或移交 `/speckit.goal coordinate`,MUST NOT 无提示重复建队。
   - frontmatter 声明 `goal_slug`(引用,不是内容副本);内联 `goal` 字段(如保留)仅为可读性渲染,**定义权威**——与定义不一致时显式报出供人裁决,MUST NOT 分叉出第二份权威叙事。
   - 写入面仅限 `team.md`;本分支对 `goal.md` 零写入(`## Targets`/`## History` 只经 `/speckit.goal` 的引擎渲染)。

### Run Mode (preview → execute)

The **run** mode MUST follow this sequence; the preview is disclosure, and the team executes directly once presented (可逆动作自动执行,判据:`.specify/shared/guidelines/confirmation-gates.md`)。**continuous 模式例外**——持续循环类运行 MUST 保留 `skills/create-team/references/operating-loops.md` 与 `project-cluster.md` 的既有分级门控:

1. **Load** the target team from `.specify/teams/<slug>/team.md`.
2. **Resolve the effective Target, then run the five checks (preview validation).** `run <team-slug> [--target <T-<nnn> | <goal-slug>.T-<nnn>>]` — the local form `T-<nnn>` is canonical; the qualified form is accepted only when its `<goal-slug>` equals the bound goal. Resolution order is **显式 `--target` > team.md `focus_target` > 无**: an explicit `--target` always wins (semantics identical to 038); otherwise a declared `focus_target` (局部形 `T-<nnn>`,插在 frontmatter `goal_slug` 之后) is the team's default focus, resolved via `resolve_effective_target` (`.specify/scripts/python/goal-utils.py`) → `{effective, source, declared_focus}`. `focus_target` 是 run 级 `--target` 的**预填**——不是写域声明、不是 Goal–Team 绑定变更、不参与 goal 身份解析。`focus_target` 格式非法(`source=input-error`)→ 停止并经 improve-team 修正,不静默忽略、不降级为无;未声明且未显式指定(`source=none`)→ 全流程与引入前逐字节等价。The resolved `effective` value (when not None) is then validated by the five checks below — **the local form is canonical** and the checks themselves are UNCHANGED; the engine parse of `.specify/scripts/python/goal-utils.py` (`parse_goal` / `preview_target_check`) is the single source of truth for every judgment below — never re-derive it in prose:
   1. **解析绑定 goal**——沿用既有两级身份解析(`goal_slug` 显式 → 团队 slug 推断);本流程不引入第三级。团队无 goal 定义而指定了 `--target` → 报"Target 依赖 goal 定义",指向 `/speckit.goal migrate` 并停止;不指定 `--target` 时一切照旧。
   2. **悬空引用**——`T-<nnn>` 不存在于绑定 goal 的 `## Targets` 节 → 报为悬空并停止,提议先经 `/speckit.goal targets --add` 添加;不静默接受、不降级、不臆测。
   3. **终态引用**——Target 状态为 `done`/`dropped` → 显式报出终态并停止,附**复核二分**指引:属实 → 返回报告结束本次 run;证据不符 → 经 `/speckit.goal targets --set open --id <T-nnn>` 重开后重新发起。run 模式 **MUST NOT 提供终态执行旁路**,MUST NOT 默默当作 open 执行。
   4. **跨 goal 引用**——限定形前缀与绑定 goal 身份不一致 → 拒绝,指明绑定轴不可越界。
   5. **goal 自身终态**(`achieved`/`abandoned`)→ 拒绝指派,指明终态 goal 只读。
3. **Restate the Goal** — surface the team's `goal` up front, so both structures below are read as *means to that end* and execution can be judged against it.
4. **Render Static Structure** — the roster as a Role × Stage × Type matrix: each member agent, its role, its type (Worker/Meta), and its lifecycle (persistent/temporary).
5. **Render Dynamic Structure** —
   - the collaboration `pattern` (parallel / serial / iteration / continuous);
   - the **parallelism** (parallel: degree + territories; serial: DAG stage order + per-handoff verification; iteration: threshold, max_iterations, regression_limit, quality dimensions; continuous: maturity level, cadence, budget, constraints, independent verifier, state spine);
   - an **execution flow diagram** (textual / mermaid / PlantUML flow showing dispatch / handoff / loop edges).
6. **Present & execute** — present the **goal** and both structures, then execute directly; the presentation is disclosure, not a blocking gate(事后修改途径:`/speckit.team` modify / `improve-team`)。
   - **Disclose the summary decision** before execution, so its cost is known up front: whether this run will refresh the goal summary or not and — when it will not — which gate suppresses it (budget / cadence / no material); the resolved **goal identity** and whether it is explicit (`goal_slug` declared) or inferred (falling back to the team slug); and the **target delivery directory** `.specify/goal/<goal-slug>/summary/`. See `skills/create-team/SKILL.md` → Summary Refresh (all patterns).
   - **Disclose the Target assignment** as one extra line, verbatim forms (the third carries the STR-001 source marker `(团队默认)` when the resolution source is `team-default`):
     ```text
     本次 Target: T-002 — <statement>(open)
     本次 Target: T-003 — <statement>(open)(团队默认)
     本次 Target: 无(对 goal 整体运行)
     ```
   - Then orchestrate per the team's pattern (delegating to `create-team`'s execution engine): territory validation before parallel dispatch, DAG (no-cycle) validation + per-handoff verification before serial chain, mandatory max-iteration cap for iteration loops, and — for **continuous** loops — read `constraints.md` + budget + kill-switch at cycle start, run exactly **one cycle** at the team's declared maturity level (starting at L1), with an independent verifier at L2+; file-path-only handoff throughout. Per-member dispatch modality (native / virtual / external) follows `.specify/shared/definitions/subagent-definitions.md`; external CLI dispatch MUST honor its Visibility Contract (stream-json + progress filter + `.live.log`/`.jsonl`/`.status` triplet — silent `cli -p … > log 2>&1` dispatch is prohibited). Work is steered toward the **goal** — and, when a Target was assigned, focused on that slice — and the evaluator measures progress against it (iteration: iterate until the goal's threshold is met or the cap is reached; continuous: run one cycle, then update the state spine and stop).
   - **叫停与事后修改** — 用户可在执行中随时叫停;对结果不满意时经 `/speckit.team` modify / `improve-team` 修改,不设事前阻塞确认。
7. **Report** — after execution finishes, write a dated run report to `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` (goal, execution time, result summary, full process detail). Mandatory for every run. The report MUST carry the assignment line (fixed field name):
   ```text
   **Target 指派**: T-002(<statement>)   # 或 "无(goal 整体)";team-default 来源时附 (团队默认)
   ```
   New ledger entries produced by a Target-assigned run MUST carry `"target_ref": "T-<nnn>"` (written by the team supervisor into `items.jsonl`; the value is the resolved `effective` — explicit or team-default alike).

**`--target` invariants**: Goal–Team 绑定、身份解析结果、summary 交付目录位置不因 `--target` 改变——它不是改绑、不是写域声明,只是本次 run 的聚焦切片。本次门控精简仅移除确认停等,解析与五项检查的判定语义保持不变。

**Output discipline** (see `skills/create-team/SKILL.md` → Run Workspace, Reports & Output Discipline): all run **intermediates** stay in the git-ignored workspace `.specify/teams/.work/<slug>/`; **deliverables** (standard output) go only to their declared target paths; the team directory `.specify/teams/<slug>/` holds **only** the team's tracked run information (`team.md`, `runs/`, `items.jsonl`, plus `constraints.md` / `STATE.md` / `run-log.jsonl` for continuous teams). The periodic **summary** is a derived product indexed by *goal*, not by team: it lands in `.specify/goal/<goal-slug>/summary/` and never in the team directory.

### Persistence

- Canonical store: the team **directory** `.specify/teams/<slug>/` — definition at `.specify/teams/<slug>/team.md`, accumulating run reports under `.specify/teams/<slug>/runs/`. No per-tool symlink — teams are a framework-internal concept. Run intermediates live in the git-ignored `.specify/teams/.work/<slug>/`, never in the team directory.
- Each persisted team carries frontmatter (`slug`, `name`, `description`, `goal`, `pattern`, `members`, `config`, `created`, `updated`), a `## Goal` section (the team's overall final objective + success criteria), a `## Static Structure` section, and a `## Dynamic Structure` section (see `skills/create-team/SKILL.md` and the data model). The `## Goal` section is authored first — the static and dynamic sections are organized to serve it.

## Handoffs

**Before**: Optional `/speckit.agents` to author or refine the single agents that will become team members.

**After**: Run `/speckit.instructions` to sync discoverability of newly created teams and team skills.