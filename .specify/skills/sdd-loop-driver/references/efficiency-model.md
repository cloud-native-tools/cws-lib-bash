# Efficiency Model — sdd-loop-driver 运行效率优化

> 本文件是七项运行效率优化（快车道 / 测试预算 / plan 小修约束 / 进度可见与脱离 / 大特性拆分门 / 确定性预检 / 跨特性重叠预检）的**唯一 owner**：快车道（§1）、两槽位测试预算（§2）、plan 只小修约束（§3）、进度可见与驱动解耦（§4）、大特性拆分门（§5）、确定性预检（§6）、跨特性重叠预检（§7）。SKILL.md 与 docs 页只保留摘要与指针；`references/dispatch-recipes.md` 与 `references/stage-prompts.md` 只引用本文件定义的字段、判据与程序，不复写规则。契约钉住落点为 `tests/contract/test_sdd_loop_driver_efficiency.py` 与 `tests/contract/test_sdd_loop_driver_gates.py`。

本文件自带运行时事实：条目只描述驱动在编排层执行的动作与判定；CLI 行为事实由 `references/cli/` 档案拥有，本文件只读引用，不复制档案内容。

## 1. 快车道（Fast Lane）

### 1.1 入口与唯一启用形式

- 快车道**仅在 U0 入口声明携带字面量 `fast-lane=opt-in` 时启用**，且该字面量原文写入该线状态脊。这是无人值守运行的唯一启用形式；自然语言声明、规模印象、历史运行推断都不构成启用。
- 交互式用户在场时，驱动可以在七判据实测后提议一次快车道，并把用户采纳的原文写入状态脊；提议不得阻塞运行，等待回答期间按完整链继续。
- 缺少字面量 → `decision=full-chain`，完整链是缺省行为。

### 1.2 裁决点与七项判据

裁决点在 `tasks.md` 已产出、`checklist` 派发之前，由 `.specify/scripts/admission-check.py` 以制品实测值判定。七项判据（全部机械判定；任一项无法证明即 fail-closed 判 `full-chain`）：

| id | 判据 | 机械证据 |
|----|------|----------|
| (a) | FR 定义行数 8–30（含端点），任务行数 10–40（含端点） | `requirements.md` 行匹配 `^- **FR-[0-9]{3}**:`（owner: requirements.md FR-003(a)）；`tasks.md` 行匹配 `^- \[[ xX]\] T[0-9]{3}`（窄模式，准入唯一）。SC 行、说明行、分组标题不计入。 |
| (b) | 宪法零改动 | `git diff --name-only <base>..HEAD` 不含 `.specify/memory/constitution.md` |
| (c) | 不新增可执行引擎、CLI 命令/模板、技能、外部依赖、网络服务或模型 API | 引擎/模板/依赖清单路径保守超集扫描 + 新增代码中的网络/模型调用痕迹；`skills/external/` 新增路径视为新技能 |
| (d) | 不涉及安全/隐私敏感面 | 路径或新增行命中认证授权、凭据/密钥、删除/迁移、发布/外传、确认门判据即拒绝 |
| (e) | 单线单分支且无并发线触碰同一交付路径 | `lines.manifest` 恰一条本线记录，分支等于 `--expected-branch` 与当前分支；语法 owner 为 `data-model.md` E1 §「lines.manifest 行语法」 |
| (f) | `clarify` 完成、活动标记为零、Related Feature 已解析 | `requirements.md` 含 `## Clarifications` + `### Session`，无 `[NEEDS CLARIFICATION:`；注册表行与详情文件存在 |
| (g) | 需求质量清单全绿 | `checklists/requirements.md` 至少一项 `- [X]`、零 `- [ ]` |

**窄/宽模式边界**：准入只使用窄任务模式 `^- \[[ xX]\] T[0-9]{3}`。仓库记账使用宽模式 `^- \[[ xX>~]\] T[0-9]{3}`，它会把 `[>]`/`[~]` 行计入，**MUST NOT 用于准入**；两者不得混用。FR/任务区间数值的运行时 owner 是 `admission-check.py` 的 `FR_MIN/FR_MAX/TASK_MIN/TASK_MAX` 常量，契约测试钉住它们；语义 owner 是 `requirements.md` FR-003。

**脚本接口**（`.specify/scripts/admission-check.py`，标准库且 Python ≥3.8）：

