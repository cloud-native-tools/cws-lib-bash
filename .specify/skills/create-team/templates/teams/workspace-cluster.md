---
preset_id: workspace-cluster
name: Workspace 多仓集群守护团队
pattern: continuous
summary: 以一个 VS Code `.code-workspace` 文件为唯一集群定义源，为每个 folder 派一个专属 subAgent，主 Agent 负责分解/派发/交叉校验的长期运营集群。
when_to_use: 一个由多个互相依赖的仓库组成的大型项目（IaC、单体拆分、多模块产品），需要持续做基线对齐、一致性巡检、故障定位，且成员仓库会增减。
signals:
  - code-workspace
  - workspace
  - 多仓
  - 多个仓库
  - 集群
  - 子模块
  - submodule
  - 巡检
  - 基线对齐
  - multi-repo
  - monorepo cluster
  - repo cluster
  - consistency guard
inputs:
  - name: workspace_file
    required: true
    description: "`.code-workspace` 文件路径；其 `folders` 列表即集群花名册（成员唯一定义源）"
  - name: authority_rules
    required: false
    description: 分支策略、权威源、submodule 上游提交流程等用户规范；写入 constraints.md
  - name: cadence
    required: false
    description: 巡检周期，默认 4h
members:
  - role: team-supervisor
    stage: optimizer
    type: Meta
    lifecycle: persistent
    responsibility: 解析 workspace folders 生成花名册并 diff 上轮成员增减；分解任务并派发 per-repo subAgent；对 subAgent 结论按证据类型抽查复核；汇总为集群报告；一切云端/写操作前设人工确认门
  - role: repo-analyst
    stage: executor
    type: Worker
    lifecycle: temporary
    responsibility: 单个 folder 的只读分析与巡检（每个 folder 一个实例）；输出结构化结论 + 证据路径；只读约束下不得写入所属仓库
  - role: consistency-checker
    stage: evaluator
    type: Worker   # 操作对象是各仓库的业务信息（分支策略/脏度/产物新鲜度）→ 业务层评估者
    lifecycle: temporary
    responsibility: 跨仓一致性判定——子模块边 initialized/pinned vs 远端 tip 的 SHA 三方校验、源码 HEAD 与构建产物新鲜度比对、依赖链每一跳存在性；对每条结论标注缺陷/环境限制/需人决策
config:
  maturity: L1
  cadence: 4h
  verifier: independent
  roster_source: workspace_folders
  roster_diff_on_start: true
  write_policy: read-only
  action_tiers: [read-only, mutate-local, mutate-cloud]
  mutate_cloud_requires_confirmation: true
  submodule_write_interception: true
  quality_dimensions:
    - name: roster-completeness
      weight: 0.20
    - name: consistency-detection
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
provenance: 2026-07 真实运营 Session（10 仓 IaC 集群：集群组建 → Git 全量同步 → 端到端资源创建 → 故障定位 → 知识沉淀），复盘见 draft/Code Workspace.md
---

## Goal Skeleton

对 `<workspace_file>` 的 `folders` 所定义的全部仓库，提供持续的集群守护：每 `<cadence>` 一个 cycle，产出
①成员花名册与上轮的增减差异 ②跨仓一致性判定（子模块边、构建产物新鲜度、依赖解析链）
③问题清单（区分代码缺陷 / 环境限制 / 需人决策）④可操作修复建议（指向具体仓库与路径）。
成功标准：四项产出齐全；每条根因结论附带对应证据类型；本 loop 对被守护仓库零写入。

## Static Structure

| Role | Stage | Type | Lifecycle | Responsibility |
|------|-------|------|-----------|----------------|
| team-supervisor | optimizer | Meta | persistent | 花名册解析与 diff、任务分解派发、证据抽查复核、汇总、确认门 |
| repo-analyst × N | executor | Worker | temporary | 每 folder 一个实例的只读分析与巡检，结构化输出 |
| consistency-checker | evaluator | Worker | temporary | 跨仓一致性判定与结论分类（评估对象是仓库业务信息 → Worker） |

`N` 不是固定值——它等于 workspace `folders` 的数量，随 workspace 文件变化而变化。

## Dynamic Structure

每个 cycle：

```
1. 读 constraints.md + budget + kill-switch
2. 解析 <workspace_file> → folders → 花名册；与上轮 roster diff → 成员增减告警
3. 派发前预检（每个 subAgent 载体的可达性/权限/用户/PATH）→ 失败给修复动作，不裸报错
4. 并行派发 repo-analyst（注入：仓库路径 + 兄弟仓清单 + 只读边界 + 输出 schema）
5. 回收结构化结论；对"根因"类结论按证据类型抽查（如"网络问题"必须附连通性证据），不达标打回
6. consistency-checker 做跨仓判定（SHA 三方校验 / 产物新鲜度 / 解析链逐跳）
7. 结论分类：缺陷 / 环境限制（预登记的已知预期失败）/ 需人决策
8. 写 cycle 报告 + STATE.md + run-log.jsonl；需人决策项与 mutate-cloud 建议交确认门
```

## Instantiation

1. 询问或确认 `workspace_file`；解析其 `folders`，把每个 folder 展开成一个 `repo-analyst` roster 行，`territory` 为该 folder 路径。
2. 用 `<workspace_file>` / `<cadence>` 替换 Goal Skeleton 的占位，写入 `goal` 与 `## Goal`。
3. 落 `.specify/teams/<slug>/team.md`，frontmatter 加 `preset: workspace-cluster`。
4. 生成 `constraints.md`：写入 `authority_rules`（分支策略、权威源、submodule 上游流程）+ 下方 Constraints 全部硬规则 + 该 workspace 全量子模块清单（扫 `.gitmodules`，含嵌套）。
5. 初始化 `STATE.md`（首轮 roster 快照 + 空的漂移清单）与空 `run-log.jsonl`。
6. 成员数会随 workspace 变化：不要把 `N` 写死进 goal，roster 每 cycle 按 folders 重算。

## Constraints & Hard Rules

- **workspace 文件是唯一集群定义源**——不另建 roster 配置；folder 的增减即成员的增减。
- **写操作三级分类**：`read-only` / `mutate-local` / `mutate-cloud`；`mutate-cloud` 强制人工确认并留痕。
- **子模块路径写操作拦截**：任何对子模块工作区副本的直接修改都必须被拦截，改走"上游提交 → fetch+checkout → gitlink bump"管线。
- **主 Agent 不轻信 subAgent**：根因结论必须附证据；证据类型不匹配的结论一律打回重做。
- **零上下文可接手**：团队目录（team.md / constraints.md / STATE.md）必须自足到另一个 Agent 无上下文即可接管运营。

## Known Pitfalls

- 成员遗漏/滞后：新增仓库长期缺席、靠人工发现——必须每 cycle diff folders，不依赖记忆。
- 启动链脆弱：subAgent 载体二进制不在 `sudo secure_path`、变量为空时的字符串拼接巧合——派发前预检，失败给修复动作。
- 环境假象污染报告：执行用户无 SSH key 导致的 fetch 失败被当成仓库异常——预登记"已知预期失败"并归类为环境限制。
- 修完源码忘记重建产物，修复不生效（同一 Session 两次实证）——登记"源码目录 → 产物 → 部署点"映射并比对新鲜度。
- 凭证静默失效：多个身份失效、`current` 指针丢失，直到报权限错误才发现——注入前验活并剔除失效身份。
- 长任务盲等：分页器卡死终端、history expansion 中断命令——派发统一 `--no-pager`、非交互环境变量、超时与僵死检测。
