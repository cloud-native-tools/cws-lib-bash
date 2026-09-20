---
preset_id: project-cluster
name: 跨项目协作集群团队
pattern: continuous
summary: 登记多个项目(有关联或仅概念相似),为每个项目派生一个以其自身项目级 harness(constitution/instructions)行事的子代理;集群层做任务分解派发、证据复核与跨项目协调(设计理念/接口定义/代码规范),长期运营。
when_to_use: 需要同时推进或守护多个项目——彼此有依赖、或仅概念结构相似但需在理念/接口/规范上协调一致;每个项目有自己的 harness 规范,委派项目子代理按各自规范整体推进,而非一刀切。
signals:
  - 跨项目
  - 多项目
  - 项目集群
  - 多仓
  - 多个仓库
  - 集群
  - 子模块
  - 巡检
  - 基线对齐
  - 协调一致
  - 跨项目协调
  - 接口对齐
  - 接口定义
  - 代码规范
  - 跨仓一致性
  - cross-project
  - multi-project
  - project cluster
  - multi-repo
  - monorepo cluster
  - repo cluster
  - workspace
  - code-workspace
  - submodule
  - consistency guard
  - coordinate projects
inputs:
  - name: projects
    required: true
    description: 项目登记清单(集群花名册唯一定义源)——每项含:项目路径 + harness 锚点(constitution/instructions 位置) + 集群内协作焦点;项目间可有关联,也可仅概念结构相似
  - name: coordination_surfaces
    required: false
    description: 需跨项目协调一致的面(如 设计理念/接口定义/代码规范/依赖版本);缺省为空——各项目按自治推进+巡检,不做对齐
  - name: authority_rules
    required: false
    description: 分支策略、权威源、上游提交流程等用户规范;写入 constraints.md
  - name: cadence
    required: false
    description: 运营节奏,默认 4h
members:
  - role: team-supervisor
    stage: optimizer
    type: Meta
    lifecycle: persistent
    responsibility: 解析项目登记生成花名册并 diff 上轮成员增减;分解任务并按项目派发 project-operator;对结论按证据类型抽查复核;汇总跨项目协调议题为集群报告;一切云端/跨项目写操作前设人工确认门
  - role: project-operator
    stage: executor
    type: Worker
    lifecycle: temporary
    responsibility: 单项目一个实例;以该项目自身项目级 harness(constitution/instructions)为最高行为准则,按项目自定义规范推进任务或巡检;输出结构化结论 + 证据路径;默认只读,写操作限所属项目且遵循其规范
  - role: coordination-checker
    stage: evaluator
    type: Worker
    lifecycle: temporary
    responsibility: 跨项目协调面判定——对 coordination_surfaces 逐面比对(接口定义漂移/规范冲突/理念分歧/依赖链逐跳存在性);每条结论标注 缺陷/环境限制/需人决策;协调面之外的跨项目差异不置评
  - role: quality-checker
    stage: evaluator
    type: Meta
    lifecycle: persistent
    responsibility: 独立核查者(L1 不派遣,晋级 L2 后启用);对 supervisor 的进度/协调判定与 High-Priority 结论做定向复核,默认 REJECT 无证据结论
config:
  summary:
    enabled: true
    every: 5
    interactive: false
  maturity: L1
  cadence: 4h
  verifier: independent
  roster_source: project_registry
  roster_diff_on_start: true
  write_policy: read-only
  action_tiers: [read-only, mutate-local, mutate-cloud]
  mutate_cloud_requires_confirmation: true
  quality_dimensions:
    - name: roster-completeness
      weight: 0.20
    - name: coordination-detection
      weight: 0.35
    - name: evidence-quality
      weight: 0.25
    - name: suggestion-actionability
      weight: 0.20
  threshold: 0.8
  budget:
    max_cycles_per_day: 6
    max_subagents_per_cycle: 0
    on_80pct: report-only
    on_100pct: halt
  kill_switch: loop-pause-all
provenance: 由 workspace-cluster(2026-07 十仓 IaC 集群真实运营:组建 → 全量同步 → 端到端资源创建 → 故障定位 → 知识沉淀)与 process-monitor(requirement-implement-monitor 4 个已记录 cycle)合并泛化——花名册从 .code-workspace 绑定推广为显式项目登记,成员子代理从只读巡检推广为按各项目自身 harness 协作推进;监控侧的证据纪律、独立复核与误报统计并入。
---

## Goal Skeleton

对 `<projects>` 登记的全部项目提供持续的跨项目协作:每 `<cadence>` 一个 cycle,产出
①成员花名册与上轮的增减差异 ②各项目推进/巡检结论(每个项目以其自身 harness 规范行事)
③`<coordination_surfaces>` 各协调面的跨项目判定(接口漂移/规范冲突/理念分歧)
④问题清单(区分代码缺陷 / 环境限制 / 需人决策)⑤可操作修复与协调建议(指向具体项目与路径)。
成功标准:五项产出齐全;每条根因结论附带对应证据路径;High-Priority 误报率 < 20%(累计复盘);
对成员项目的写入严格限于该项目自身规范允许的范围,云端/跨项目变更全部过确认门。

## Static Structure

| Role | Stage | Type | Lifecycle | Responsibility |
|------|-------|------|-----------|----------------|
| team-supervisor | optimizer | Meta | persistent | 花名册解析与 diff、任务分解派发、证据抽查复核、协调议题汇总、确认门 |
| project-operator × N | executor | Worker | temporary | 每项目一个实例,以该项目自身 harness 为最高准则推进/巡检,结构化输出 |
| coordination-checker | evaluator | Worker | temporary | 跨项目协调面判定与结论分类(评估对象是各项目业务信息 → Worker) |
| quality-checker | evaluator | Meta | persistent | 独立复核(L2+ 启用),无证据结论默认 REJECT |

