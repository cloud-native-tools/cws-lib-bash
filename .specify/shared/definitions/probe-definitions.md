# Probe Definitions(全框架探测点真源·伞形)

> **Single source of truth** for Probe(探测点)definitions across the whole
> framework — canonical at `.specify/shared/definitions/probe-definitions.md`, mirrored
> to `.specify/shared/definitions/`. 伞形定位:本文件是全框架唯一 Probe 真源;
> **Feedback Probe(反馈插点)是其首个域实例**(commands/skills 收尾面,
> 既有 Class×Object 行语义不变),散布的引擎侧探测点(050 升级探测 / 运行判定
> 四轴 / 证据引擎 lane)以 scripts 切片 Class 入册,每行携带代码锚点。
> 纯代码微探针按 One Source of Truth 的 code-first 原则**不入册**,仅收录于
> 「非实体 probe 目录」章(纯指针)。
> Two-layer model: **Probe Class**(插点类,特征定义)× **Probe Object**
> (插点实例,系统落点); each Class carries an **internal/external** kind.
> Derived views (probe-map, command mode-1 overview) MUST be rebuilt from this
> file — never hand-copied.
> Invariants: five class features non-empty; ids unique; every Object belongs
> to exactly one Class; internal units match `/speckit.*` or `skill:*`(scripts
> 切片 Class 的 Object 单元为引擎脚本路径); external ids carry the `ext-`
> prefix and `custom:` units. Validate with `--action probes --validate`.

## Slices

- commands — 框架命令模板域
- skills — 框架技能域
- scripts — 引擎脚本域(散布探测点入册面;Object 单元 = 引擎脚本路径)
- templates / docs — 预留切片维度(暂无活动 probe)
- host-custom — 宿主项目自定义单元域(仅外部 probe)

## Classes

| class_id | kind | collection | target_slice | processing | insertion_type | code_anchor |
|----------|------|------------|--------------|------------|----------------|-------------|
| command-wrapup | internal | 命令单次运行的回顾与 ≥1 条单元级优化点 | commands | record→threshold→package→manual→mark-submitted | wrap-up | — |
| skill-wrapup | internal | 技能单次运行的回顾与 ≥1 条单元级优化点 | skills | record→threshold→package→manual→mark-submitted | wrap-up | — |
| external-custom | external | 宿主项目自定义单元运行的回顾与优化点 | host-custom | record→local-consumption(不上送) | wrap-up | — |
| command-gate | internal | 保留确认点触发后的用户决定观察事实(门控必要性证据) | commands | record→threshold→package→manual→mark-submitted | confirm-gate | — |
| skill-gate | internal | 保留确认点触发后的用户决定观察事实(门控必要性证据) | skills | record→threshold→package→manual→mark-submitted | confirm-gate | — |
| skill-evaluation-form | internal | 绘图技能交付产物后由用户主动给出的 Evaluation Form(绘制评价单),用于评价该次已交付结果 | skills | record→threshold→package→manual→mark-submitted | evaluation-form | — |
| trigger-escalation | internal | 050 主动流程触发的 P1–P5 升级探测(确定性存在性/计数/差集,永不读制品正文) | scripts | assess→suggest(非阻塞建议行) | situation | `.specify/scripts/python/trigger-utils.py`:`run_probes` |
| run-determination | internal | 运行判定四轴测量与两个可用性探测(token/elapsed/artifact_correctness/satisfaction;session store / evidence lane) | scripts | determine→session-record→route-into-feedback | wrap-up | `.specify/scripts/python/run-determination.py`:`AXES`,`probe_session_store`,`probe_evidence_lane` |
| evidence-lane | internal | 证据引擎 lane 的可用性探测(node 运行时 / session store / 平台存储清单) | scripts | collect→findings.json | collect | `.specify/scripts/python/evidence-utils.py`:`LANE_NAMES`,`probe_node`,`probe_session_store`,`probe_platforms` |
| exec-quant | internal | 受测单元执行的环境与质量遥测采集(agent 程序 / LLM 详细 / 质量指标;exec-quant durable store,Recording Only) | scripts | collect→durable-record | wrap-up | `.specify/scripts/python/exec-quant.py`:`ACTIONS`,`build_record`,`resolve_run_identity` |

## Objects

