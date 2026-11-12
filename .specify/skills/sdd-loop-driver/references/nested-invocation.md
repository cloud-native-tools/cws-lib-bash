# Nested SDD Invocation（团队内嵌套 SDD 调用）——控制层级之下的从属执行路径

**Owner（唯一所有者）**: 本文件是 `sdd-loop-driver` 被团队席位调用时的**入口与交回契约**的唯一所有者：六项事实的校验集、止于 review 的边界、handoff 的封闭字段集、集成身份四事实、零 merge / 零 push 与本层交回义务，都只在这里写一次。

**不在本文件（只给指针，不复述）**:

| 主题 | 所有者 |
|------|--------|
| 阶段名册、状态脊格式、哨兵、U0–U6、卡死处置 | `../SKILL.md` § The Loop 与 `stage-prompts.md` |
| Goal / Target 的身份、状态机与绑定校验 | `.specify/shared/definitions/goal-definitions.md` 与 `.specify/scripts/python/goal-utils.py` |
| 授权谓词的两半（Agent 能力 AND 席位策略） | `.specify/skills/internal/run-agent/SKILL.md`、`.specify/skills/internal/create-team/references/create-mode.md` |
| line registry、worktree-per-write-line、ownership、集成队列 | 既有机制（`.specify/scripts/line-registry.py` 与其 references）；本文件只引用，MUST NOT 重述其语义 |
| 工作包模型（包执行者、集成队列的包侧语义） | 既有契约；本文件不涉及 |

**调用边界一句话**: 一条已获有效授权的团队成员职责 → **恰好一次**有界嵌套 SDD 运行 → 止于 review → 一份字段集封闭的 handoff。SDD 运行是从属执行路径：它 MUST NOT 创建、重绑、改范围或终止 Goal、Target、Team 或 roster。

---

## Entry validation table（六项事实在 U0 之前的校验集）

入口形态见 `../SKILL.md` § Invoked-from-Team Entry。下表是它的**校验集**：六项事实在任何 U0 动作之前逐项校验，任一不通过即**拒绝启动并点名失败的条件**——不启动运行、不进入 U0，且 MUST NOT re-scope 该职责（不得把职责改写到能通过的形状）。

| # | fail-closed 条件 | 判定依据 | 拒绝时点名 |
|---|------------------|----------|------------|
| V-1 | Goal 缺失或未定义 | `goal_ref` 未给出，或解析不到已定义的 Goal（`goal-utils.py list` 的归档集内无此 slug） | 缺失的 Goal 引用 |
| V-2 | Target 悬空、已关闭、已 drop 或越出绑定 Goal | `target_ref` 非空时必须是**该 Goal** 的 `open` Target；悬空/关闭/dropped/越界一律拒绝 | `target_ref` 与它越出的那个 Goal |
| V-3 | 终态 Goal（achieved / abandoned） | Goal 生命周期状态为终态 | 终态值本身 |
| V-4 | team slug 或 seat 缺失 | 两个授权坐标缺一即拒——授权按 (team, seat) 解析 | 缺的那一个坐标 |
| V-5 | scope 越出该席位 territory | 声明的工件/领域范围必须落在该席位（团队 roster 记录）的 territory 内 | scope 与越出的席位 |
| V-6 | 裁决缺失，或裁决不是 SDD 值 | `verdict_ref` 必须引用一条**已记录**的路由裁决，且其 verdict 为 SDD 值；`direct` 不产生 SDD 运行，`adjudicate` 停等裁定 | `verdict_ref` 与它实际携带的裁决 |

**校验失败不是「缩小范围后重试」的理由**：拒绝即结束，外层按失败隔离处置；提示词改词修不好一次拒绝，因为授权与裁决都由引擎与记录判定，不由叙述判定。

## Handoff schema（交接件：字段集封闭）

运行在 review 修复循环收束后结束并交回 handoff。字段集**封闭**——七项全填、无第八项：