```text
admission-check.py --project P --base-ref R --requirements F --tasks F \
  --checklists F --entry-evidence F --lines-manifest F --expected-branch B \
  [--json-out F]
```

退出码：`0` = 可录取（`fast-lane`）；`1` = 拒绝（`full-chain`）；`2` = 输入或解析错误。JSON 记录逐条携带 `{id, verdict, evidence}`。

### 1.3 准入记录（E1）

准入记录在 `checklist` 派发前写入状态脊。字段面以 `data-model.md` E1 为准，至少包含：

- `decision`：`fast-lane` | `full-chain`
- `entry_evidence`：入口原文（含 `fast-lane=opt-in`）
- `criteria[]`：七项 `{id, verdict, evidence}`，evidence 非空且可复算
- `measured`：`{fr_count, task_count}`，由制品实测派生，不手抄
- `decided_at`：裁决时间
- `reversion`（可选）：`{trigger, evidence, at}`，录取后判据失效时记录

录取时记录必须携带跳过标记 `checklist=skipped(fast-lane)`（[[STR-003]]）。

### 1.4 下游发布与收口标记

- 裁决结果 MUST 随下游阶段提示词发布（至少 `implement` 与 `review`），使阶段不把缺失的 `checklist` 产物当作缺失的必需门；条件块见 `references/stage-prompts.md` §「Fast Lane Conditional Blocks」。
- 收尾汇总 MUST 携带 `checklist=skipped(fast-lane)` 或等价可见标记。
- 未录取的运行不发布跳过块，`checklist` 照常执行。

### 1.5 失败回退

录取后任一判据失效，或后续阶段发现新事实使判据不再成立（新增引擎/模式/安全面、任务数越界等）时：

1. 驱动 MUST 回退完整链，记录回退触发与证据到状态脊 `reversion` 字段；
2. 在适用位置补派 `checklist`；
3. 若回退发生在 `analyze` 已通过之后，补派 `checklist` 后 MUST 重过 `analyze` 一次，再按完整链继续；
4. 回退 MUST NOT 静默；收尾汇总必须列出回退次数与原因。

### 1.6 analyze / review 不变量

快车道 MUST NOT 改变 `analyze` 的 CRITICAL/HIGH 归零或已处置判据、至多一轮有界回环，也 MUST NOT 改变 `review` 的行为、证据义务与发现分级。快车道只替代 `checklist` 的质量清单步骤；`analyze` 与 `review` 始终必经、判定不削弱。

### 1.7 自应用排除

自应用例外：开发本技能的项目自身 MUST 使用完整阶段链（`checklist`、`analyze`、`review` 均必经），MUST NOT 产生本特性自身的快车道记录。该例外在 requirements FR-010、plan 与收尾证据中可见；它是规格约束，不是对快车道判据的豁免。

### 1.8 契约钉住

FL-01…FL-10 由 `tests/contract/test_sdd_loop_driver_efficiency.py` 的 `test_fl_01…test_fl_10` 钉住；准入行为由 `tests/unit/test_admission_check.py` 覆盖。任何运行 MUST NOT 在缺少 E1 准入记录时声称自己走了快车道。

> 快车道区间只适用于**单个**特性；超出区间的特性由 §5 的大特性拆分门接管——快车道拒绝不是终点，拆分后每个切片重新进入区间判定。

## 2. 两槽位测试预算（Test Budget）

### 2.1 全量定义与作用域

**全量测试运行** = 以项目规范测试运行器执行、不带路径/测试过滤器的完整套件（本仓 = `bash .specify/scripts/bash/run-tests.sh`）。预算以**运行线**为作用域：每线独立台账与独立槽位，多线并行互不共享或消耗。每条运行线恰好两个全量槽位：

| 槽位 | 时点 | 程序 |
|------|------|------|
| `baseline` | implement 起点（首个任务前） | `run-tests.sh --names-out <spec-dir>/baseline-failed.txt`，按名称捕获失败名单 |
| `closure` | `review` 通过之后、合并之前，由驱动或独立校验单元执行 | `run-tests.sh --names-out <spec-dir>/final-failed.txt`，`comm -13` 名称级比较 |

implement 内 MUST NOT 再运行第二次全量套件；其内部回归比较义务由收口槽位承担。槽内重跑记 `in-slot-rerun`，不另开槽。

### 2.2 台账与证据分工