> SC-001 对账基准(历史快照,仅作当时留痕,不代表当前数量):彼时的隐式埋点
> 与嵌入点清单一一对应,`/speckit.feedback` 命令自身的 Object 随命令模板落地
> 同变更登记(见 contracts/probe-registry.md C-3.4)。当前生效的埋点集合以本
> 注册表为准,用 `feedback-utils.py --action probes --validate` 读取与对账,
> MUST NOT 在他处复写计数。
>
> 51–70 行为 044 Phase 7 的门控必要性 probe(insertion_type=confirm-gate):
> 每个非 intrinsic 保留确认点一个 Object,锚点是点位的单行 probe 指针
> (非 `## Feedback` 嵌入),故不参与 wrap-up embed 对账;unit 为确定性归属单元,
> 实际触发单元记在条目正文 `fired_during` 字段。行序即解析优先级:wrap-up 行
> 在前,保证无 lifecycle_point 的 record 调用行为不变。
>
> 「散布探测点」Object 行(trigger-escalation / run-determination /
> evidence-lane 三 Class,scripts 切片):unit 为引擎脚本路径,锚点在该
> Class 行的 code_anchor 列(类级锚点,Object 行不重复);这些行注册的是
> 声明性元数据(id/锚点/归属切片),不是行为本身,行为真源仍在引擎代码。