| 字段 | 必填 | 规则 |
|------|------|------|
| `outcome` | 是 | 三值封闭：`completed`（review 后交接成功）/ `blocked`（授权或前置条件失败）/ `failed`（运行失败、卡死、超时、预算触顶）；四值以上一律非法 |
| `stages_reached` | 是 | 本次运行实际到达的阶段名，按驱动的名册引用；不复述名册，也不记未到达的阶段 |
| `artifact_paths` | 是 | 工件路径列表，逐项可定位；每个路径在交接时必须存在 |
| `evidence_paths` | 是 | 证据路径列表（测试证据、运行记录、裁决记录），逐项可定位 |
| `unresolved_findings` | 是 | review 后的未决 findings；`[]` 只表示「review 后无未决发现」，无 review 证据时写显式的 `not-evaluated` 文本，不得用空集冒充 |
| `anomaly_line` | 是 | 快速失败纪律的异常行：`未发现异常`，或行首 `ANOMALY:` 开头的逐条异常 |
| `integration_identity` | 是 | 集成身份四事实（见下节）；缺项即 handoff **incomplete（不完整）** |

缺任一项即判 **incomplete**；不完整的 handoff **不算成功**（never a successful return）——外层 MUST NOT 把它读成完成，调用方 MUST NOT 用散文把它补成完整的样子。

### Integration identity（集成身份四事实）

| 事实 | 来源 | 规则 |
|------|------|------|
| `line_id` | 既有 line registry 条目 | 运行的身份就是既有 line id；不新开编号族 |
| `branch` | 既有 line registry 的 branch 字段 | handoff MUST 点名该 branch 为**保留（retained）**分支，使外层知道集成发生在哪里 |
| `worktree_path` | 既有 line registry 的 worktree_path 字段 | 逐项可定位；运行结束后该路径仍指向工作所在 |
| `head_commit` | 交接时的一次 `git rev-parse HEAD` 读取 | 不落第二份状态：四值全部来自既有 line 条目与这一次读取 |

## Line registration（写线登记）

- 嵌套运行**就是一条写线**：启动时按既有 line registry（`.specify/scripts/line-registry.py`）登记，事件携带 `(line_id, run_id)` 信封，结束（成功、失败或卡死交回）后 deregister；line 身份来自该 registry，不新开。
- **worktree-per-write-line** 与 ownership manifest 沿用既有机制。两个嵌套运行的 territory 重叠时，**由该机制串行化或拒绝**——本文件不引入第二套并发原语，「同一成员同时只承载一次运行」的硬上限也由该机制落实。
- MUST NOT 新建第二套 line registry / ownership 模型 / integration queue / 状态脊（state spine）：本运行的全部记录解析到既有 line 条目与既有 state spine，不新增第二份存储。
- 每次嵌套运行结束后，worktree 的移除与分支保留按既有 line 机制的收尾规则处置；handoff 只**点名**工作所在，不移动它。

## Failure and stall handoff（失败与卡死交回）

卡死、超时或预算触顶时，运行 MUST 停止并交回：**不静默等待**、不无限重试、不把未完成的工作叙述成完成。

1. **停止**：停在当前阶段边界，不推进下一阶段，不丢弃已完成的部分。
2. **先把状态脊（state spine）落盘**，再交回——续跑与重入只认脊，不依赖会话记忆。
3. **返回失败的 handoff**：`outcome` = `failed`，并携带四要素——**发现了什么**（已完成到哪、结论是什么）/ **为何吃重**（why the run was costly）/ **已产生的中间产物**逐项按路径可定位 / **可选处置**（dispositions，例如缩小范围、换席位、人工裁定）。
4. **外层失败隔离与上报**：外层团队的失败隔离与上报照常适用；本次运行的记录按既有载体保留，不由本文件另开通道。

## Consumer duty（调用方义务）

- 调用方（发起本运行的成员 Agent，即 driver host 所在席位）把 handoff **原样（verbatim）**放进自己的结果，或按**稳定路径**引用同一条记录；MUST NOT 复算、改写，或把一个不完整的 handoff 叙述成完整。
- `outcome` 为 `blocked` 或 `failed` 时，调用方 MUST NOT 报成功；它自己的结果 MUST 携带该失败值本身，而不是一句掩盖它的总结。
- 团队运行报告引用同一条记录（既有 `create-team` 报告契约的载体）；该报告的嵌套段标题与段语义归 `074b-nested-governance`，本文件不定义、也不预先占用。