- **E2 台账唯一来源** = 线状态脊的 `<!-- test-budget:begin -->` … `<!-- test-budget:end -->` JSONL 围栏；`<spec-dir>/test-evidence/implement.jsonl` 仅是 E3 传输/证据副本，MUST NOT 作为台账或审计来源。
- 本地拓扑 `spine_write_mode=direct` 由阶段直接追加；远端 `transport` 由执行侧写传输行，驱动在 U4 后合并进状态脊并记 `merge_source`/`merged_at`，合并前不得审计。
- E2 行字段以 `data-model.md` E2 为准（seq / slot / stage / purpose / trigger / at / command / selection_basis / rc / passed / failed / failed_names_path / baseline_compare / evidence_ptr，例外行另带 `exception_reason`，环境失败行带 `environment_evidence`）。
- 缺失 `passed`/`failed` → 审计报 `unknown`，MUST NOT 记为零或补造。

### 2.3 固定选择程序 `targeted-set-v1`

`clarify` / `plan` / `tasks` / `checklist` / `analyze` 与 `review` 只运行定向测试集；选择 MUST 由固定程序 `targeted-set-v1` 执行。算法 owner 是 `contracts/test-budget.md` TB-05；本节是实现载体，二者不一致时以 TB-05 为准。

- **输入**：`stage_base`（阶段起点提交）、`spec_dir`、`changed_paths`（`git diff --name-only --diff-filter=ACMR <stage_base>..HEAD` 与 `git status --porcelain` 的路径并集）、`test_roots` = `tests/unit`、`tests/contract`、`tests/integration`、`tests/scenarios`。
- **(a) 改动路径覆盖**：候选 = `find <test_roots> -type f -name 'test_*.py' | LC_ALL=C sort`；对每个不在 `test_roots` 下的 `changed_path`，选中内容包含该仓库相对路径或其模块 stem（basename 去扩展名）的候选文件（`grep -lF` 固定字符串）。
- **(b) 交付物契约测试**：本特性短名从 `spec_dir` 目录名去掉编号前缀派生；选中内容包含该短名或交付面路径（`skills/external/sdd-loop-driver`、`docs/reference/skills/sdd-loop-driver.md`）的契约/集成测试。
- **(c) 夹具变更**：`changed_path` 在 `test_roots` 下时选中该文件自身；在 `tests/fixtures/` 下时选中内容引用该夹具路径的测试文件。
- **排序与输出**：去重后 `LC_ALL=C sort -u`，每行一个仓库相对测试路径（stdout），供 E3 `selected_paths[]` 原样记录。
- **复现性**：同一 `stage_base` + 同一工作树状态 MUST 产生同一集合；阶段 MUST 记录完整命令、`stage_base`、输出（或摘要 + 哈希）与充分性说明；不同阶段 MUST NOT 使用不同选择命令。
- **空集**：改动了可执行面却得到空集 → `empty-selection-escalated`（扩大同族或按显式例外升级为全量，并记录原因）；仅文档改动 → `not-run-docs-only`。

### 2.4 E3 证据字段与完整性

每次定向运行记录：命令、选择依据、所选路径 `selected_paths[]`、充分性 `sufficiency`、rc、passed/failed、新增失败 `new_failures[]`、比较基线。每个**适用阶段**（`clarify` / `plan` / `tasks` / `checklist` / `analyze` / `review`）恰有一条 `row_type=stage-status` 行；整阶段缺行计入完整性分母，MUST NOT 静默缩小分母。

- `not-run-docs-only` 按**六项缩减字段集**判完整：`stage`、`row_type=stage-status`、`status`、`selection_basis`、`changed_paths[]`、`evidence_ptr`；运行字段不适用，MUST NOT 报 `unknown`。
- 快车道按 §1 授权跳过 `checklist` 时，该阶段记 `not-applicable-skipped-stage`（[[STR-008]]），以 E1 准入记录 + [[STR-003]] 为联结证据；MUST NOT 记为 `unknown`，MUST NOT 计入完整性分母。缺失联结证据的 skip 视为未授权：阶段计入分母并报 `unknown`。
- 证据文件整体缺失、文件为空、或没有唯一 `stage-status` 行时，该阶段仍计入分母并报 `unknown` + 违规（审计 exit 1）；MUST NOT 静默跳过或缩小分母。
- `unknown` 只用于证据缺失；收口审计输出 `stages=N complete=N`（N = 适用阶段总数，含文档型阶段）。

### 2.5 审计、例外与修复