| object_id | class_id | unit | lifecycle_point |
|-----------|----------|------|-----------------|
| speckit-analyze-wrapup | command-wrapup | /speckit.analyze | wrap-up |
| speckit-checklist-wrapup | command-wrapup | /speckit.checklist | wrap-up |
| speckit-clarify-wrapup | command-wrapup | /speckit.clarify | wrap-up |
| speckit-derive-wrapup | command-wrapup | /speckit.derive | wrap-up |
| speckit-docs-wrapup | command-wrapup | /speckit.docs | wrap-up |
| speckit-goal-wrapup | command-wrapup | /speckit.goal | wrap-up |
| speckit-history-wrapup | command-wrapup | /speckit.history | wrap-up |
| speckit-implement-wrapup | command-wrapup | /speckit.implement | wrap-up |
| speckit-improve-wrapup | command-wrapup | /speckit.improve | wrap-up |
| speckit-instructions-wrapup | command-wrapup | /speckit.instructions | wrap-up |
| speckit-interview-wrapup | command-wrapup | /speckit.interview | wrap-up |
| speckit-plan-wrapup | command-wrapup | /speckit.plan | wrap-up |
| speckit-requirements-wrapup | command-wrapup | /speckit.requirements | wrap-up |
| speckit-research-wrapup | command-wrapup | /speckit.research | wrap-up |
| speckit-review-wrapup | command-wrapup | /speckit.review | wrap-up |
| speckit-sanitize-wrapup | command-wrapup | /speckit.sanitize | wrap-up |
| speckit-session-wrapup | command-wrapup | /speckit.session | wrap-up |
| speckit-skills-wrapup | command-wrapup | /speckit.skills | wrap-up |
| speckit-tasks-wrapup | command-wrapup | /speckit.tasks | wrap-up |
| speckit-team-wrapup | command-wrapup | /speckit.team | wrap-up |
| speckit-todo-wrapup | command-wrapup | /speckit.todo | wrap-up |
| speckit-tools-wrapup | command-wrapup | /speckit.tools | wrap-up |
| skill-archive-session-wrapup | skill-wrapup | skill:archive-session | wrap-up |
| skill-code-review-wrapup | skill-wrapup | skill:code-review | wrap-up |
| skill-collect-evidence-wrapup | skill-wrapup | skill:collect-evidence | wrap-up |
| skill-create-agent-wrapup | skill-wrapup | skill:create-agent | wrap-up |
| skill-create-docs-wrapup | skill-wrapup | skill:create-docs | wrap-up |
| skill-create-pages-wrapup | skill-wrapup | skill:create-pages | wrap-up |
| skill-create-skills-wrapup | skill-wrapup | skill:create-skills | wrap-up |
| skill-create-team-wrapup | skill-wrapup | skill:create-team | wrap-up |
| skill-create-tools-wrapup | skill-wrapup | skill:create-tools | wrap-up |
| skill-database-utils-wrapup | skill-wrapup | skill:database-utils | wrap-up |
| skill-document-utils-wrapup | skill-wrapup | skill:document-utils | wrap-up |
| skill-draw-diagram-wrapup | skill-wrapup | skill:draw-diagram | wrap-up |
| skill-git-utils-wrapup | skill-wrapup | skill:git-utils | wrap-up |
| skill-humanize-wrapup | skill-wrapup | skill:humanize | wrap-up |
| skill-sdd-loop-driver-cli-profile | skill-wrapup | skill:sdd-loop-driver | wrap-up |
| gate-git-workflow-tiered-mode | skill-gate | skill:git-utils | gate-git-workflow-tiered-mode |
| skill-improve-agent-wrapup | skill-wrapup | skill:improve-agent | wrap-up |
| skill-improve-docs-wrapup | skill-wrapup | skill:improve-docs | wrap-up |
| skill-improve-skills-wrapup | skill-wrapup | skill:improve-skills | wrap-up |
| skill-improve-team-wrapup | skill-wrapup | skill:improve-team | wrap-up |
| skill-improve-tools-wrapup | skill-wrapup | skill:improve-tools | wrap-up |
| skill-manage-agents-wrapup | skill-wrapup | skill:manage-agents | wrap-up |
| skill-memory-recall-wrapup | skill-wrapup | skill:memory-recall | wrap-up |
| skill-memory-record-wrapup | skill-wrapup | skill:memory-record | wrap-up |
| skill-merge-skills-wrapup | skill-wrapup | skill:merge-skills | wrap-up |
| skill-self-improvement-wrapup | skill-wrapup | skill:self-improvement | wrap-up |
| skill-sdd-project-setup-wrapup | skill-wrapup | skill:sdd-project-setup | wrap-up |
| skill-study-project-wrapup | skill-wrapup | skill:study-project | wrap-up |
| skill-summarize-project-wrapup | skill-wrapup | skill:summarize-project | wrap-up |
| skill-think-skills-wrapup | skill-wrapup | skill:think-skills | wrap-up |
| speckit-feedback-wrapup | command-wrapup | /speckit.feedback | wrap-up |
| gate-feature-status-regression | command-gate | /speckit.feature | gate-feature-status-regression |
| gate-implement-checklist-waiver | command-gate | /speckit.implement | gate-implement-checklist-waiver |
| gate-implement-evidence-binding | command-gate | /speckit.implement | gate-implement-evidence-binding |
| gate-sanitize-destructive-cleanup | command-gate | /speckit.sanitize | gate-sanitize-destructive-cleanup |
| gate-session-export-overwrite | command-gate | /speckit.session | gate-session-export-overwrite |
| gate-tools-invoke-entry | command-gate | /speckit.tools | gate-tools-invoke-entry |
| gate-tools-invoke-mode | command-gate | /speckit.tools | gate-tools-invoke-mode |
| gate-tools-invoke-rule | command-gate | /speckit.tools | gate-tools-invoke-rule |
| gate-tools-invoke-prompt | command-gate | /speckit.tools | gate-tools-invoke-prompt |
| gate-rubric-high-stakes | command-gate | /speckit.instructions | gate-rubric-high-stakes |
| gate-glossary-user-entry-overwrite | command-gate | /speckit.instructions | gate-glossary-user-entry-overwrite |
| gate-create-docs-tiered-disposition | skill-gate | skill:create-docs | gate-create-docs-tiered-disposition |
| gate-create-docs-write-plan | skill-gate | skill:create-docs | gate-create-docs-write-plan |
| gate-create-team-presence-loop | skill-gate | skill:create-team | gate-create-team-presence-loop |
| gate-create-team-noninteractive-call | skill-gate | skill:create-team | gate-create-team-noninteractive-call |
| gate-create-team-agent-reuse | skill-gate | skill:create-team | gate-create-team-agent-reuse |
| gate-create-tools-no-execute | skill-gate | skill:create-tools | gate-create-tools-no-execute |
| gate-git-workflow-remote-ops | skill-gate | skill:git-utils | gate-git-workflow-remote-ops |
| gate-improve-tools-no-test-invoke | skill-gate | skill:improve-tools | gate-improve-tools-no-test-invoke |
| gate-summarize-project-four-gates | skill-gate | skill:summarize-project | gate-summarize-project-four-gates |
| gate-summarize-project-structure-freeze | skill-gate | skill:summarize-project | gate-summarize-project-structure-freeze |
| gate-summarize-project-degraded-gates | skill-gate | skill:summarize-project | gate-summarize-project-degraded-gates |
| skill-draw-diagram-evaluation-form | skill-evaluation-form | skill:draw-diagram | evaluation-form |
| trigger-p1-feature-dir | trigger-escalation | .specify/scripts/python/trigger-utils.py | situation |
| trigger-p2-clarification-markers | trigger-escalation | .specify/scripts/python/trigger-utils.py | situation |
| trigger-p3-tasks-state | trigger-escalation | .specify/scripts/python/trigger-utils.py | situation |
| trigger-p4-feedback-threshold | trigger-escalation | .specify/scripts/python/trigger-utils.py | situation |
| trigger-p5-instructions-staleness | trigger-escalation | .specify/scripts/python/trigger-utils.py | situation |
| rd-axis-token-consumption | run-determination | .specify/scripts/python/run-determination.py | wrap-up |
| rd-axis-elapsed | run-determination | .specify/scripts/python/run-determination.py | wrap-up |
| rd-axis-artifact-correctness | run-determination | .specify/scripts/python/run-determination.py | wrap-up |
| rd-axis-satisfaction | run-determination | .specify/scripts/python/run-determination.py | wrap-up |
| rd-probe-session-store | run-determination | .specify/scripts/python/run-determination.py | wrap-up |
| rd-probe-evidence-lane | run-determination | .specify/scripts/python/run-determination.py | wrap-up |
| evidence-probe-node | evidence-lane | .specify/scripts/python/evidence-utils.py | collect |
| evidence-probe-session-store | evidence-lane | .specify/scripts/python/evidence-utils.py | collect |
| evidence-probe-platforms | evidence-lane | .specify/scripts/python/evidence-utils.py | collect |
| eq-collect-execution | exec-quant | .specify/scripts/python/exec-quant.py | wrap-up |
| eq-probe-host-process | exec-quant | .specify/scripts/python/exec-quant.py | wrap-up |
| eq-probe-host-config | exec-quant | .specify/scripts/python/exec-quant.py | wrap-up |
| eq-probe-determination-link | exec-quant | .specify/scripts/python/exec-quant.py | wrap-up |
| skill-analyze-artifacts-wrapup | skill-wrapup | skill:analyze-artifacts | wrap-up |
| skill-clarify-artifact-wrapup | skill-wrapup | skill:clarify-artifact | wrap-up |
| skill-create-checklist-wrapup | skill-wrapup | skill:create-checklist | wrap-up |
| skill-create-plan-wrapup | skill-wrapup | skill:create-plan | wrap-up |
| skill-create-requirements-wrapup | skill-wrapup | skill:create-requirements | wrap-up |
| skill-create-tasks-wrapup | skill-wrapup | skill:create-tasks | wrap-up |
| skill-derive-architecture-wrapup | skill-wrapup | skill:derive-architecture | wrap-up |
| skill-implement-feature-wrapup | skill-wrapup | skill:implement-feature | wrap-up |
| skill-manage-constitution-wrapup | skill-wrapup | skill:manage-constitution | wrap-up |
| skill-manage-features-wrapup | skill-wrapup | skill:manage-features | wrap-up |
| skill-manage-feedback-wrapup | skill-wrapup | skill:manage-feedback | wrap-up |
| skill-manage-goal-wrapup | skill-wrapup | skill:manage-goal | wrap-up |
| skill-manage-history-wrapup | skill-wrapup | skill:manage-history | wrap-up |
| skill-manage-instructions-wrapup | skill-wrapup | skill:manage-instructions | wrap-up |
| skill-manage-todo-wrapup | skill-wrapup | skill:manage-todo | wrap-up |
| skill-research-feature-wrapup | skill-wrapup | skill:research-feature | wrap-up |
| skill-review-sdd-process-wrapup | skill-wrapup | skill:review-sdd-process | wrap-up |
| skill-run-agent-wrapup | skill-wrapup | skill:run-agent | wrap-up |
| skill-run-interview-wrapup | skill-wrapup | skill:run-interview | wrap-up |
| skill-run-skills-wrapup | skill-wrapup | skill:run-skills | wrap-up |
| skill-run-team-wrapup | skill-wrapup | skill:run-team | wrap-up |
| skill-sanitize-materials-wrapup | skill-wrapup | skill:sanitize-materials | wrap-up |