`N` 不是固定值——它等于项目登记清单的条目数,随登记变化而变化。项目之间可以有依赖关联,也可以仅概念结构相似;关联与否只影响协调面的检查内容,不影响花名册机制。

## Dynamic Structure

每个 cycle:

```
1. READ constraints.md + budget + kill-switch;预算触顶按 on_80pct / on_100pct 降级或中止
2. 解析 <projects> 登记 → 花名册;与上轮 roster diff → 成员增减告警
3. 派发前预检(每个项目的可达性/权限/harness 锚点存在性/执行身份)→ 失败给修复动作,不裸报错
4. 并行派发 project-operator(注入:项目路径 + 该项目 harness 锚点 + 兄弟项目清单 + 写边界 + 输出 schema);
   operator 加载并遵循所属项目的 constitution/instructions,按项目自定义规范推进
5. 回收结构化结论;对"根因"类结论按证据类型抽查(如"网络问题"必须附连通性证据),不达标打回
6. coordination-checker 对 coordination_surfaces 逐面做跨项目判定;未声明的面不强行统一
7. 结论分类:缺陷 / 环境限制(预登记的已知预期失败)/ 需人决策
8. L2+:quality-checker 对 High-Priority 结论独立复核,无证据即 REJECT
9. 写 cycle 报告到 runs/ + 更新 STATE.md + run-log.jsonl;需人决策项、mutate-cloud 与跨项目规范变更交确认门
10. Post-Run Critique:记录本轮误报,累计误报率统计
```

## Instantiation

1. 与用户共建 `projects` 登记清单:每项目给出路径、harness 锚点(该项目的 constitution/instructions 文件)、协作焦点。`.code-workspace` 文件的 `folders` 可作为登记种子,登记后以清单为准。
2. 与用户确认 `coordination_surfaces`:要在哪些面上跨项目协调一致(设计理念/接口定义/代码规范/依赖版本)。缺省为空即纯自治推进+巡检;面之外的差异合法,不置评。
3. 用 `<projects>` / `<cadence>` 替换 Goal Skeleton 的占位,写入 `goal` 与 `## Goal`;N 不写死进 goal,roster 每 cycle 按登记重算。
4. 落 `.specify/teams/<slug>/team.md`,frontmatter 加 `preset: project-cluster`，并按 `create-mode.md` schema 写入 `## Self-Improvement Contract`。
5. 生成 `constraints.md`:写入 `authority_rules` + 下方 Constraints 全部硬规则 + 各项目写边界(含子模块/上游流程)。
6. 初始化 `STATE.md`(首轮 roster 快照 + 空的漂移清单)与空 `run-log.jsonl`;从 `maturity: L1` 起步,先积累若干 cycle 的误报率数据再考虑晋级。
7. 明确 cadence 与每日 cycle 上限,避免集群运营本身消耗超过被推进的项目。

## Constraints & Hard Rules

- **项目登记清单是唯一花名册定义源**——不另建 roster 配置;登记条目的增减即成员的增减,每 cycle diff,不依赖记忆。
- **项目自治优先**:project-operator 以所属项目自身的项目级 harness(constitution/instructions)为最高行为准则;集群协调不得越过项目宪法——协调面之外的跨项目差异是合法的,不得借集群名义抹平项目自治。
- **写操作三级分类**:`read-only` / `mutate-local` / `mutate-cloud`;`mutate-cloud` 与跨项目规范变更强制人工确认并留痕;项目内写操作遵循该项目定义的提交流程(如子模块走"上游提交 → fetch+checkout → gitlink bump"管线)。
- **主 Agent 不轻信 subAgent**:根因结论必须附证据;证据类型不匹配的结论一律打回重做。
- **每条判定必须附证据路径**:无证据的进度/协调结论一律不得进报告;绝不猜测项目状态,推断不出就询问用户。
- **零上下文可接手**:团队目录(team.md / constraints.md / STATE.md)必须自足到另一个 Agent 无上下文即可接管运营。
- **必须从 L1 起步**:L1 不派遣 quality-checker、report-only;cycle 开始必读 constraints + budget + kill-switch。
- **状态脊是跨周期唯一记忆**:STATE.md / run-log.jsonl 之外不依赖会话上下文;每 cycle 报告头部显式声明本轮花名册版本。

## Known Pitfalls

- 成员遗漏/滞后:新增项目长期缺席、靠人工发现——必须每 cycle diff 登记清单。
- 启动链脆弱:子代理载体二进制不在 `sudo secure_path`、变量为空时的字符串拼接巧合——派发前预检,失败给修复动作。
- 环境假象污染报告:执行用户无 SSH key 导致的 fetch 失败被当成项目异常——预登记"已知预期失败"并归类为环境限制。
- 修完源码忘记重建产物,修复不生效(同一 Session 两次实证)——登记"源码目录 → 产物 → 部署点"映射并比对新鲜度。
- 凭证静默失效:多个身份失效、`current` 指针丢失,直到报权限错误才发现——注入前验活并剔除失效身份。
- 长任务盲等:分页器卡死终端、history expansion 中断命令——派发统一 `--no-pager`、非交互环境变量、超时与僵死检测。
- High-Priority 误报堆积导致报告被忽视——必须做 Post-Run Critique 并统计误报率。
- 目标漂移:cycle 之间悄悄换了推进对象却沿用旧 STATE——每 cycle 在报告头部显式声明本轮花名册与各项目焦点。
- cadence 过密导致预算被集群运营本身吃掉——先用较宽的周期跑稳再收紧。
- 把"协调一致"做成"强行统一":仅概念相似的项目在协调面之外保持差异是合法的,协调检查越界置评即越权。