`.specify/scripts/audit-test-budget.py --spine "$STATE_SPINE" --spec-dir <spec-dir> [--logs-dir <dir>] [--stage-check implement|closure]`：

- 校验两槽位、第三槽位拒绝、`in-slot-rerun` 只能出现在 `closure` 之后、`out-of-slot-exception` 必带原因与证据、`environment-failure` 不消耗槽位、closure 必须是名称级差集。
- `--logs-dir` 扫描阶段日志中的全量 runner 命令：日志中出现但台账未入账 → 违规；日志缺失 → `unknown`，MUST NOT 当零。
- `--stage-check implement` 只要求 baseline 恰 1 且允许 closure 未写入；`--stage-check closure` 要求 baseline 与 closure 各 1。
- 摘要 MUST 输出 `slots=baseline:N closure:N reruns=N exceptions=N unknown:N environment_failures=N` 与 `stages=N complete=N`。

**槽外例外与槽内重跑**：任何槽外全量 MUST 以 `out-of-slot-exception` 形式出现，带原因与证据，收尾汇总列出次数与原因。收口因修复新失败而重跑同一套件记 `in-slot-rerun`（含触发与证据），不另开槽；MUST NOT 静默超预算。**环境失败**：收集/执行任何测试前即失败（解释器或依赖缺失、收集前错误）记 `environment-failure`，不消耗槽位并附证据；实际执行了测试的调用（含 0 tests collected 的选择失败）消耗槽位。

**收口归属**：implement 只消耗 `baseline` 槽位；`closure` 由驱动在 `review` 通过之后、合并之前写入同一状态脊。closure 修复重入携带 `baseline_slot=skip(closure-repair)`，不再消耗 baseline。

### 2.6 编排层实现

本预算 MUST 在编排层实现（阶段提示词 + 状态脊台账 + 收口审计），MUST NOT 依赖修改框架命令内部流程。`STATE_SPINE_PATH`、`EVIDENCE_DIR`、`SPINE_WRITE_MODE=direct|transport` 由阶段提示词骨架统一携带；缺失 `STATE_SPINE_PATH` → 派发前快速失败（`ANOMALY:`），MUST NOT 另建第二份台账。

### 2.7 契约钉住

TB-01…TB-10 由 `tests/contract/test_sdd_loop_driver_efficiency.py` 的 `test_tb_01…test_tb_10` 钉住；审计行为由 `tests/unit/test_audit_test_budget.py` 覆盖；名称级回归由 `tests/integration/test_sdd_loop_efficiency_regression.py` 覆盖。

## 3. Plan 只小修约束（Plan Constraint）

### 3.1 生效点与状态

`plan` 阶段 U4 通过时，驱动 MUST 在状态脊登记：

```text
plan_constraint=active
activated_at=<epoch/ISO-8601>
plan_commit=<plan U4 commit>
approved_baseline_commit=<initial = plan_commit>
plan_owned_paths=plan.md,data-model.md,contracts/,quickstart.md,research.md,feature-ref.md
```

此后 `tasks` / `analyze` / `implement` / `review` 的提示词携带只小修块。驱动重入 MUST 从状态脊恢复 `plan_constraint=active` 与 `activated_at`，不得依赖会话记忆；二者缺失时不得假装约束不存在，按断点探测恢复。

### 3.2 小修与实质改动

- **小修**：错别字/措辞、断链/引用修复、格式、行级一致性；不改变范围、架构方向、数据模型语义、契约语义、FR/SC 内容或任务分解范围。
- **实质改动**：改变上述任一项、引入新能力/安全面，或多处小修累积后按**最终 diff** 改变语义。分类 MUST 按最终累计差异判定，MUST NOT 按单次编辑的措辞规避。

### 3.3 `PLAN-EDIT:` 声明格式（唯一 owner）

任何下游阶段对 plan 制品的改动 MUST 在完成哨兵前的回传中包含声明行。本小节是该格式的唯一 owner：

```text
PLAN-EDIT: <repo-relative path or artifact> — <one-line reason>；分类=minor|substantive
```

- 一条声明覆盖其点名的路径（或该路径的 basename）；未被任何声明覆盖的触碰判 `undeclared`。
- 需要实质改动但无法在约束下继续时，阶段 MUST 以 `ANOMALY: <一句话事实>` 回传建议改动与实质性理由，MUST NOT 静默改写 plan 或自行重跑 plan 阶段。

### 3.4 U4 校验与分类

驱动在每个下游阶段 U4 运行：