## Handler

> 反应层实体(056):一个探测点(Probe Object)经 HandlerBinding 可挂接 N 个已注册反应。
> 六字段封闭集。kind=engine 的 action MUST 命中真实引擎 action 封闭集(对账面:
> contracts/engine-action-sets.md,校验见 `probe-utils.py --action handlers --validate`);
> kind=agent 的 action 为 behavior_owner 文件 `##` 级标题原文;kind=gate 的 action 为
> confirmation-gates.md 治理条目名。behavior_owner 仅路径指针——本表 MUST NOT
> 复述行为规则(One Source Of Truth)。order 冲突判定:同一 lifecycle point 内
> 不同 Handler 不得同序。
> 编译面占位约定(063 C-20,kind=engine 行):渲染集 = 该 action 引擎 manifest
> (`--action args-manifest`,per contracts/engine-action-sets.md 对账义务 4)的
> required 全集 + source 全集(--unit-id/--unit-type 已由调用行携带实值,不重复
> 占位渲染);占位语法 = 参数名去 `--` 前缀、连字符转下划线、全大写(如
> `--run-id` ⇒ `<RUN_ID>`);代入规则 = 尖括号为本轮运行时值——代入后照抄执行。
> 约定行文本由本注声明、渲染器逐字采用:当 section 内任一引擎行含占位时,在该行
> 之后渲染一行约定行;无占位则不渲染。
> Compiled-face convention line: 尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)

| handler_id | kind | action | mode | order | behavior_owner |
|------------|------|--------|------|-------|----------------|
| h-run-determination | engine | determine | non-blocking | 10 | .specify/scripts/python/run-determination.py |
| h-exec-quant | engine | collect | non-blocking | 15 | .specify/scripts/python/exec-quant.py |
| h-feedback-record | engine | record | non-blocking | 20 | .specify/scripts/python/feedback-utils.py |
| h-threshold-notice | agent | Threshold prompt protocol (canonical semantics for step 6) | non-blocking | 30 | .specify/shared/workflow/feedback-step.md |
| h-token-reflection | agent | Reflection procedure (the embedded step points here) | non-blocking | 40 | .specify/shared/workflow/feedback-step.md |
| h-docs-sync-eval | agent | Evaluation procedure (the embedded step points here) | non-blocking | 50 | .specify/shared/workflow/docs-step.md |
| h-situation-assess | engine | assess | non-blocking | 10 | .specify/scripts/python/trigger-utils.py |
| h-team-phase-summary | agent | Summary Refresh (all patterns) | non-blocking | 20 | .specify/skills/internal/create-team/SKILL.md |
| h-gate-evidence | gate | 门控观察协议 (Gate Observation Protocol) | non-blocking | 30 | .specify/shared/guidelines/confirmation-gates.md |

## HandlerBinding

> 订阅行:selector = 字面 `@point:<lifecycle_point>`(封闭集 wrap-up / situation /
> phase-boundary / confirm-gate);scope = complex-commands / skills / all 或逐
> object_id;身份 = (handler_id, selector, scope) 三元组,validate 拒绝完全重复。
> 一个 Probe Object 可被多个 Binding 订阅(1 ⇒ N)。