```bash
python3 <skill-dir>/scripts/audit-plan-changes.py --repo <repo> \
  --base <stage-base> --head HEAD --plan-owned plan.md --plan-owned data-model.md \
  --plan-owned contracts --plan-owned quickstart.md --plan-owned research.md \
  --plan-owned feature-ref.md --declarations <stage-declarations.txt>
```

脚本机械给出 `touched_paths[]`（`git diff --name-only <base>..HEAD` 加 `git status --porcelain` 未提交改动）、`declaration_lines[]`、`undeclared` 与按 `base` 的最终累计 `diff_stats`。驱动据最终 diff 把每个触碰分类为 `minor` / `substantive` / `undeclared`，并写入状态脊（E5）。`undeclared` 或 `substantive` MUST 先判该阶段门失败，再进入 3.5 分流。

### 3.5 两分支分流

「已批准需求基线」= E4 最新 `approved_baseline_commit` 中 `requirements.md` 的 FR/SC 定义集合与语义（`git show <commit>:requirements.md` 复核）。分类记录 MUST 写入该值；MUST NOT 以工作树文本或其它提交替代。

- **(a) 修复既有缺陷所必需**，且不改变已批准的需求范围/FR/SC 语义、架构方向、数据模型语义、契约语义或任务分解范围 → 驱动派发一次完整 plan 重审并记录触发与证据；重审通过后对门失败阶段做一次 U4 复验。
- **(b) 改变上述任一项、引入新能力/安全面，或驱动无法确定** → 作为决策以四要素上送（发现了什么 / 为何吃重 / 中间产物逐项可定位 / 可选处置），MUST NOT 自行重审。

每一次 `substantive`/`undeclared` 改动都按其分支处置并留痕，MUST NOT 因次数跳过分流；重复回环由既有 stall/retry 纪律兜底，不设人工次数上限。

### 3.6 Re-anchoring（requirements 门内变更）

plan 约束激活后，任何门内完成的 `requirements.md` 变更（含 analyze 路由修复、clarify 写回与显式范围修订）MUST 在下一个依赖该基线的 U4 分类之前触发 re-baseline：

1. 在 E4 追加一条 `rebaseline_events[]`：触发、时间、前一基线提交、新基线提交（= 包含该变更的提交）、FR/SC 定义集合与语义差异摘要；
2. 把 `approved_baseline_commit` 更新为新基线（此后一律使用**最新**锚点）；
3. 变更未提交或不可定位其提交时 MUST NOT re-anchor，受影响 plan 改动一律按 3.5(b) 上送；
4. re-anchoring 本身不构成 plan 重审，也不移动约束生效点；为落实新基线所含需求而做的 plan 改动按两分支正常分类，不得因旧基线缺少该需求而误判越界。

### 3.7 analyze 修复路由不变

本约束 MUST NOT 取消或削弱 analyze 门的上游修复路由：analyze 发现仍须回到所属制品修复并重过该门；约束只限制修复规模与重审开销。

### 3.8 收尾报告

收尾汇总 MUST 报告：约束是否 active、是否发生过 plan 制品改动、每项分类与处置去向（pass / gate-fail-rereview / gate-fail-escalate）。

### 3.9 显式排除与设计代价

框架命令内部的硬执行是**显式排除**项：约束是编排层纪律，驱动是执行点。已接受的设计代价：非驱动手工调用阶段命令不受约束；若后续证明编排层实现不安全，MUST 另立特性修订，不得静默扩大范围。

### 3.10 契约钉住

PC-01…PC-11 由 `tests/contract/test_sdd_loop_driver_efficiency.py` 的 `test_pc_01…test_pc_11` 钉住；机械判定由 `tests/unit/test_audit_plan_changes.py` 覆盖。

## 4. 进度可见与驱动解耦（Progress & Detach）

### 4.1 stream-json 主路径

`.specify/scripts/stage-runner.sh` 默认以 `stream-json` 调用阶段 CLI（`[[STR-001]]`），并把原始事件流完整落盘为 `raw-<line>-<stage>.jsonl`；CLI 的 stderr 单独落 `runner-log-<line>-<stage>.log`，不混入 raw。CLI 行为事实（是否支持该输出模式、事件形状、哨兵可靠性、工具超时上限）由 `references/cli/<cli>.md` 与 `contracts/cli-profiles.md` 拥有，本文件只读引用、不复制档案内容。派发资格由 `CAPABILITY_MATRIX` 决定；档案存在不等于可派发。

### 4.2 增量派生与可追溯性

`.specify/scripts/derive-live-log.py` 是确定性派生步骤：逐行读取 raw NDJSON，每个有意义的非终止事件立即输出一行可读进度（不缓冲到进程退出），实时日志可追加读取与尾部跟踪。每条派生行携带其 raw 事件序号与接收时间戳（`[evt=<seq> at=<epoch>] ...`），且在 runner 侧有对应的 raw 接收时间戳 sidecar（`raw-<line>-<stage>.ts.jsonl`）：

- **事件→派生行延迟 ≤120 秒**；无事件的静默区间不适用该阈值（也不产生任何派生行）。
- **每条派生行 MUST 可追溯到一条 raw 事件**；无对应事件时伪造进度行数 MUST 为 0（SC-007）。
- 不可解析行容错跳过，不得伪造进度或完成。

### 4.3 哨兵契约

阶段正常结束时，live log 的最后一个非空行 MUST 恰好是 `<STAGE>-DONE`。派生 MUST 取 CLI 终止 `result` 事件的文本并在 EOF 时作为最后内容逐字追加；MUST NOT 让 JSON 信封、事件元数据或**非终止事件**中的哨兵字样满足判定。`--finish` 从 raw 一次性恢复终止 result 文本。

### 4.4 watcher 可见性与判定不变

watcher 把流式进度只当作可见性信号：进度行数/增长与 raw 字节增长 MUST NOT 单独产生 `DONE` 或 `TIMEOUT`；完成仍须哨兵 + U4 独立校验，超时仍只由阶段 deadline 产生。`--raw-stream PATH` 在 WATCH 行附 `stream=na|absent|growing|idle`、在 EVIDENCE 行附 raw 路径与字节数，**不参与任何 verdict**。既有判定顺序、退出码与窗口/deadline 语义零改动（精确值 owner 是 `.specify/scripts/watch-target.sh --help/--self-test`）。`BASH_DEFAULT_TIMEOUT_MS` / `BASH_MAX_TIMEOUT_MS` 是宿主工具上限，不是阶段 deadline；工具上限导致的提前终止 MUST NOT 记作阶段超时。

### 4.5 降级

CLI 不支持 stream-json（能力探测失败）或派生运行时缺失/派生失败时，runner MUST 回退既有缓冲模式，在 status 记录 `progress=degraded` 与原因，并继续以退出记录 + 哨兵 + deadline 判定：

- 探测失败 → `progress=degraded reason=cli-lacks-stream`。
- 派生失败 → 先跑一次性 `--finish` 从 raw 恢复终止 `result` 文本；成功即写入 live log 并记 `degradation=derivation-recovered`。
- raw 无终止 result、但 raw 最后非空行恰为哨兵（CLI 未按 stream 输出）→ `buffered-fallback`。
- 两者皆无 → `sentinel=0`，按 `INCOMPLETE` 处理——这是缺失完成证据，不是降级导致的阶段失败。降级 MUST NOT 产生伪完成或阶段失败。

### 4.6 nohup 双拓扑与未脱离风险

阶段派发 MUST 在本地与远端两种拓扑下都完全脱离驱动会话：以 `nohup` 启动 runner，stdin 接 `/dev/null`，stdout/stderr 重定向到文件。远端保留 `ssh + su + nohup` 形态；本地补齐等价形态。脱离是默认形态：

- 派发记录写 `detached=yes|no`；遗漏 nohup 或 `</dev/null` → 记 `detached=no`，status 另写 `unprotected=true` 与风险原因。
- 四件套（pid / status / log / heartbeat）保持；新会话用 `--once` 快照接管，已完成阶段只核验、不重新派发；脱离 MUST NOT 削弱 U3/U4。

### 4.7 等待与证据纪律

驱动等待仍是既有长轮询窗口；实时日志只在窗口内读取用于可见性。MUST NOT 新增独立 `sleep` 回合或固定 cadence 空转，MUST NOT 引入新的常驻服务、守护进程或外部依赖。raw stream 与派生 live log MUST 作为 U4/U5 与事后审计证据保留。

### 4.8 契约钉住

PD-01…PD-10 由 `tests/contract/test_sdd_loop_driver_efficiency.py` 的 `test_pd_01…test_pd_10` 钉住；派生由 `tests/unit/test_derive_live_log.py` 覆盖；runner 行为由 `tests/integration/test_sdd_loop_efficiency_runner.py` 与 `watch-target.sh --self-test` 的四个 stream 用例覆盖。