| handler_id | selector | scope | 覆盖说明 |
|------------|----------|-------|----------|
| h-situation-assess | @point:situation | all | 050 情境评估:每回合环境评估与建议遥测(trigger-utils.py assess);非单元编译面,声明性订阅 |
| h-team-phase-summary | @point:phase-boundary | skill-create-team-wrapup | 036 团队阶段边界总结:create-team 驱动的团队执行流在阶段边界刷新 goal 级总结 |
| h-gate-evidence | @point:confirm-gate | gate-create-docs-tiered-disposition | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-create-docs-write-plan | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-create-team-agent-reuse | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-create-team-noninteractive-call | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-create-team-presence-loop | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-create-tools-no-execute | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-feature-status-regression | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-git-workflow-remote-ops | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-git-workflow-tiered-mode | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-glossary-user-entry-overwrite | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-implement-checklist-waiver | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-implement-evidence-binding | 063 证据绑定门:pass 声明绑定归档证据([[STR-001]]) |
| h-gate-evidence | @point:confirm-gate | gate-improve-tools-no-test-invoke | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-rubric-high-stakes | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-sanitize-destructive-cleanup | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-session-export-overwrite | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-summarize-project-degraded-gates | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-summarize-project-four-gates | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-summarize-project-structure-freeze | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-tools-invoke-entry | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-tools-invoke-mode | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-tools-invoke-prompt | 044 门控必要性证据(逐 gate Object) |
| h-gate-evidence | @point:confirm-gate | gate-tools-invoke-rule | 044 门控必要性证据(逐 gate Object) |
| h-run-determination | @point:wrap-up | all | T019 实测更正 MVP 骨架:owner 链 feedback-step.md § Run Determination「Step 1 runs the engine's `determine` action at wrap-up」⇒ 69/69 单元生效 |
| h-exec-quant | @point:wrap-up | all | 059 执行量化采集:每受测单元 wrap-up 落一条量化记录;在运行判定(order 10)之后、反馈记录(order 20)之前,同 run 携带不重测 |
| h-feedback-record | @point:wrap-up | all | 69 单元现均有反馈记录面 |
| h-threshold-notice | @point:wrap-up | all | 消费 h-run-determination 判定结果(order 10 → 30 次序约束 FR-008/FR-014) |
| h-token-reflection | @point:wrap-up | all | owner 链:Token 效率自评在 Reflection procedure step 2 |
| h-docs-sync-eval | @point:wrap-up | skill-humanize-wrapup | humanize 技能的 Documentation 面(062;技能侧首个 docs 绑定) |
| h-docs-sync-eval | @point:wrap-up | speckit-analyze-wrapup | /speckit.analyze 的 Documentation 面(T019 矩阵;正枚举,免扣减语义) |
| h-docs-sync-eval | @point:wrap-up | speckit-checklist-wrapup | /speckit.checklist 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-clarify-wrapup | /speckit.clarify 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-derive-wrapup | /speckit.derive 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-docs-wrapup | /speckit.docs 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-feedback-wrapup | /speckit.feedback 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-goal-wrapup | /speckit.goal 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-implement-wrapup | /speckit.implement 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-improve-wrapup | /speckit.improve 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-instructions-wrapup | /speckit.instructions 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-interview-wrapup | /speckit.interview 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-plan-wrapup | /speckit.plan 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-requirements-wrapup | /speckit.requirements 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-research-wrapup | /speckit.research 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-review-wrapup | /speckit.review 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-sanitize-wrapup | /speckit.sanitize 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-session-wrapup | /speckit.session 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-skills-wrapup | /speckit.skills 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-tasks-wrapup | /speckit.tasks 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-team-wrapup | /speckit.team 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-todo-wrapup | /speckit.todo 的 Documentation 面 |
| h-docs-sync-eval | @point:wrap-up | speckit-tools-wrapup | /speckit.tools 的 Documentation 面 |

## 非实体 probe 目录

> 纯代码微探针按 One Source of Truth 的 code-first 原则**不入册**——它们不是
> 可订阅的探测实体(无 id、无生命周期点、无注册面),本目录仅以**纯指针**
> 收录:路径 + 一行语义。硬约束:MUST NOT 复述行为规则(行为真源在代码);
> MUST NOT 参与任何对账计数(probes --validate / reconcile 的计数断言排除本节)。
> requirements 输入例举的「git probe」未定位到具名代码探针,故本目录不含虚构条目。

- `.specify/scripts/bash/check-prerequisites.sh` — writability:L149 起的 write-bit 预探针(命令前置 fail-fast 可写性探测)
- `.specify/scripts/python/derive-utils.py` — probe-links:`probe_links`(L819)URL 可达性微探针,derive 核实前置
- `.specify/scripts/python/sanitize-utils.py` — probe-roots:`probe_roots`(L267)材料根清点微探针,sanitize 域内消费
- `.specify/scripts/python/validate-tasks.py` — read-only governor:L87–92 只读指向检测探针(引用形命令识别)
- `.specify/scripts/python/clause_extract.py` — mutual-exclusion:L16/L148 三正交则互斥探测微探针

## External Probe 登记契约

宿主项目的外部 probe 不写入本文件,登记于项目侧
`.specify/memory/feedback/probes/<object_id>.md`(YAML frontmatter,一文件一 probe):

```yaml
object_id: ext-<slug>        # MUST 以 ext- 开头(内外命名空间强制隔离)
class_id: external-custom    # MUST 引用 kind=external 的 Class
unit: custom:<owner>/<name>  # MUST 匹配 ^custom:[a-z0-9._/-]+$
lifecycle_point: wrap-up
```

- 注入路径:`/speckit.feedback` § Probe Injection(引擎 `--action probe-inject`)。
- 外部条目(`kind: external`)保留在宿主项目本地,**永不进入**框架上送打包路径
  (engine `--action package` 100% 排除,见 contracts/engine-cli.md C-4)。
- 校验:`--action probes --validate` 覆盖本文件 Classes/Objects 与外部 probe 文件。