## 5. 大特性拆分门（Decomposition Gate）

### 5.1 判据与决策点

单条运行线一次只推进**一个**特性。规模超上限时禁止把完整链一次性压在大特性上，MUST 先拆分为多个切片。两个决策点（均为机械判定）：

| 决策点 | 输入 | 触发 `split-required` 的条件 |
|--------|------|------------------------------|
| plan 入口（requirements U4 后、plan 派发前） | `requirements.md` | FR 定义行数 > 30 |
| tasks U4（tasks 产物后、analyze 派发前） | `requirements.md` + `tasks.md` | FR 定义行数 > 30，或任务行数 > 40 |

FR 定义行 = `^- \*\*FR-[0-9]{3}\*\*:`；任务行 = `^- \[[ xX>~]\] T[0-9]{3}`（宽模式，含 `[>]`/`[~]`）。上限与快车道中型区间端点一致（`FR_MAX`/`TASK_MAX`），数值 owner 是 `.specify/scripts/decomposition-check.py` 的 `FR_CEILING`/`TASK_CEILING` 常量；契约测试钉住二者相等。

### 5.2 脚本接口

```text
decomposition-check.py --mode plan|tasks --requirements F [--tasks F] [--json-out F]
```

退出码：`0` = `proceed`；`1` = `split-required`；`2` = 输入或解析错误（缺文件、零 FR/任务定义）。标准库且 Python ≥3.8。

### 5.3 `split-required` 处置

1. 驱动 MUST NOT 派发后续阶段（plan 或 analyze）；在状态脊写入拆分记录：`measured`（FR/任务实测数）、`reasons[]`、`ceilings`、`proposed_slices[]`（每个切片给出名称、FR 范围或主题、预估规模）与 `base_commit`。
2. 拆分粒度为**特性切片**：每个切片 MUST 自身落入 8–30 FR / 10–40 任务的区间，并各自拥有独立的 spec 目录与注册表绑定（`Related Feature` 仍指向同一特性）。
3. 拆分记录经用户或上游流程确认后，驱动按切片顺序逐条走完整链；MUST NOT 在同一线并行推进多个切片。
4. 拆分是**范围决策**：驱动 MUST NOT 自行删除、合并或重排需求来规避上限；无法在保留原意的前提下拆分时按四要素上送。

### 5.4 边界

- 上限只约束单特性规模，不评价内容质量；小于 8 FR 的特性不因此被拒绝，只按完整链执行（其成本本就低）。
- 拆分后切片仍受测试预算（§2）、plan 约束（§3）与全部质量门约束，MUST NOT 因拆分降低任何门。
- 本门是编排层纪律：非驱动手工调用阶段命令不受约束（与 §3.9 同一排除语义）。

### 5.5 钉住

常量与退出码由 `tests/unit/test_decomposition_check.py` 覆盖；上限与快车道端点的一致性由 `tests/contract/test_sdd_loop_driver_gates.py` 钉住。

## 6. 确定性预检（Pre-Analyze Deterministic Gate）

### 6.1 目的与运行点

analyze 是跨产物一致性的最后防线，不是第一次检查。requirements / plan / tasks 三个阶段的 U4 MUST 在派发下一阶段（plan / tasks / analyze）之前运行 `.specify/scripts/pre-analyze-check.py`，把可机械判定的漂移挡在 analyze 之前。预检通过是 analyze 派发的前置条件；预检失败 MUST NOT 派发 analyze。

### 6.2 检查项

| 检查 | 判据 | 严重度 |
|------|------|--------|
| `duplicate-id` | FR/SC 在 requirements.md 内、契约条款在 `contracts/` 内、任务在 tasks.md 内重复定义 | error |
| `dangling-id` | 引用不存在的 FR/SC；引用本规格契约命名空间内不存在的条款；跨特性命名空间（本规格未定义的 prefix） | error / advisory |
| `blocked-by` | `[blockedBy: ...]` 指向不存在的任务；非具体占位符（如 `Txxx`） | error / advisory |
| `count-claim` | 形式化制品中的 `N FR`、`N SC`、`N tasks/任务` 声明与实际定义数不符（区间、示例、历史/修复记录行跳过） | error |
| `missing-path` | 反引号声明的工作区路径在 `<repo>` 下不存在 | advisory（`--strict` 时 error） |

只扫描形式化制品（requirements/plan/tasks/data-model/quickstart/research/feature-ref/contracts/checklists）；`notes/`、`review.md`、`verification.md` 是带日期的记录，不参与实时一致性判定。

### 6.3 脚本接口

```text
pre-analyze-check.py --spec-dir D --stage requirements|plan|tasks --repo R \
  [--strict] [--waive CHECK:REL_PATH:LINE ...] [--json-out F]
```

退出码：`0` = pass；`1` = fail（存在未豁免的阻挡项）；`2` = 输入或解析错误。输出 JSON 携带 `findings[]{check,severity,path,line,message}` 与 `summary{errors,advisories,waived,fr,sc,tasks,clauses,files}`。

### 6.4 修复与豁免

1. error 级 finding MUST 在所属制品修复后重跑预检；连续两轮仍失败按 stall 纪律处理。
2. advisory 默认不阻挡；`--strict` 把它们升级为阻挡，用于收口前加固。
3. 豁免 MUST 使用 `--waive check:path:line` 精确到行，并在状态脊记录理由；MUST NOT 用宽泛豁免掩盖整类漂移。
4. 预检 MUST NOT 替代 analyze：预检只处理机械可判定项，语义/覆盖/宪法冲突仍由 analyze 判定，analyze 的 CRITICAL/HIGH 归零判据不削弱。

### 6.5 钉住

行为由 `tests/unit/test_pre_analyze_check.py` 覆盖；脚本接口与 owner 文档由 `tests/contract/test_sdd_loop_driver_gates.py` 钉住。

## 7. 跨特性重叠预检（Cross-Feature Overlap Pre-check）

### 7.1 目的与运行点

同一仓库内多条特性线可能交付同一路径（同一技能、同一 CLI 档案、同一 probe 对象），重叠在 implement 才暴露会产生成串返工。`clarify` U4 MUST 在派发 plan 之前运行 `.specify/scripts/overlap-check.py`，对当前特性与 specs 根下所有同级特性做交付面比较。

### 7.2 判据

- **当前特性的交付面**：`feature-ref.md` 中声明的共享交付根路径（反引号或行首路径；无声明时回退 `tasks.md` / `plan.md`）。特性自身 spec 目录内的路径不计。
- **其他特性的交付面**：优先取**实际交付面**——提交信息点名该 spec 的提交所改动的共享根文件（次选：触碰该 spec 目录的提交）；无 git 历史时回退其声明。这样"被引用的输入路径"不会被误判为交付物。
- **共享交付根**：`skills/`、`.specify/shared/`、`.specify/scripts/`、`.specify/templates/`、`src/`、`agents/`、`docs/`。无扩展名且不以 `/` 结尾的裸目录 token 忽略（它指整个区域，不是交付物）；显式目录声明以 `/` 结尾保留。
- **重叠关系**：`same-path`（完全相同）或 `nested-path`（一方是另一方的目录前缀）。
- 当前特性未声明任何共享交付路径 → `clear`（附 `note`），不是错误。
- 同级 specs 目录按 `^[0-9]{3}-` 识别；当前特性不在 specs 根下时也纳入比较集合。

### 7.3 脚本接口

```text
overlap-check.py --spec-dir D [--specs-root S] [--repo R] [--json-out F]
```

退出码：`0` = clear；`1` = overlap；`2` = 输入或解析错误。输出携带 `overlaps[]{other_spec,relation,current_path,other_path}` 与 `checked_specs[]`。

### 7.4 处置

1. 出现 overlap MUST NOT 直接派发 plan；驱动先做**归属裁决**：为每个重叠路径指定唯一 owner（通常为先声明或既有特性），另一方从范围中移除或改为只读引用。
2. 裁决结果 MUST 同时写入两条线的状态脊（`overlap_adjudication`：路径、owner、另一方的处置、时间）与相关 spec 的 Clarifications/feature-ref 注记。
3. 裁决后重跑 `overlap-check.py` 直至 `clear`；无法裁决时按四要素上送，MUST NOT 让两条线并行写同一路径。
4. 重叠预检是 clarify 的完成条件之一，MUST NOT 因"稍后可能不冲突"而跳过。

### 7.5 钉住

行为由 `tests/unit/test_overlap_check.py` 覆盖；脚本接口、owner 文档与阶段提示词接线由 `tests/contract/test_sdd_loop_driver_gates.py` 钉住。
